"""
common.py

这份教程的公共工具箱。

你可以把它当成“教具仓库”：每个 lesson 只讲一个主题，重复出现的连接 CARLA、
生成车辆、创建相机、坐标投影、pygame 显示等代码，都放在这里。

为什么要有 common.py？
  如果每个 lesson 都完整复制一遍连接、生成、清理代码，文件会很长，
  你很难看出本节真正要学的重点。把基础工具放在 common.py 后，
  lesson 文件就可以更专注。

当前机器环境：
  CARLA root : D:\\HST_WORK\\carla\\WindowsNoEditor
  Python env : C:\\Users\\cicii\\miniconda3\\envs\\carla_test
  CARLA 版本 : 实测为 0.9.15
"""

import glob
import math
import os
import sys
import time
import weakref

import numpy as np


# =============================================================================
# 0. 导入 CARLA Python API
# =============================================================================

DEFAULT_CARLA_ROOT = r"D:\HST_WORK\carla\WindowsNoEditor"


def add_carla_egg_to_path(carla_root=None):
    """
    CARLA 的 Python API 可以通过两种方式导入：

    方式 A：conda/pip 环境已经安装 carla 包
      import carla

    方式 B：没有安装包，但 CARLA 目录里有 egg/whl
      WindowsNoEditor/PythonAPI/carla/dist/carla-xxx.egg

    你的环境已经 pip/conda 安装了 carla==0.9.15，所以通常不需要这个函数。
    这里写出来是为了让教程更稳：以后换环境时，它可以自动把 egg 加进 sys.path。
    """
    carla_root = carla_root or os.environ.get("CARLA_ROOT", DEFAULT_CARLA_ROOT)
    platform_tag = "win-amd64" if os.name == "nt" else "linux-x86_64"

    pattern = os.path.join(
        carla_root,
        "PythonAPI",
        "carla",
        "dist",
        "carla-*%d.%d-%s.egg" % (
            sys.version_info.major,
            sys.version_info.minor,
            platform_tag,
        ),
    )

    matches = glob.glob(pattern)
    if matches:
        sys.path.append(matches[0])


try:
    import carla
except ImportError:
    add_carla_egg_to_path()
    import carla


# =============================================================================
# 1. 全局配置
# =============================================================================

HOST = "localhost"
PORT = 2000
TIMEOUT = 30.0

WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
CAMERA_FOV = 90.0


# 这个起点来自你现有的 manual_drive_trajectory_compare.py。
# 后续所有 lesson 都尽量用同一个起点，方便你对比不同实验结果。
START_TRANSFORM = carla.Transform(
    carla.Location(x=55.754353, y=130.663452, z=0.500000),
    carla.Rotation(pitch=0.000000, yaw=180.320450, roll=0.000000),
)


# 摄像头安装在车辆局部坐标中：
#   x=1.25：向车头方向移动 1.25 米
#   y=-0.35：向车辆左侧移动 0.35 米，因为 CARLA 车辆 local +Y 是右侧
#   z=1.35：离地高度，模拟驾驶员眼睛/前挡风玻璃位置
#   pitch=-4：稍微向下看，方便看到路面
DRIVER_CAMERA_TRANSFORM = carla.Transform(
    carla.Location(x=1.25, y=-0.35, z=1.55),
    carla.Rotation(pitch=-5.0, yaw=0.0, roll=0.0),
)


# =============================================================================
# 2. CARLA 基础：client / world / vehicle / 清理
# =============================================================================

def connect_to_carla(host=HOST, port=PORT, timeout=TIMEOUT):
    """
    连接 CARLA server。

    运行任何 lesson 前，你都需要先手动启动：
      D:\\HST_WORK\\carla\\WindowsNoEditor\\CarlaUE4.exe -carla-rpc-port=2000

    client 是 Python 端和 CARLA server 通信的入口。
    world 是当前仿真世界，后续生成车辆、读取地图、调试绘制都从 world 开始。
    """
    # carla.Client 只是 Python 端的“遥控器”，真正的仿真在 CarlaUE4.exe 里跑。
    # 后面所有 world 操作，都会通过这个 client 发 RPC 请求给 server。
    client = carla.Client(host, port)

    # 地图刚加载、server 卡顿或没启动时，请求可能会等很久。
    # 设置 timeout 后，如果连接失败会更快报错，方便定位问题。
    client.set_timeout(timeout)

    # world 表示当前正在运行的仿真世界。
    # 它不是静态地图，而是包含地图、车辆、传感器、天气、时间步等运行状态。
    world = client.get_world()
    return client, world


def print_world_summary(world):
    """
    打印 world 最基本的信息。
    
    这个函数帮助你快速了解当前 CARLA 世界的状态。
    在调试时非常有用，可以确认：
      - 是否连接到了正确的地图
      - 世界里有多少 actor（车辆、行人、传感器等）
      - 仿真是在同步还是异步模式下运行

    world.get_map()       -> 当前地图，例如 Town10HD_Opt
    world.get_actors()    -> 当前世界里所有车辆、行人、传感器、交通灯等
    world.get_settings()  -> 同步/异步模式、固定步长等设置
    """
    # 获取当前世界的运行设置
    # settings 包含：synchronous_mode（同步模式）、fixed_delta_seconds（固定时间步长）等
    settings = world.get_settings()
    
    print("Connected to CARLA.")
    
    # world.get_map().name: 获取当前加载的地图名称
    # 常见地图：Town01, Town02, ..., Town10HD_Opt 等
    print("Map name:", world.get_map().name)
    
    # len(world.get_actors()): 统计世界中所有 actor 的数量
    # actor 包括：车辆、行人、传感器、交通灯、标志牌等
    print("Actor count:", len(world.get_actors()))

    """
    CARLA 有两种运行模式：
    
    异步模式 (Asynchronous, synchronous_mode=False)
        - CARLA server 以自己的速度运行（尽可能快）
        - Python 脚本和仿真不同步
        - 传感器数据可能在不同的仿真帧返回
        - 适合快速演示、手动驾驶体验
        
    同步模式 (Synchronous, synchronous_mode=True)
        - CARLA server 等待 Python 脚本的指令才推进每一帧
        - 必须调用 world.tick() 才能前进一帧
        - 传感器数据和车辆状态严格同步
        - 适合数据采集、机器学习训练等需要精确时序的场景
        
    如何设置？
        settings = world.get_settings()
        settings.synchronous_mode = True  # 或 False
        settings.fixed_delta_seconds = 0.05  # 每帧 0.05 秒 = 20 FPS
        world.apply_settings(settings)
    """
    print("Synchronous mode:", settings.synchronous_mode)

    """
    什么是 Fixed Delta Seconds？
    
    fixed_delta_seconds 是同步模式下的一个重要参数，表示每一帧仿真推进的时间长度（单位：秒）。
    
    常见设置：
        0.0：异步模式，CARLA 以最大速度运行，不固定帧率
        0.05：同步模式，每帧 0.05 秒 = 20 FPS（常用）
        0.1：同步模式，每帧 0.1 秒 = 10 FPS
        0.016667：同步模式，每帧约 0.0167 秒 = 60 FPS
        
    为什么需要这个参数？
        在同步模式下：
          1. 每次调用 world.tick() 或 world.wait_for_tick()，仿真只前进 fixed_delta_seconds 秒
          2. 所有传感器数据都基于这个固定时间步长生成
          3. 保证数据采集的时间一致性，方便后续处理
          
    举例：
        如果 fixed_delta_seconds = 0.05：
          - 第 1 次 tick(): 仿真时间从 0.00s -> 0.05s
          - 第 2 次 tick(): 仿真时间从 0.05s -> 0.10s
          - 第 3 次 tick(): 仿真时间从 0.10s -> 0.15s
          - 以此类推...
    """
    print("Fixed delta seconds:", settings.fixed_delta_seconds)


def spawn_ego_vehicle(world, transform=START_TRANSFORM):
    """
    生成一辆 ego vehicle，也就是"我们自己控制的车"。
    
    Ego vehicle 是自动驾驶系统中的"主车"，即我们想要控制的车辆。
    与之相对的是其他交通参与者（NPC 车辆、行人等）。

    CARLA 里所有可生成对象都来自 blueprint：
      vehicle.tesla.model3     <- 车辆模板
      sensor.camera.rgb        <- RGB 相机模板
      sensor.other.imu         <- IMU 传感器模板
      ...

    blueprint 是模板，spawn_actor 会根据模板和 transform 生成真实 actor。
    
    类比：
      blueprint 就像"类"（class）
      actor 就像"实例"（instance）
    """
    # blueprint_library 是"模板库"，里面有所有可生成对象的模板。
    # 可以通过 filter() 方法查找特定类型的模板。
    blueprint_library = world.get_blueprint_library()
    
    # filter("vehicle.tesla.model3") 会返回匹配 Tesla Model 3 的车辆模板列表。
    # [0] 取第一个匹配项（通常只有一个）。
    vehicle_bp = blueprint_library.filter("vehicle.tesla.model3")[0]

    # role_name=hero 是 CARLA 示例里的常用约定。
    # 一些工具会优先识别 role_name 为 hero 的主车。
    # 这不是必须的，但有助于其他系统识别哪辆车是"主角"。
    vehicle_bp.set_attribute("role_name", "hero")

    # try_spawn_actor 和 spawn_actor 的区别：
    #   try_spawn_actor: 失败时返回 None（更友好，适合教学）
    #   spawn_actor:     失败时直接抛异常（更严格）
    # 
    # 常见失败原因：
    #   1. 出生点被其他 actor 占用
    #   2. 上一次脚本没清理 actor
    #   3. 位置在地图外或不可达区域
    vehicle = world.try_spawn_actor(vehicle_bp, transform)
    if vehicle is None:
        raise RuntimeError(
            "车辆生成失败。常见原因：上一次脚本没清理 actor，出生点被占用。"
            "可以重启 CARLA server，或先运行清理脚本/换出生点。"
        )

    # 关闭自动驾驶，后续由 pygame 键盘输入控制车辆。
    # 如果设置为 True，CARLA 会自动控制车辆行驶（AI 驾驶）。
    vehicle.set_autopilot(False)

    # 再 set_transform 一次，确保生成后车辆姿态就是我们指定的固定起点。
    # 虽然 spawn_actor 时已经指定了 transform，但显式设置更安全。
    vehicle.set_transform(transform)
    return vehicle


def destroy_actors(actors):
    """
    清理 lesson 生成的 actor。
    
    ⚠️ 非常重要：
      CARLA actor 不会因为 Python 脚本退出就自动消失！
      如果忘记 destroy，世界里会留下旧车、旧传感器，占用出生点和资源。
      
    后果：
      1. 多次运行后，出生点会被占满，无法生成新车辆
      2. 旧传感器继续消耗计算资源
      3. CARLA UE4 窗口中会看到很多"幽灵"车辆
      4. 可能导致内存泄漏

    传感器 actor 需要先 stop() 再 destroy()。
    
    工作原理：
      1. 反向遍历列表（先销毁后创建的）
      2. 对每个 actor，如果有 stop() 方法就先调用（传感器需要）
      3. 然后调用 actor.destroy() 销毁 actor
      4. 用 try-except 捕获可能的异常，避免中断清理流程
    """
    # 反向销毁更安全：通常传感器是后创建的、挂在车辆上，
    # 先销毁传感器，再销毁车辆，可以减少依赖关系带来的异常。
    # 
    # reversed([a for a in actors if a is not None]):
    #   1. 过滤掉 None 值（可能有些 actor 生成失败）
    #   2. 反转列表顺序
    for actor in reversed([a for a in actors if a is not None]):
        try:
            if hasattr(actor, "stop"):
                # sensor.listen 启动后会持续回调，destroy 前先 stop。
                # 如果不停止就直接销毁，可能导致回调访问已销毁的对象，引发崩溃。
                actor.stop()
        except RuntimeError:
            # 如果 actor 已经被销毁或其他错误，忽略并继续
            pass

        try:
            actor.destroy()
        except RuntimeError:
            # 同样，如果销毁失败（可能已经被销毁），忽略并继续
            pass


# =============================================================================
# 3. Transform / Location / Rotation / 车辆局部坐标
# =============================================================================

def location_to_homogeneous(location):
    """
    将 carla.Location 转换为齐次坐标 [x, y, z, 1]。

    什么是齐次坐标（Homogeneous Coordinates）？
      - 普通 3D 坐标是 (x, y, z)，只能表示位置
      - 齐次坐标是 (x, y, z, w)，通常 w=1
      - 加上第 4 维后，可以用 4x4 矩阵同时处理旋转和平移

    为什么要加最后的 1？
      - 4x4 变换矩阵不只表达旋转，也表达平移
      - 用 [x,y,z,1] 才能被 4x4 矩阵同时旋转和平移
      - 如果 w=0，则表示一个方向向量（不受平移影响）

    数学原理：
      | R11 R12 R13 Tx |   | x |   | R11*x + R12*y + R13*z + Tx |
      | R21 R22 R23 Ty | * | y | = | R21*x + R22*y + R23*z + Ty |
      | R31 R32 R33 Tz |   | z |   | R31*x + R32*y + R33*z + Tz |
      | 0   0   0   1  |   | 1 |   |            1               |
      其中 R 是旋转矩阵，T 是平移向量

    Args:
        location: CARLA 的 3D 位置对象

    Returns:
        numpy.ndarray: 形状为 (4,) 的齐次坐标数组
    """
    return np.array([location.x, location.y, location.z, 1.0], dtype=float)


def homogeneous_to_location(values):
    """
    将齐次坐标或三维数组转换回 carla.Location。

    这是 location_to_homogeneous 的逆操作。
    在矩阵运算完成后，需要把结果转回 CARLA 能识别的 Location 对象。

    Args:
        values: 包含至少 3 个元素的数组或列表 [x, y, z, ...]

    Returns:
        carla.Location: CARLA 位置对象
    """
    return carla.Location(
        x=float(values[0]),
        y=float(values[1]),
        z=float(values[2]),
    )


def local_location_to_world(parent_transform, local_location):
    """
    把 actor 局部坐标里的点转换成 CARLA 世界坐标。

    核心概念：什么是局部坐标 vs 世界坐标？
      - 世界坐标 (World Frame): 整个地图的全局坐标系，所有物体都用同一套 (x, y, z)
      - 局部坐标 (Local Frame): 相对于某个物体（如车辆）的坐标系
        * 车辆的局部坐标：+X = 车头方向，+Y = 车辆右侧，+Z = 车顶方向
        * 无论车辆怎么旋转，"车头前方 10 米"在局部坐标里永远是 (10, 0, 0)

    为什么要转换？
      - CARLA 的调试绘制、传感器投影等功能都需要世界坐标
      - 但我们思考问题时，用局部坐标更直观（例如："车前方 10 米"）

    数学原理：
      - 使用 4x4 变换矩阵（Transform Matrix）进行坐标转换
      - 矩阵包含了旋转（Rotation）和平移（Translation）信息
      - 公式：world_point = T_parent_to_world * local_point

    Args:
        parent_transform: 父物体的变换矩阵（例如车辆的 transform）
        local_location: 局部坐标点（例如 carla.Location(x=10, y=0, z=0) 表示前方 10 米）

    Returns:
        carla.Location: 转换后的世界坐标点

    使用示例：
        # 计算车辆前方 10 米、右侧 2 米处的世界坐标
        local_pt = carla.Location(x=10.0, y=2.0, z=0.0)
        world_pt = local_location_to_world(vehicle.get_transform(), local_pt)
        # world_pt 现在可以在地图上绘制了
    """
    # parent_transform.get_matrix() 获取 4x4 变换矩阵
    # 这个矩阵描述了如何从 parent 的局部坐标系转换到世界坐标系
    parent_to_world = np.array(parent_transform.get_matrix())

    # 矩阵乘法：world_point = T_parent_to_world * local_point
    # 注意：local_point 必须是齐次坐标 [x, y, z, 1]，才能同时处理旋转和平移
    world_point = np.dot(parent_to_world, location_to_homogeneous(local_location))
    return homogeneous_to_location(world_point)


def get_ground_z(world, location):
    """
    查询 location 附近道路中心线 waypoint 的 z 坐标（路面高度）。

    核心概念：什么是 Waypoint（航点/路点）？
      - CARLA 的地图是由无数条"隐形轨道"组成的网络
      - Waypoint 就是这些轨道上的标记点，记录了道路的精确位置、朝向和高度
      - 可以把它想象成马路中间白色虚线上的一个个"小钉子"

    为什么需要这个函数？
      - 贴地 AR 需要一个精确的路面高度
      - 如果直接用车辆 z 或相机 z，箭头会飘在空中（因为车辆有悬挂高度）
      - 如果完全等于地面 z，可能和道路表面发生 z-fighting（深度冲突），导致画面闪烁
      - 所以后续通常会用 road_z + 0.03 或 +0.05，让标志物稍微浮在路面上方

    工作原理：
      1. 调用 world.get_map().get_waypoint() 找到最近的道路航点
      2. project_to_road=True 会把空中的点"垂直投影"到路面上
      3. 返回该航点的 z 坐标，即路面海拔高度

    Args:
        world: CARLA world 对象
        location: 参考位置 (carla.Location)，可以是空中任意点

    Returns:
        float: 该位置对应的路面高度（z 坐标）

    使用示例：
        # 假设你想在车头前方 10 米处画一个贴地箭头
        ahead_location = vehicle.get_transform().location + forward_vector * 10
        ground_height = get_ground_z(world, ahead_location)
        arrow_z = ground_height + 0.05  # 抬高 5 厘米避免闪烁
    """
    # get_waypoint 会把一个空间点投影到最近的道路 waypoint
    # 参数详解：
    #   location: 参考点，即使它在空中（z=100米），也会被垂直投影到路面
    #   project_to_road=True: 关键参数！即使 location 不在路面上，也强行找到最近的道路
    #   lane_type=carla.LaneType.Driving: 只查找"可驾驶车道"，忽略人行道、草地、护栏等
    waypoint = world.get_map().get_waypoint(
        location,
        project_to_road=True,      # 【关键】即使你的点在空中或路边，也强行把它"吸"到最近的路面上
        lane_type=carla.LaneType.Driving,  # 只找可驾驶的车道，忽略人行道或草地
    )
    
    # 如果找不到路（比如在野外、河里或地图边界外），waypoint 会是 None
    if waypoint is None:
        # 降级策略：返回原始位置的 z 坐标
        return location.z
    
    # 返回道路中心线上该点的精确高度
    # waypoint.transform.location.z 是 CARLA 地图预先计算好的路面海拔
    return waypoint.transform.location.z


def ground_point_in_vehicle_frame(world, vehicle, forward_m, right_m=0.0, z_offset=0.04):
    """
    从车辆局部坐标定义一个地面点，并返回其世界坐标。

    这是本教程中最常用的工具函数之一！
    它结合了"局部坐标转换"和"路面高度查询"两个功能。

    工作流程：
      1. 根据车辆局部坐标（前方多少米、右侧多少米）计算粗略的世界坐标
      2. 查询该位置的路面高度（通过 Waypoint）
      3. 调整 z 坐标，使点贴近地面

    为什么需要 z_offset？
      - 如果 z 完全等于路面高度，绘制的箭头/标志会和路面重叠
      - 这会导致 z-fighting（深度冲突），画面出现闪烁的噪点
      - 抬高 0.04 米（4 厘米）可以让标志物清晰可见，又不会显得飘在空中

    Args:
        world: CARLA world 对象
        vehicle: 参考车辆
        forward_m: 车辆前方多少米（正数=车头前，负数=车尾后）
        right_m: 车辆右侧多少米（正数=右侧，负数=左侧）
        z_offset: 比路面高出的距离（默认 0.04 米 = 4 厘米）

    Returns:
        carla.Location: 世界坐标下的地面点

    使用示例：
        # 获取车辆前方 10 米、左侧 3 米处的地面点
        target = ground_point_in_vehicle_frame(world, vehicle, forward_m=10.0, right_m=-3.0)
        # 在这个位置画一个调试点
        world.debug.draw_point(target, size=0.2, color=carla.Color(255, 0, 0))
    """
    # 第一步：把"车前方 forward_m、右侧 right_m"的局部点转成世界坐标
    # 此时 z=0.0，只是一个粗略的水平位置，高度还不准确
    rough = local_location_to_world(
        vehicle.get_transform(),
        carla.Location(x=forward_m, y=right_m, z=0.0),
    )

    # 第二步：查询该位置的路面高度，并调整 z 坐标
    # get_ground_z 会通过 Waypoint 找到精确的路面海拔
    # + z_offset 让点稍微高于路面，避免视觉闪烁
    rough.z = get_ground_z(world, rough) + z_offset
    return rough


def print_transform_details(name, transform):
    """把 Transform 拆成 Location 和 Rotation 打印出来。"""
    loc = transform.location
    rot = transform.rotation
    print("\n{} Transform".format(name))
    print("  Location: x={:.3f}, y={:.3f}, z={:.3f}".format(loc.x, loc.y, loc.z))
    print("  Rotation: pitch={:.3f}, yaw={:.3f}, roll={:.3f}".format(
        rot.pitch, rot.yaw, rot.roll
    ))


def print_vehicle_local_axes(vehicle):
    """
    打印车辆局部坐标轴在世界坐标中的方向。

    车辆局部坐标：
      +X forward：车头方向
      +Y right  ：车辆右侧
      +Z up     ：车辆上方

    get_forward_vector/get_right_vector/get_up_vector 返回的是这些局部轴
    经过车辆 Transform 旋转后，在 world 坐标中指向哪里。
    """
    transform = vehicle.get_transform()
    forward = transform.get_forward_vector()
    right = transform.get_right_vector()
    up = transform.get_up_vector()
    yaw = math.radians(transform.rotation.yaw)

    print_transform_details("Vehicle", transform)
    print("\nVehicle local axes expressed in world frame:")
    print("  local +X forward -> ({:.4f}, {:.4f}, {:.4f})".format(
        forward.x, forward.y, forward.z
    ))
    print("  local +Y right   -> ({:.4f}, {:.4f}, {:.4f})".format(
        right.x, right.y, right.z
    ))
    print("  local +Z up      -> ({:.4f}, {:.4f}, {:.4f})".format(
        up.x, up.y, up.z
    ))
    print("\nYaw sanity check:")
    print("  cos(yaw), sin(yaw) -> ({:.4f}, {:.4f})".format(
        math.cos(yaw), math.sin(yaw)
    ))
    print("  forward x/y        -> ({:.4f}, {:.4f})".format(forward.x, forward.y))


# =============================================================================
# 4. RGB / Depth camera sensor
# =============================================================================

def carla_bgra_to_rgb_array(image):
    """
    CARLA camera RGB 图像原始格式是 BGRA：
      B, G, R, A

    pygame 和大多数深度学习预处理更常用 RGB：
      R, G, B

    返回：
      numpy array, shape=(height, width, 3), dtype=uint8
    """
    # raw_data 是一维 bytes buffer，先按 uint8 解释。
    array = np.frombuffer(image.raw_data, dtype=np.uint8)

    # CARLA 每个像素 4 个通道：B, G, R, A。
    array = np.reshape(array, (image.height, image.width, 4))

    # 去掉 alpha 通道，只保留 BGR。
    array = array[:, :, :3]

    # BGR -> RGB。这里 ::-1 表示反转最后一个通道维度。
    array = array[:, :, ::-1]
    return array


def decode_depth_image_to_meters(image):
    """
    把 CARLA depth camera 图像解码成“米”。

    CARLA depth camera 不是直接给 float depth，而是把深度编码在 RGB 三个通道里。
    官方解码公式：

      normalized = (R + G * 256 + B * 256 * 256) / (256^3 - 1)
      depth_m    = 1000 * normalized

    注意 raw_data 是 BGRA，所以 array[:,:,2] 才是 R。

    返回：
      depth_meters, shape=(height, width), float32
    """
    # depth camera 的 raw_data 同样是 BGRA 形式，只是 RGB 三个通道编码的是深度。
    array = np.frombuffer(image.raw_data, dtype=np.uint8)
    array = np.reshape(array, (image.height, image.width, 4)).astype(np.float32)

    b = array[:, :, 0]
    g = array[:, :, 1]
    r = array[:, :, 2]

    # 三个 8-bit 通道合起来形成一个 24-bit 数值，再归一化到 [0, 1]。
    normalized = (r + g * 256.0 + b * 256.0 * 256.0) / (256.0 ** 3 - 1.0)

    # CARLA depth camera 默认最大可表示 1000 米，所以乘以 1000 得到米。
    return 1000.0 * normalized


def depth_meters_to_grayscale(depth_meters, max_depth=80.0):
    """
    把深度米值转成灰度图，方便 pygame 显示。

    近处亮，远处暗。这里只是教学显示，不改变真实 depth 数值。
    """
    clipped = np.clip(depth_meters, 0.0, max_depth)
    normalized = 1.0 - clipped / max_depth
    gray = (normalized * 255.0).astype(np.uint8)
    rgb = np.dstack([gray, gray, gray])
    return rgb


class CameraSensor(object):
    """
    一个轻量 camera sensor 包装。

    camera_type:
      "sensor.camera.rgb"
      "sensor.camera.depth"

    sensor.listen(callback) 是异步的。
    回调里只保存 latest_image/latest_array，lesson 主循环再读取。
    """

    def __init__(
        self,
        world,
        vehicle,
        camera_type="sensor.camera.rgb",
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        fov=CAMERA_FOV,
        transform=DRIVER_CAMERA_TRANSFORM,
        sensor_tick="0.0",
    ):
        self.world = world
        self.vehicle = vehicle
        self.camera_type = camera_type
        self.width = width
        self.height = height
        self.fov = fov
        self.transform = transform

        # 根据 camera_type 找到相机模板。
        # RGB 和 Depth 的创建方式几乎一样，只是 type_id 不同。
        bp = world.get_blueprint_library().find(camera_type)
        bp.set_attribute("image_size_x", str(width))
        bp.set_attribute("image_size_y", str(height))
        bp.set_attribute("fov", str(fov))
        bp.set_attribute("sensor_tick", sensor_tick)

        # attach_to=vehicle 表示相机跟随车辆运动。
        # transform 是相对车辆局部坐标的安装位姿，不是世界坐标。
        self.actor = world.spawn_actor(
            bp,
            transform,
            attach_to=vehicle,
            attachment_type=carla.AttachmentType.Rigid,
        )

        self.latest_image = None
        self.latest_rgb = None
        self.latest_depth_m = None

        # sensor 回调可能在对象销毁后仍被短暂触发。
        # weakref 可以避免回调强行持有 self，减少退出时的引用问题。
        weak_self = weakref.ref(self)
        self.actor.listen(lambda image: CameraSensor._on_image(weak_self, image))

    @staticmethod
    def _on_image(weak_self, image):
        self = weak_self()
        if self is None:
            return

        # 保存最近一帧原始 CARLA image，里面有 frame/timestamp/raw_data。
        self.latest_image = image

        if self.camera_type == "sensor.camera.depth":
            # Depth 相机：先解码成米，再转灰度图用于显示。
            self.latest_depth_m = decode_depth_image_to_meters(image)
            self.latest_rgb = depth_meters_to_grayscale(self.latest_depth_m)
        else:
            # RGB 相机：把 CARLA BGRA 转成普通 RGB numpy 图像。
            self.latest_rgb = carla_bgra_to_rgb_array(image)

    def get_transform(self):
        return self.actor.get_transform()


# =============================================================================
# 5. pygame 显示与车辆键盘控制
# =============================================================================

def make_pygame_surface(pygame, rgb_array):
    """
    numpy RGB 图像 -> pygame surface。

    numpy 图像 shape 是：
      (height, width, channel)

    pygame.surfarray.make_surface 需要：
      (width, height, channel)

    所以要 swapaxes(0, 1)。
    """
    return pygame.surfarray.make_surface(rgb_array.swapaxes(0, 1))


def get_keyboard_vehicle_control(pygame, keys, current_steer):
    """
    pygame 键盘状态 -> carla.VehicleControl。

    这段是你后续做自定义 UI 的基础：
      读取 pygame.key.get_pressed()
      生成 VehicleControl
      vehicle.apply_control(control)

    注意：
      只有 pygame 窗口获得焦点时，pygame 才能收到按键。
      所以运行后要点击 pygame 窗口开车。
    """
    # VehicleControl 是 CARLA 给车辆的低层控制命令：
    # throttle 油门、brake 刹车、steer 方向、reverse 倒挡。
    control = carla.VehicleControl()

    throttle = 0.0
    brake = 0.0
    reverse = False

    # W/上箭头：前进。这里设置一个固定油门，教学阶段够用。
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        throttle = 0.55
        reverse = False

    # S/下箭头：倒车。CARLA 里倒车通常是 reverse=True + throttle。
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        throttle = 0.45
        reverse = True

    # 空格：刹车，优先级高于油门。
    if keys[pygame.K_SPACE]:
        throttle = 0.0
        brake = 1.0
        reverse = False

    steer_step = 0.04
    # 方向盘不是瞬间从 0 跳到最大，而是逐帧递增/递减。
    # 这样开起来更平滑，也更接近真实方向盘。
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        current_steer -= steer_step
    elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        current_steer += steer_step
    else:
        # 松开方向键后，让方向盘慢慢回正。
        if current_steer > 0.0:
            current_steer -= steer_step
        elif current_steer < 0.0:
            current_steer += steer_step

    current_steer = max(-0.75, min(0.75, current_steer))
    if abs(current_steer) < 0.03:
        current_steer = 0.0

    control.throttle = throttle
    control.brake = brake
    control.steer = current_steer
    control.reverse = reverse
    return control, current_steer


def draw_text_lines(pygame, display, font, lines, x=18, y=16, line_height=23):
    """在 pygame 窗口左上角绘制多行文字。"""
    for i, line in enumerate(lines):
        surface = font.render(line, True, (255, 255, 255))
        display.blit(surface, (x, y + i * line_height))


# =============================================================================
# 6. 几何：相机内参、外参、投影、反投影
# =============================================================================

def build_camera_intrinsic_k(width, height, fov_degrees):
    """
    构造针孔相机内参矩阵 K（Camera Intrinsic Matrix）。

    什么是相机内参矩阵？
      - 它描述了相机的内部属性：焦距、主点、像素尺寸等
      - 用于将 3D 相机坐标投影到 2D 图像平面
      - 是计算机视觉中最基础的数学工具之一

    K 矩阵的结构：
      | fx   0  cx |
      |  0  fy  cy |
      |  0   0   1 |

    参数含义：
      - fx, fy: 焦距（单位：像素），决定视野大小
      - cx, cy: 主点（principal point），通常是图像中心 (width/2, height/2)

    CARLA camera 的 fov 是水平视场角（Horizontal FOV）。
    焦距计算公式：
      fx = width / (2 * tan(fov / 2))

    Args:
        width: 图像宽度（像素）
        height: 图像高度（像素）
        fov_degrees: 水平视场角（度），CARLA 默认 90 度

    Returns:
        numpy.ndarray: 3x3 的相机内参矩阵

    使用示例：
        k = build_camera_intrinsic_k(1280, 720, 90.0)
        # 现在可以用 k 将 3D 点投影到 2D 像素坐标
    """
    # FOV 越大，焦距越小；同样的空间偏移投影到图像上的像素偏移越小
    # 可以想象：广角镜头（大 FOV）看到的物体更小，长焦镜头（小 FOV）看到的物体更大
    focal = width / (2.0 * math.tan(math.radians(fov_degrees) / 2.0))

    # 从单位矩阵开始填 fx/fy/cx/cy，避免手写完整矩阵出错
    k = np.identity(3)
    k[0, 0] = focal      # fx
    k[1, 1] = focal      # fy
    k[0, 2] = width / 2.0   # cx (图像中心 x)
    k[1, 2] = height / 2.0  # cy (图像中心 y)
    return k


def world_to_camera_ue(location, camera_transform):
    """
    世界坐标点 -> CARLA camera 局部坐标。

    使用 camera_transform.get_inverse_matrix()。

    输出仍然是 CARLA/UE 风格的 camera 坐标：
      x：相机前方
      y：相机右方
      z：相机上方
    """
    # camera_transform 是 camera local -> world。
    # 要把 world 点转到 camera local，需要取逆矩阵。
    world_to_camera = np.array(camera_transform.get_inverse_matrix())
    return np.dot(world_to_camera, location_to_homogeneous(location))


def camera_ue_to_camera_cv(point_ue):
    """
    CARLA/UE camera 坐标 -> OpenCV camera 坐标。

    CARLA camera local:
      x forward
      y right
      z up

    OpenCV camera:
      x right
      y down
      z forward

    所以：
      x_cv = y_ue
      y_cv = -z_ue
      z_cv = x_ue
    """
    return np.array([point_ue[1], -point_ue[2], point_ue[0]], dtype=float)


def camera_cv_to_camera_ue(point_cv):
    """
    OpenCV camera 坐标 -> CARLA/UE camera 坐标。

    上面变换的反变换：
      x_ue = z_cv
      y_ue = x_cv
      z_ue = -y_cv
    """
    return np.array([point_cv[2], point_cv[0], -point_cv[1]], dtype=float)


def camera_cv_to_pixel(point_cv, k):
    """
    OpenCV camera 坐标 -> 像素坐标。

    针孔模型：
      [u, v, 1]^T = K * [x/z, y/z, 1]^T

    更常写成：
      u = fx * x / z + cx
      v = fy * y / z + cy
    """
    x, y, z = point_cv

    # z <= 0 表示点在相机后面，无法投影到前方成像平面。
    if z <= 0.05:
        return None

    # K * [x, y, z] 得到的是齐次像素坐标，还要除以第三维 z。
    projected = np.dot(k, point_cv)
    u = projected[0] / projected[2]
    v = projected[1] / projected[2]
    return float(u), float(v), float(z)


def world_to_pixel(location, camera_transform, k, image_w, image_h, margin=0.0):
    """
    将世界坐标点投影到图像像素坐标。

    这是 AR（增强现实）的核心函数！
    它完成了从 3D 世界到 2D 图像的完整投影链路。

    完整投影链路：
      1. 世界坐标 (World Frame)
         ↓ (通过相机外参：旋转+平移)
      2. 相机坐标 (Camera UE Frame: x前, y右, z上)
         ↓ (坐标系转换：UE -> OpenCV)
      3. 相机坐标 (Camera CV Frame: x右, y下, z前)
         ↓ (通过相机内参 K：透视投影)
      4. 像素坐标 (Pixel Frame: u, v)

    Args:
        location: 世界坐标点 (carla.Location)
        camera_transform: 相机的位姿 (位置和旋转)
        k: 相机内参矩阵 (3x3)
        image_w: 图像宽度（像素）
        image_h: 图像高度（像素）
        margin: 允许的边界溢出（像素），用于绘制超出屏幕的箭头

    Returns:
        tuple: (u, v, depth) 或 None
          - u, v: 像素坐标
          - depth: 沿相机前方的距离（OpenCV 相机坐标系的 z）
          - 如果点在相机后面或超出屏幕，返回 None

    使用示例：
        # 将车辆前方 10 米的点投影到图像上
        target_world = ground_point_in_vehicle_frame(world, vehicle, 10.0, 0.0)
        pixel = world_to_pixel(target_world, camera.get_transform(), k, 1280, 720)
        if pixel:
            u, v, depth = pixel
            print(f"目标点在图像上的位置: ({u}, {v}), 距离: {depth}米")
    """
    # 1. 世界坐标 -> CARLA/UE 相机坐标
    # 使用相机的逆矩阵，将世界点转换到相机局部坐标系
    point_ue = world_to_camera_ue(location, camera_transform)

    # 2. CARLA/UE 相机坐标 -> OpenCV 相机坐标
    # CARLA: x前, y右, z上 -> OpenCV: x右, y下, z前
    point_cv = camera_ue_to_camera_cv(point_ue)

    # 3. OpenCV 相机坐标 -> 像素坐标
    # 使用内参矩阵 K 进行透视投影
    pixel = camera_cv_to_pixel(point_cv, k)

    if pixel is None:
        return None

    u, v, depth = pixel
    # margin 允许点稍微超出屏幕，画箭头多边形时更宽容
    # 例如 margin=100 表示允许点在屏幕外 100 像素范围内仍然有效
    if u < -margin or u >= image_w + margin:
        return None
    if v < -margin or v >= image_h + margin:
        return None

    return u, v, depth


def pixel_depth_to_camera_cv(u, v, depth_m, k):
    """
    像素坐标 + depth -> OpenCV camera 坐标。

    已知：
      u = fx*x/z + cx
      v = fy*y/z + cy
      z = depth

    反解：
      x = (u - cx) / fx * z
      y = (v - cy) / fy * z
      z = depth

    注意：
      这里的 depth 必须是沿相机前方的 z，而不是欧氏距离。
      CARLA depth camera 的值可用于这个教学近似。
    """
    # 先从 K 里取出四个内参。
    fx = k[0, 0]
    fy = k[1, 1]
    cx = k[0, 2]
    cy = k[1, 2]

    # 把像素偏移量还原成相机坐标中的米制偏移。
    x = (u - cx) / fx * depth_m
    y = (v - cy) / fy * depth_m
    z = depth_m
    return np.array([x, y, z], dtype=float)


def camera_ue_point_to_world(point_ue, camera_transform):
    """
    CARLA camera 局部坐标点 -> 世界坐标点。
    """
    camera_to_world = np.array(camera_transform.get_matrix())
    point_h = np.array([point_ue[0], point_ue[1], point_ue[2], 1.0], dtype=float)
    world_point = np.dot(camera_to_world, point_h)
    return homogeneous_to_location(world_point)


def pixel_depth_to_world(u, v, depth_m, camera_transform, k):
    """
    像素坐标 + depth -> 世界坐标。

    完整链路：
      pixel + depth
        -> camera CV coordinate
        -> camera UE coordinate
        -> world coordinate
    """
    point_cv = pixel_depth_to_camera_cv(u, v, depth_m, k)
    point_ue = camera_cv_to_camera_ue(point_cv)
    return camera_ue_point_to_world(point_ue, camera_transform)


def pixel_to_world_on_ground(u, v, camera_transform, k, ground_z):
    """
    像素点 -> 地面世界点。

    这个函数不用 depth camera，而是假设像素点落在 z=ground_z 的地面平面上。
    它适合下面这种情况：
      模型检测到“路面上的一个点”
      你想知道这个点在 CARLA world 里大概在哪里

    做法：
      1. 像素点通过 K^-1 得到相机坐标系下的一条射线；
      2. 射线转到世界坐标；
      3. 和地面平面 z=ground_z 求交点。
    """
    # 从内参矩阵中取出焦距和主点。
    fx = k[0, 0]
    fy = k[1, 1]
    cx = k[0, 2]
    cy = k[1, 2]

    # 先在 OpenCV camera 坐标里构造一条 z=1 的方向射线。
    # 把像素点变成归一化相机坐标。
    # 这里令 z=1，得到的是一条射线方向，而不是一个固定距离的点。
    x_cv = (u - cx) / fx
    y_cv = (v - cy) / fy
    ray_cv = np.array([x_cv, y_cv, 1.0], dtype=float)

    # 转成 CARLA/UE camera 局部方向。
    # 转成 CARLA/UE 相机局部坐标方向。
    ray_ue = camera_cv_to_camera_ue(ray_cv)

    # 把射线起点和射线上一点从 camera local 转到 world。
    camera_to_world = np.array(camera_transform.get_matrix())
    origin_local = np.array([0.0, 0.0, 0.0, 1.0], dtype=float)
    ray_point_local = np.array([ray_ue[0], ray_ue[1], ray_ue[2], 1.0], dtype=float)

    origin_world = np.dot(camera_to_world, origin_local)
    ray_point_world = np.dot(camera_to_world, ray_point_local)
    # 两个世界点相减，得到世界坐标下的射线方向。
    direction_world = ray_point_world - origin_world

    # 如果射线几乎平行于地面平面，就无法稳定求交。
    if abs(direction_world[2]) < 1e-8:
        return None

    # 解方程：origin.z + scale * direction.z = ground_z。
    scale = (ground_z - origin_world[2]) / direction_world[2]
    if scale <= 0.0:
        return None

    # scale > 0 表示交点在相机前方。
    hit = origin_world + scale * direction_world
    return homogeneous_to_location(hit)


# =============================================================================
# 7. AR 箭头几何和调试绘制
# =============================================================================

def make_ground_arrow_polygon(start, end, width=1.2):
    """
    用 start/end 两个地面世界点构造一个箭头多边形。

    返回：
      [carla.Location, carla.Location, ...]

    这个多边形还不是像素，它仍然在 CARLA world 坐标中。
    后续用 world_to_pixel 把每个顶点投影到图像上，再用 pygame.draw.polygon 绘制。
    """
    # 箭头方向由 start 指向 end，只在地面 x/y 平面上计算。
    dx = end.x - start.x
    dy = end.y - start.y
    length = math.sqrt(dx * dx + dy * dy)
    if length < 0.5:
        return []

    # 单位前向向量。
    fx = dx / length
    fy = dy / length

    # 与 forward 垂直的右向量。
    # 与前向向量垂直的右向量，用来给箭头生成宽度。
    rx = -fy
    ry = fx

    # 箭头头部不能太短，也不能超过总长度的一半，否则近距离会变形。
    head_len = min(max(width * 1.8, 0.8), length * 0.45)
    body_half = width * 0.22
    head_half = width * 0.58
    neck_x = end.x - fx * head_len
    neck_y = end.y - fy * head_len
    z = max(start.z, end.z)

    def p(x, y):
        return carla.Location(x=float(x), y=float(y), z=float(z))

    # 按顺时针/逆时针顺序返回多边形顶点，pygame.draw.polygon 才能正确填充。
    return [
        p(start.x + rx * body_half, start.y + ry * body_half),
        p(neck_x + rx * body_half, neck_y + ry * body_half),
        p(neck_x + rx * head_half, neck_y + ry * head_half),
        p(end.x, end.y),
        p(neck_x - rx * head_half, neck_y - ry * head_half),
        p(neck_x - rx * body_half, neck_y - ry * body_half),
        p(start.x - rx * body_half, start.y - ry * body_half),
    ]


def project_polygon_to_pixels(locations, camera_transform, k, image_w, image_h, margin=120.0):
    """把一组世界点投影成 pygame 可用的像素点列表。"""
    pixels = []
    for loc in locations:
        pixel = world_to_pixel(loc, camera_transform, k, image_w, image_h, margin)
        if pixel is None:
            return None
        pixels.append((int(pixel[0]), int(pixel[1])))
    return pixels


def debug_draw_point(world, location, color=None, text=None, life_time=0.08):
    """在 UE/CARLA 世界里画一个调试点。"""
    color = color or carla.Color(0, 255, 0)
    world.debug.draw_point(location, size=0.12, color=color, life_time=life_time)
    if text:
        label_location = carla.Location(location.x, location.y, location.z + 0.45)
        world.debug.draw_string(
            label_location,
            text,
            draw_shadow=False,
            color=color,
            life_time=life_time,
        )


def debug_draw_arrow(world, start, end, color=None, life_time=0.08):
    """在 UE/CARLA 世界里画一个调试箭头。"""
    color = color or carla.Color(255, 100, 0)
    world.debug.draw_arrow(
        start,
        end,
        thickness=0.08,
        arrow_size=0.7,
        color=color,
        life_time=life_time,
    )


# =============================================================================
# 8. 车辆速度、角度、简单滤波
# =============================================================================

def normalize_angle_rad(angle):
    """把弧度角限制到 [-pi, pi]，避免角度差跨越 180 度时跳变。"""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def get_forward_speed(vehicle):
    """
    获取车辆沿车头方向的速度。

    vehicle.get_velocity() 返回 world 坐标下的速度向量。
    我们把它投影到车辆 forward vector 上：
      speed = velocity dot forward

    好处：
      前进是正数，倒车是负数；
      不会把 z 方向颠簸误算成前进距离。
    """
    velocity = vehicle.get_velocity()
    forward = vehicle.get_transform().get_forward_vector()
    return (
        velocity.x * forward.x +
        velocity.y * forward.y +
        velocity.z * forward.z
    )


def get_planar_speed(vehicle):
    """水平面速度大小，只用于显示参考。"""
    velocity = vehicle.get_velocity()
    return math.sqrt(velocity.x * velocity.x + velocity.y * velocity.y)


class ExponentialLocationFilter(object):
    """
    一个非常简单的位置低通滤波器。

    真实检测点会抖：
      一帧在左边一点，下一帧在右边一点。
    反投影到远处地面后，这种像素抖动会被放大。

    指数滑动平均：
      filtered = (1-alpha) * old + alpha * measurement

    alpha 越大：
      跟得越快，但越抖。
    alpha 越小：
      越平滑，但延迟越大。
    """

    def __init__(self, alpha=0.25):
        self.alpha = alpha
        self.location = None

    def reset(self):
        self.location = None

    def update(self, measurement):
        if measurement is None:
            # 没有新观测时，沿用上一次滤波结果。
            return self.location

        if self.location is None:
            # 第一帧没有历史值，直接用当前测量初始化。
            self.location = carla.Location(measurement.x, measurement.y, measurement.z)
            return self.location

        a = self.alpha
        # 指数滑动平均：新值占 alpha，旧值占 1-alpha。
        self.location.x = (1.0 - a) * self.location.x + a * measurement.x
        self.location.y = (1.0 - a) * self.location.y + a * measurement.y
        self.location.z = measurement.z
        return self.location


def sleep_seconds(seconds):
    """简单等待，给一些无 pygame 的 lesson 留出观察 debug draw 的时间。"""
    time.sleep(seconds)
