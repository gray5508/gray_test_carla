"""
common.py

这一组 lesson 共用的小工具。

设计原则：
1. 尽量只封装重复代码，不把关键数学藏起来；
2. 每个函数都保留中文注释，方便你边运行边对照理解；
3. 坐标转换函数尽量显式写出 CARLA/相机/OpenCV 坐标之间的关系。

当前本机环境：
  CARLA root: D:\\HST_WORK\\carla\\WindowsNoEditor
  conda env : C:\\Users\\cicii\\miniconda3\\envs\\carla_test
  Python    : 3.7
  CARLA     : 0.9.15
"""

import glob
import math
import os
import sys
import time
import weakref

import numpy as np


# ---------------------------------------------------------------------------
# 0. CARLA PythonAPI 导入兜底
# ---------------------------------------------------------------------------

DEFAULT_CARLA_ROOT = r"D:\HST_WORK\carla\WindowsNoEditor"


def add_carla_python_api(carla_root=None):
    """
    你的 conda 环境已经安装了 carla==0.9.15，正常情况下直接 import carla 即可。

    这里仍然加一个兜底：
    如果某天换环境后 import carla 失败，可以把 CARLA_ROOT 指向 WindowsNoEditor，
    本函数会把 PythonAPI/carla/dist 里的 egg 加到 sys.path。
    """
    carla_root = carla_root or os.environ.get("CARLA_ROOT", DEFAULT_CARLA_ROOT)
    platform_tag = "win-amd64" if os.name == "nt" else "linux-x86_64"
    egg_pattern = os.path.join(
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

    matches = glob.glob(egg_pattern)
    if matches:
        sys.path.append(matches[0])


try:
    import carla
except ImportError:
    add_carla_python_api()
    import carla


# ---------------------------------------------------------------------------
# 1. 基础配置
# ---------------------------------------------------------------------------

HOST = "localhost"
PORT = 2000
TIMEOUT = 30.0

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
CAMERA_FOV = 90.0


# 沿用你现有 manual_drive_trajectory_compare.py 里的固定起点。
START_TRANSFORM = carla.Transform(
    carla.Location(x=55.754353, y=130.663452, z=0.500000),
    carla.Rotation(pitch=0.000000, yaw=180.320450, roll=0.000000),
)


DRIVER_CAMERA_TRANSFORM = carla.Transform(
    # CARLA 车辆局部坐标：
    #   x 正方向：车头
    #   y 正方向：车辆右侧
    #   z 正方向：向上
    # y=-0.35 表示偏左，模拟左舵驾驶位。
    carla.Location(x=1.25, y=-0.35, z=1.35),
    carla.Rotation(pitch=-4.0, yaw=0.0, roll=0.0),
)


def connect_client(host=HOST, port=PORT, timeout=TIMEOUT):
    """
    创建 CARLA client 并获取 world。

    运行这些 lesson 前，请你先启动 CARLA server：
      D:\\HST_WORK\\carla\\WindowsNoEditor\\CarlaUE4.exe -carla-rpc-port=2000
    """
    client = carla.Client(host, port)
    client.set_timeout(timeout)
    world = client.get_world()
    return client, world


def print_environment_summary(world):
    """打印最常用的环境信息。"""
    settings = world.get_settings()
    print("Connected to CARLA.")
    print("Map:", world.get_map().name)
    print("Actors:", len(world.get_actors()))
    print("Synchronous mode:", settings.synchronous_mode)
    print("Fixed delta seconds:", settings.fixed_delta_seconds)


# ---------------------------------------------------------------------------
# 2. Actor 创建与清理
# ---------------------------------------------------------------------------

def spawn_ego_vehicle(world, transform=START_TRANSFORM):
    """
    生成一辆手动车。

    这里优先用 Tesla Model 3，是 CARLA 示例里常用、行为稳定的车辆。
    try_spawn_actor 失败时通常表示出生点被占用，可以先清掉之前残留 actor，
    或者把 z 调高一点、换一个 spawn point。
    """
    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.filter("vehicle.tesla.model3")[0]
    vehicle_bp.set_attribute("role_name", "hero")

    vehicle = world.try_spawn_actor(vehicle_bp, transform)
    if vehicle is None:
        raise RuntimeError(
            "车辆生成失败：起点可能被其他 actor 占用。"
            "请先关闭旧脚本，或在 CARLA 中清理残留车辆。"
        )

    vehicle.set_autopilot(False)
    vehicle.set_transform(transform)
    return vehicle


def destroy_actors(actors):
    """
    统一清理 actor。

    sensor 需要先 stop 再 destroy；普通 vehicle 直接 destroy 即可。
    清理失败时不抛出异常，避免退出阶段被二次错误打断。
    """
    for actor in reversed([a for a in actors if a is not None]):
        try:
            if hasattr(actor, "stop"):
                actor.stop()
        except RuntimeError:
            pass

        try:
            actor.destroy()
        except RuntimeError:
            pass


class RgbCamera(object):
    """
    一个最小 RGB camera 包装。

    CARLA sensor.listen 是异步回调：新图像来了以后回调函数会被调用。
    lesson 主循环只读取 latest_image/latest_rgb，理解起来比完整队列同步更轻。
    """

    def __init__(
        self,
        world,
        vehicle,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        fov=CAMERA_FOV,
        transform=DRIVER_CAMERA_TRANSFORM,
        sensor_tick="0.0",
    ):
        self.world = world
        self.vehicle = vehicle
        self.width = width
        self.height = height
        self.fov = fov
        self.transform = transform

        blueprint_library = world.get_blueprint_library()
        camera_bp = blueprint_library.find("sensor.camera.rgb")
        camera_bp.set_attribute("image_size_x", str(width))
        camera_bp.set_attribute("image_size_y", str(height))
        camera_bp.set_attribute("fov", str(fov))
        camera_bp.set_attribute("sensor_tick", sensor_tick)

        self.actor = world.spawn_actor(
            camera_bp,
            transform,
            attach_to=vehicle,
            attachment_type=carla.AttachmentType.Rigid,
        )

        self.latest_image = None
        self.latest_rgb = None

        weak_self = weakref.ref(self)
        self.actor.listen(lambda image: RgbCamera._on_image(weak_self, image))

    @staticmethod
    def _on_image(weak_self, image):
        self = weak_self()
        if self is None:
            return

        self.latest_image = image
        self.latest_rgb = carla_image_to_rgb_array(image)

    def get_transform(self):
        """返回 camera actor 当前世界位姿。"""
        return self.actor.get_transform()

    def destroy(self):
        destroy_actors([self.actor])
        self.actor = None


# ---------------------------------------------------------------------------
# 3. 图像与键盘控制
# ---------------------------------------------------------------------------

def carla_image_to_rgb_array(image):
    """
    CARLA RGB camera 原始数据是 BGRA。

    pygame / OpenCV 通常更习惯 RGB 或 BGR。
    这里输出 RGB，shape = (height, width, 3)。
    """
    array = np.frombuffer(image.raw_data, dtype=np.uint8)
    array = np.reshape(array, (image.height, image.width, 4))
    array = array[:, :, :3]
    array = array[:, :, ::-1]
    return array


def make_pygame_surface(pygame, rgb_array):
    """
    numpy 图像转 pygame surface。

    pygame.surfarray.make_surface 需要 (width, height, channel)，
    而 numpy 图像是 (height, width, channel)，所以要 swapaxes。
    """
    return pygame.surfarray.make_surface(rgb_array.swapaxes(0, 1))


def get_keyboard_vehicle_control(pygame, keys, current_steer):
    """
    pygame 输入 -> carla.VehicleControl。

    这套输入只在 pygame 窗口获得焦点时生效，不会和 UE spectator 的 WASD
    自由相机抢控制权。运行后请点击 pygame 窗口。
    """
    control = carla.VehicleControl()

    throttle = 0.0
    brake = 0.0
    reverse = False

    if keys[pygame.K_UP] or keys[pygame.K_w]:
        throttle = 0.55
        reverse = False

    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        throttle = 0.45
        reverse = True

    if keys[pygame.K_SPACE]:
        throttle = 0.0
        brake = 1.0
        reverse = False

    steer_increment = 0.04
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        current_steer -= steer_increment
    elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        current_steer += steer_increment
    else:
        if current_steer > 0.0:
            current_steer -= steer_increment
        elif current_steer < 0.0:
            current_steer += steer_increment

    current_steer = max(-0.75, min(0.75, current_steer))
    if abs(current_steer) < 0.03:
        current_steer = 0.0

    control.throttle = throttle
    control.brake = brake
    control.steer = current_steer
    control.reverse = reverse
    control.hand_brake = False
    control.manual_gear_shift = False

    return control, current_steer


def get_forward_speed(vehicle):
    """
    车辆速度向车头方向投影。

    forward_speed 比 3D speed 更适合做平面轨迹积分：
    车辆刚生成或颠簸时 z 方向可能有速度，3D speed 会误把它算成前进距离。
    """
    velocity = vehicle.get_velocity()
    forward = vehicle.get_transform().get_forward_vector()
    return (
        velocity.x * forward.x +
        velocity.y * forward.y +
        velocity.z * forward.z
    )


def draw_text_lines(pygame, display, font, lines, x=18, y=16, line_height=23):
    """左上角 HUD 文本。"""
    for i, line in enumerate(lines):
        surface = font.render(line, True, (255, 255, 255))
        display.blit(surface, (x, y + i * line_height))


# ---------------------------------------------------------------------------
# 4. CARLA 世界坐标 / 车辆局部坐标
# ---------------------------------------------------------------------------

def location_to_np(location):
    return np.array([location.x, location.y, location.z, 1.0], dtype=float)


def np_to_location(values):
    return carla.Location(
        x=float(values[0]),
        y=float(values[1]),
        z=float(values[2]),
    )


def transform_local_location(parent_transform, local_location):
    """
    把 actor 局部坐标点转换成世界坐标点。

    例子：
      local_location = carla.Location(x=10, y=0, z=0)
    表示车辆前方 10 米。经过 vehicle.get_transform() 变换后，
    得到它在 CARLA world 里的 x/y/z。
    """
    matrix = np.array(parent_transform.get_matrix())
    world_point = np.dot(matrix, location_to_np(local_location))
    return np_to_location(world_point)


def get_ground_z(world, location):
    """
    获取 location 附近车道中心线的 z。

    对 AR 贴地绘制来说，z 需要略高于路面，避免投影和地面重合时闪烁。
    如果 waypoint 查询失败，就退回 location.z。
    """
    try:
        waypoint = world.get_map().get_waypoint(
            location,
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )
        if waypoint is not None:
            return waypoint.transform.location.z
    except RuntimeError:
        pass

    return location.z


def ground_point_from_vehicle(world, vehicle, forward_m, right_m=0.0, z_offset=0.04):
    """
    从车辆局部坐标取一个路面点。

    forward_m：车头前方多少米
    right_m  ：车辆右侧多少米，负数就是左侧
    """
    vehicle_transform = vehicle.get_transform()
    rough_point = transform_local_location(
        vehicle_transform,
        carla.Location(x=forward_m, y=right_m, z=0.0),
    )
    rough_point.z = get_ground_z(world, rough_point) + z_offset
    return rough_point


def print_vehicle_axes(vehicle):
    """
    打印车辆局部坐标轴在世界坐标里的方向。

    你后续做坐标变换时，经常要确认：
      local +X 是否真的是车头方向；
      yaw 的 cos/sin 是否和 forward vector 对齐。
    """
    transform = vehicle.get_transform()
    loc = transform.location
    rot = transform.rotation
    forward = transform.get_forward_vector()
    right = transform.get_right_vector()
    up = transform.get_up_vector()

    yaw_rad = math.radians(rot.yaw)

    print("\nVehicle transform:")
    print("  location: x={:.3f}, y={:.3f}, z={:.3f}".format(loc.x, loc.y, loc.z))
    print("  rotation: pitch={:.3f}, yaw={:.3f}, roll={:.3f}".format(
        rot.pitch, rot.yaw, rot.roll
    ))
    print("\nLocal axes expressed in world frame:")
    print("  +X forward: ({:.4f}, {:.4f}, {:.4f})".format(
        forward.x, forward.y, forward.z
    ))
    print("  +Y right:   ({:.4f}, {:.4f}, {:.4f})".format(
        right.x, right.y, right.z
    ))
    print("  +Z up:      ({:.4f}, {:.4f}, {:.4f})".format(up.x, up.y, up.z))
    print("\nYaw check:")
    print("  cos(yaw), sin(yaw): ({:.4f}, {:.4f})".format(
        math.cos(yaw_rad), math.sin(yaw_rad)
    ))
    print("  forward x/y:        ({:.4f}, {:.4f})".format(forward.x, forward.y))


# ---------------------------------------------------------------------------
# 5. 相机内参、外参、投影
# ---------------------------------------------------------------------------

def build_camera_matrix(width, height, fov_degrees):
    """
    根据 CARLA camera 的 fov 和图像尺寸构造 pinhole camera 内参矩阵 K。

    K = [[fx,  0, cx],
         [ 0, fy, cy],
         [ 0,  0,  1]]

    CARLA 的像素通常是正方形，所以 fx == fy。
    """
    focal = width / (2.0 * math.tan(math.radians(fov_degrees) / 2.0))
    k = np.identity(3)
    k[0, 0] = focal
    k[1, 1] = focal
    k[0, 2] = width / 2.0
    k[1, 2] = height / 2.0
    return k


def world_to_camera_ue(location, camera_transform):
    """
    世界坐标点 -> camera sensor 局部坐标。

    注意这里还是 CARLA/UE 风格的 sensor 局部坐标：
      x: camera 前方
      y: camera 右方
      z: camera 上方
    """
    world_2_camera = np.array(camera_transform.get_inverse_matrix())
    sensor_point = np.dot(world_2_camera, location_to_np(location))
    return sensor_point


def world_to_pixel(location, camera_transform, k, image_w, image_h, margin=0.0):
    """
    世界坐标点 -> 图像像素点。

    CARLA/UE camera 局部坐标与标准 OpenCV camera 坐标不同：
      CARLA local:   (x forward, y right, z up)
      OpenCV camera: (x right,   y down,  z forward)

    因此：
      (x_ue, y_ue, z_ue) -> (x_cv, y_cv, z_cv)
      (x_cv, y_cv, z_cv) = (y_ue, -z_ue, x_ue)
    """
    sensor_point = world_to_camera_ue(location, camera_transform)

    # sensor_point[0] 是点在 camera 前方的距离。<=0 表示在相机后面。
    if sensor_point[0] <= 0.05:
        return None

    point_cv = np.array([
        sensor_point[1],
        -sensor_point[2],
        sensor_point[0],
    ])

    projected = np.dot(k, point_cv)
    u = projected[0] / projected[2]
    v = projected[1] / projected[2]
    depth = projected[2]

    if u < -margin or u >= image_w + margin:
        return None
    if v < -margin or v >= image_h + margin:
        return None

    return float(u), float(v), float(depth)


def pixel_to_world_on_ground(u, v, camera_transform, k, ground_z):
    """
    图像像素点 -> 地面世界点。

    这是“模型识别到图像里的一个点，然后反推它在路面哪里”的核心。

    假设：
      1. 被识别的点在路面上；
      2. 路面局部可近似为 z = ground_z 的平面；
      3. camera 内参 K 和 camera_transform 已知。

    做法：
      1. 像素点通过 K^-1 变成相机坐标系下的一条射线；
      2. 把射线从 camera local 转到 CARLA world；
      3. 求射线与地面平面 z=ground_z 的交点。
    """
    fx = k[0, 0]
    fy = k[1, 1]
    cx = k[0, 2]
    cy = k[1, 2]

    x_cv = (u - cx) / fx
    y_cv = (v - cy) / fy

    # OpenCV camera ray: (x right, y down, z forward)
    # 转回 CARLA camera local:
    #   x_ue = z_cv = 1
    #   y_ue = x_cv
    #   z_ue = -y_cv
    local_origin = np.array([0.0, 0.0, 0.0, 1.0])
    local_ray_point = np.array([1.0, x_cv, -y_cv, 1.0])

    camera_2_world = np.array(camera_transform.get_matrix())
    world_origin = np.dot(camera_2_world, local_origin)
    world_ray_point = np.dot(camera_2_world, local_ray_point)

    direction = world_ray_point - world_origin

    if abs(direction[2]) < 1e-6:
        return None

    scale = (ground_z - world_origin[2]) / direction[2]
    if scale <= 0.0:
        return None

    hit = world_origin + scale * direction
    return np_to_location(hit)


# ---------------------------------------------------------------------------
# 6. 贴地箭头几何
# ---------------------------------------------------------------------------

def make_arrow_polygon(start, end, width=1.1):
    """
    根据路面上的 start/end 两个世界点，构造一个箭头多边形。

    start：箭头尾部中心
    end  ：箭头尖端

    返回一组 carla.Location，全部位于同一个 z 高度附近。
    这个多边形可以：
      1. 用 world_to_pixel 投影到 pygame 画面；
      2. 以后换成 UE decal / mesh 贴地绘制时复用同一套世界点。
    """
    dx = end.x - start.x
    dy = end.y - start.y
    length = math.sqrt(dx * dx + dy * dy)

    if length < 0.5:
        return []

    fx = dx / length
    fy = dy / length

    # 右向量。yaw=0 时 forward=(1,0)，right=(0,1)。
    rx = -fy
    ry = fx

    head_len = min(max(width * 1.8, 0.8), length * 0.45)
    body_half = width * 0.22
    head_half = width * 0.55

    neck_x = end.x - fx * head_len
    neck_y = end.y - fy * head_len
    z = max(start.z, end.z)

    def p(x, y):
        return carla.Location(x=float(x), y=float(y), z=float(z))

    return [
        p(start.x + rx * body_half, start.y + ry * body_half),
        p(neck_x + rx * body_half, neck_y + ry * body_half),
        p(neck_x + rx * head_half, neck_y + ry * head_half),
        p(end.x, end.y),
        p(neck_x - rx * head_half, neck_y - ry * head_half),
        p(neck_x - rx * body_half, neck_y - ry * body_half),
        p(start.x - rx * body_half, start.y - ry * body_half),
    ]


def project_locations(locations, camera_transform, k, image_w, image_h, margin=100.0):
    """批量投影世界点，任何点不可见则返回 None。"""
    pixels = []
    for loc in locations:
        pixel = world_to_pixel(loc, camera_transform, k, image_w, image_h, margin)
        if pixel is None:
            return None
        pixels.append((int(pixel[0]), int(pixel[1])))
    return pixels


def draw_debug_ground_arrow(world, start, end, color=None, life_time=0.08):
    """
    在 CARLA 世界里画一个 debug arrow，便于和 pygame 投影结果对照。

    这不是 AR 叠加本身，只是调试辅助。
    """
    if color is None:
        color = carla.Color(255, 80, 20)
    try:
        world.debug.draw_arrow(
            start,
            end,
            thickness=0.08,
            arrow_size=0.7,
            color=color,
            life_time=life_time,
        )
    except RuntimeError:
        pass


def draw_debug_point(world, location, color=None, text=None, life_time=0.08):
    """在 CARLA 世界里标记一个点。"""
    if color is None:
        color = carla.Color(0, 255, 0)
    try:
        world.debug.draw_point(location, size=0.12, color=color, life_time=life_time)
        if text:
            label_location = carla.Location(location.x, location.y, location.z + 0.5)
            world.debug.draw_string(
                label_location,
                text,
                draw_shadow=False,
                color=color,
                life_time=life_time,
            )
    except RuntimeError:
        pass


# ---------------------------------------------------------------------------
# 7. 小工具
# ---------------------------------------------------------------------------

def sleep_with_world_debug(seconds, tick_hz=20):
    """
    简单等待，避免 lesson_01 这种脚本一闪而过。
    """
    end_time = time.time() + seconds
    while time.time() < end_time:
        time.sleep(1.0 / float(tick_hz))
