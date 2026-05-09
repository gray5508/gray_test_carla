"""
07_world_to_pixel_projection.py

本节目标：
  1. 把 CARLA 世界坐标点投影到 RGB camera 图像；
  2. 理解 world -> camera UE -> camera CV -> pixel；
  3. 在 pygame 画面上标记车辆前方的地面点；
  4. 在 CARLA 世界中可视化相机坐标系（RGB 三轴箭头）。

这就是 AR overlay 的半条链：
  world ground point -> image pixel

新增功能：
  - 在相机位置绘制三条细线，直观显示相机的位姿：
    * 暗红色细线：相机右侧方向（X 轴）
    * 暗绿色细线：相机上方方向（Y 轴）
    * 暗蓝色细线：相机前方方向/光轴（Z 轴）
  - 在车辆中心绘制三条细线，直观显示车辆的位姿：
    * 青色细线：车辆右侧方向（X 轴）
    * 品红细线：车辆上方方向（Y 轴）
    * 黄色细线：车辆前方方向/车头（Z 轴）
  - 帮助你理解相机坐标系与世界坐标系的关系
  - 验证相机安装位置和姿态是否正确
  - 对比车辆和相机坐标系的差异
"""

import pygame

from common import CAMERA_FOV
from common import CameraSensor
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import build_camera_intrinsic_k
from common import carla
from common import connect_to_carla
from common import debug_draw_camera_coordinate_system
from common import debug_draw_point
from common import debug_draw_vehicle_coordinate_system
from common import destroy_actors
from common import draw_text_lines
from common import get_keyboard_vehicle_control
from common import ground_point_in_vehicle_frame
from common import make_pygame_surface
from common import spawn_ego_vehicle
from common import world_to_pixel


def draw_pixel_marker(pygame, display, font, pixel, color, label):
    """
    在 pygame 显示界面上绘制像素级别的标记点。
    
    Args:
        pygame: pygame 模块引用（用于调用绘图函数）
        display: pygame.Surface 对象，即主显示窗口
        font: pygame.font.Font 对象，用于渲染文字标签
        pixel: 三元组 (u, v, depth) 或 None
               - u: 像素横坐标（列），从图像左侧开始计算，单位：像素
               - v: 像素纵坐标（行），从图像顶部开始计算，单位：像素  
               - depth: 该点到相机的深度距离，单位：米（沿相机 Z 轴方向）
        color: RGB 颜色元组 (R, G, B)，每个分量范围 0-255，例如 (255, 0, 0) 表示红色
        label: 字符串标签，显示在标记点旁边，如 "5m"、"left" 等
    
    绘制内容：
        1. 实心彩色圆圈（半径 7 像素）- 作为主要标记点
        2. 黑色空心圆环（半径 9 像素，线宽 2）- 作为边框增强可见性  
        3. 文字标签 - 显示标签名称和深度信息，位于标记点右上方 10 像素处
    
    注意：
        - 如果 pixel 为 None（点在视野外或被遮挡），则不绘制任何内容
        - u, v 会被转换为整数，因为像素坐标必须是整数
        - 这种双层圆圈设计确保在不同背景色下都能清晰看到标记点
    """
    if pixel is None:
        return
    u, v, depth = pixel
    center = (int(u), int(v))
    pygame.draw.circle(display, color, center, 7, 0)
    pygame.draw.circle(display, (0, 0, 0), center, 9, 2)
    text = font.render("{} {:.1f}m".format(label, depth), True, color)
    display.blit(text, (center[0] + 10, center[1] - 10))


def main():
    """
    主函数：演示世界坐标点到像素坐标的投影。
    
    学习重点：
      1. 理解完整的投影链路：world -> camera UE -> camera CV -> pixel
      2. 学会使用 world_to_pixel() 函数
      3. 在 pygame 图像上标记车辆前方的地面点
      4. 验证 CARLA debug draw 和 pygame 绘制的位置是否一致
    
    实际应用场景：
      - 这是 AR overlay 的半条链：world ground point -> image pixel
      - 如果你知道某个物体在世界坐标中的位置，可以把它画在相机图像上
      - AR 导航箭头、车道线投影等都基于这个原理
    
    实验流程：
      1. 初始化 pygame 并连接 CARLA
      2. 生成车辆和 RGB 相机
      3. 定义几个测试点（车前方不同距离）
      4. 把每个点从世界坐标投影到像素坐标
      5. 在 pygame 图像和 CARLA 世界中同时标记这些点
    """
    # ========================================================================
    # 第 1 步：初始化 pygame 和 CARLA
    # ========================================================================
    pygame.init()
    pygame.font.init()

    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("07 world point to pixel")
    font = pygame.font.SysFont("Arial", 18)
    # 创建 pygame 时钟对象，用于控制游戏循环的帧率（FPS）
    # 
    # pygame.time.Clock() 的作用：
    #   - 跟踪时间流逝，计算每帧的实际耗时  
    #   - 通过 tick(fps) 方法限制循环速度，确保程序以稳定的帧率运行  
    #   - 防止程序运行过快导致 CPU 占用过高或物理仿真不稳定  
    # 
    # 在本程序中：
    #   - 后续会调用 clock.tick(30)，将帧率限制在 30 FPS  
    #   - 这意味着主循环每秒最多执行 30 次，每帧约 33.3 毫秒  
    #   - 30 FPS 是 CARLA 仿真的常用帧率，平衡了流畅性和计算负载  
    #   - 如果设置为更高（如 60），可能导致 CARLA 服务器跟不上  
    #   - 如果设置为更低（如 10），画面会显得卡顿  
    # 
    # 为什么需要限帧？
    #   1. 稳定性：保证物理仿真、传感器数据采样的时间间隔一致  
    #   2. 可重复性：不同硬件上运行时行为更一致  
    #   3. 资源管理：避免无限制循环占用 100% CPU  
    #   4. 同步需求：与 CARLA 服务器的更新频率匹配（默认 20-30 Hz）  
    clock = pygame.time.Clock()

    # 构建相机内参矩阵 K
    k = build_camera_intrinsic_k(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)
    client, world = connect_to_carla()

    actors = []
    current_steer = 0.0

    try:
        # ====================================================================
        # 第 2 步：生成车辆和相机
        # ====================================================================
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        camera = CameraSensor(world, vehicle, "sensor.camera.rgb")
        actors.append(camera.actor)

        # ====================================================================
        # 第 3 步：游戏主循环
        # ====================================================================
        running = True
        while running:
            clock.tick(30)

            # ---------------------------------------------------------------
            # 3.1 处理事件
            # ---------------------------------------------------------------
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
                    running = False

            # ---------------------------------------------------------------
            # 3.2 控制车辆
            # ---------------------------------------------------------------
            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            # ---------------------------------------------------------------
            # 3.3 显示 RGB 图像
            # ---------------------------------------------------------------
            if camera.latest_rgb is not None:
                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))
            else:
                display.fill((10, 10, 10))

            # ====================================================================
            # 第 4 步：定义测试点并投影到像素坐标（核心演示环节）
            # ====================================================================
            # 这是本节的核心内容：演示如何将世界坐标系中的点投影到 2D 图像像素坐标
            # 
            # 完整的投影链路（4 个步骤）：
            #   world coordinates -> camera UE coordinates -> camera CV coordinates -> pixel coordinates
            # 
            # 【步骤详解】
            # 1. World Coordinates（世界坐标）: CARLA 全局坐标系中的点 (X, Y, Z)
            #    - 原点：地图固定位置，Z 轴向上，X/Y 平面为水平面
            #    - 单位：米（meter）
            # 
            # 2. Camera UE Coordinates（相机 UE 坐标）: 相对于相机的 Unreal Engine 坐标系
            #    - 原点：相机光学中心（镜头中心）
            #    - 坐标轴：X 向右，Y 向上，Z 向前（UE 标准）
            #    - 通过相机 Transform 的逆矩阵将世界坐标转换到此坐标系
            # 
            # 3. Camera CV Coordinates（相机 CV 坐标）: 计算机视觉标准坐标系  
            #    - 原点：相机光学中心（与 UE 相同）
            #    - 坐标轴：X 向右，Y 向下，Z 向前（CV 标准，Y 轴翻转）
            #    - 从 UE 到 CV：只需将 Y 轴取反（Y_cv = -Y_ue）
            # 
            # 4. Pixel Coordinates（像素坐标）: 2D 图像上的像素位置 (u, v)
            #    - 原点：图像左上角（(0, 0) 表示第一行第一列）
            #    - u: 横向坐标（列索引），从左到右递增，范围 [0, WINDOW_WIDTH]
            #    - v: 纵向坐标（行索引），从上到下递增，范围 [0, WINDOW_HEIGHT]
            #    - 通过相机内参矩阵 K 进行透视投影：
            #      [u]   [fx  0  cx] [X/Z]
            #      [v] = [ 0 fy  cy] [Y/Z]  （齐次坐标，最后需要除以 Z）
            #      [1]   [ 0  0   1] [ 1 ]
            #      其中 fx=fy=WINDOW_WIDTH/(2*tan(FOV/2)), cx=WINDOW_WIDTH/2, cy=WINDOW_HEIGHT/2
            # 
            # 【为什么需要这个投影？】
            # - AR 应用：把虚拟物体（导航箭头、车道线）画在真实相机图像上
            # - 目标检测验证：将检测到的物体位置标注回图像进行可视化  
            # - 传感器融合：将激光雷达、毫米波雷达的点云投影到相机图像上进行对比
            # - 自动驾驶可视化：在视频中显示车辆周围的障碍物、路径规划等
            
            # ---------------------------------------------------------------
            # 4.1 获取相机位姿并绘制坐标系
            # ---------------------------------------------------------------
            # 获取相机当前的世界坐标 Transform（包含位置和姿态信息）
            # Transform 是一个 4x4 齐次变换矩阵，描述了相机在世界坐标系中的位姿：
            #   - location: 相机在世界坐标系中的位置 (X, Y, Z)，单位：米  
            #   - rotation: 相机的欧拉角姿态 (pitch, yaw, roll)，单位：度  
            #     * pitch: 俯仰角（上下点头），正值为抬头，负值为低头  
            #     * yaw: 偏航角（左右摇头），正值为左转，负值为右转  
            #     * roll: 翻滚角（左右倾斜），正值为右倾，负值为左倾  
            # 
            # 这个 Transform 用于构建从世界坐标到相机坐标的旋转平移矩阵（外参矩阵）
            camera_tf = camera.get_transform()
            
            # 在 CARLA 世界中绘制相机坐标系（三条细线）
            # - 暗红色细线：相机右侧方向（X 轴）
            # - 暗绿色细线：相机上方方向（Y 轴）
            # - 暗蓝色细线：相机前方方向/光轴（Z 轴）
            # 这样你可以在 UE4 视图中直观地看到相机的位置和朝向
            debug_draw_camera_coordinate_system(world, camera_tf, axis_length=1.0, life_time=0.08)
            
            # 在车辆中心绘制车辆坐标系（三条细线）
            # - 青色细线：车辆右侧方向（X 轴）
            # - 品红细线：车辆上方方向（Y 轴）
            # - 黄色细线：车辆前方方向/车头（Z 轴）
            # 与相机坐标系对比，可以看到相机相对于车辆的安装位置
            debug_draw_vehicle_coordinate_system(world, vehicle, axis_length=2.0, life_time=0.08)
            
            # ---------------------------------------------------------------
            # 4.2 定义测试点
            # ---------------------------------------------------------------
            # 定义 5 个测试点：不同距离和方向的组合，用于全面验证投影算法的正确性
            # 格式：(标签字符串, 前方距离_米, 右侧距离_米, pygame颜色RGB, CARLA调试颜色)
            # 
            # 选择这些点的目的：
            # - 正前方 3 个距离点（5m, 10m, 15m）：验证不同深度的投影准确性，近处和远处的畸变差异
            # - 左右偏移点（±2.5m）：验证横向偏移的投影效果，测试相机视场角覆盖范围  
            # - 所有点都在地面高度（Z=0）：模拟路面标记、车道线等实际应用场景
            samples = [
                ("5m", 5.0, 0.0, (255, 255, 0), carla.Color(255, 255, 0)),     # 黄色：近距离正前方点，应该出现在图像中下部较大位置
                ("10m", 10.0, 0.0, (255, 150, 0), carla.Color(255, 150, 0)),   # 橙色：中等距离正前方点，位置比 5m 点更靠近图像中心（消失点方向）
                ("15m", 15.0, 0.0, (255, 80, 0), carla.Color(255, 80, 0)),     # 深橙色：远距离正前方点，更接近图像中心的消失点，尺寸更小  
                ("left", 10.0, -2.5, (0, 220, 255), carla.Color(0, 220, 255)), # 青色：左前方点（right_m 为负值表示向左偏移），应出现在图像左侧区域  
                ("right", 10.0, 2.5, (255, 0, 255), carla.Color(255, 0, 255)), # 紫色：右前方点（right_m 为正值表示向右偏移），应出现在图像右侧区域  
            ]
            
            # 遍历每个测试点，执行完整的投影流程并在两个地方同时标记：
            #   1. CARLA 3D 世界中的 debug draw（绿色点 + 文字）- 用于验证世界坐标位置正确性  
            #   2. pygame 2D 图像上的像素标记（彩色圆圈 + 文字）- 用于验证投影算法正确性  
            # 
            # 如果两种标记在视觉上对齐（3D 点投影到 2D 后位置一致），说明投影算法正确！
            for label, forward_m, right_m, pg_color, dbg_color in samples:
                # 【子步骤 1】将局部坐标系中的点转换为世界坐标系中的绝对位置  
                # 
                # ground_point_in_vehicle_frame() 函数执行的操作：
                #   a) 以车辆当前位置为原点，建立车辆局部坐标系：
                #      - X 轴：车辆正前方（车头方向）  
                #      - Y 轴：车辆正右方（副驾驶侧）  
                #      - Z 轴：垂直向上（与重力相反）  
                #   b) 根据参数构造局部坐标点：
                #      local_point = (forward_m, right_m, 0.0)  # Z=0 表示在地面高度  
                #   c) 使用车辆的 Transform 将局部坐标转换为世界坐标：
                #      world_point = vehicle_transform.transform(local_point)  
                #      这等价于：world_point = R * local_point + T  
                #      其中 R 是旋转矩阵，T 是平移向量（车辆位置）  
                #   d) 调整 Z 坐标到地面高度：
                #      - 查询该 (X, Y) 位置的地形高度 map_z  
                #      - 设置 world_point.z = map_z（确保点贴在地面上，而不是悬空或陷入地下）  
                # 
                # 为什么要这样做？
                # - 车辆局部坐标更容易理解："车前方 10 米，右侧 2.5 米" 比世界坐标直观  
                # - 自动适应地形起伏：即使在不平的路面上，点也会贴在地面上  
                # - 跟随车辆移动：当车辆前进时，这些点会相对车辆保持固定位置  
                world_point = ground_point_in_vehicle_frame(world, vehicle, forward_m, right_m)
                
                # 【子步骤 2】在 CARLA 3D 世界中绘制调试点（可视化验证世界坐标位置）
                # 
                # debug_draw_point() 函数会在 CARLA 仿真环境中绘制一个永久性的标记点：
                #   - 类型：小圆球（sphere），半径约 0.1 米  
                #   - 颜色：dbg_color（CARLA Color 对象，与 pygame 颜色对应以便对比）  
                #   - 生命周期：持久显示（直到下一帧被清除或手动删除）  
                #   - 附加文字标签：在点上方显示 label 字符串（如 "5m"、"left"）  
                # 
                # 作用：
                # - 可以在 CARLA 客户端（Unreal Engine 视图）中直接看到这个点  
                # - 用于验证 ground_point_in_vehicle_frame() 计算的世界坐标是否正确  
                # - 如果点的位置不符合预期（比如应该在车前却出现在车后），说明坐标转换有误  
                debug_draw_point(world, world_point, dbg_color, label)
                
                # 【子步骤 3】核心投影计算：将世界坐标点投影到 2D 像素坐标  
                # 
                # world_to_pixel() 是 common.py 中实现的关键函数，它封装了完整的投影链路：
                # 
                # 输入参数：
                #   - world_point: Carla.Location 对象，世界坐标系中的 3D 点 (X, Y, Z)  
                #   - camera_tf: Carla.Transform 对象，相机的位姿（位置 + 姿态）  
                #   - k: 3x3 numpy 数组，相机内参矩阵（intrinsic matrix）  
                #         K = [[fx,  0, cx],  
                #              [ 0, fy, cy],  
                #              [ 0,  0,  1]]  
                #         其中：  
                #           fx = fy = W / (2 * tan(FOV/2))  # 焦距（像素单位）  
                #           cx = W / 2  # 主点横坐标（图像中心）  
                #           cy = H / 2  # 主点纵坐标（图像中心）  
                #           W = WINDOW_WIDTH, H = WINDOW_HEIGHT  
                #   - WINDOW_WIDTH, WINDOW_HEIGHT: 图像分辨率（像素）  
                #   - margin: 边界容差（像素），允许点稍微超出屏幕仍被视为有效  
                #             默认 30.0 像素，防止边缘点因浮点误差被误判为无效  
                # 
                # 内部计算流程（详细版）：
                #   Step A: 世界坐标 -> 相机 UE 坐标  
                #     1. 构建相机外参矩阵（extrinsic matrix）E = [R|t]  
                #        - R: 3x3 旋转矩阵，从 camera_tf.rotation 计算得到  
                #        - t: 3x1 平移向量，等于 -R * camera_tf.location  
                #     2. 将世界点转换为齐次坐标：P_world_h = [X, Y, Z, 1]^T  
                #     3. 应用外参变换：P_camera_ue_h = E * P_world_h  
                #     4. 提取 3D 坐标：P_camera_ue = (X_ue, Y_ue, Z_ue)  
                #     
                #   Step B: 相机 UE 坐标 -> 相机 CV 坐标  
                #     5. 翻转 Y 轴：X_cv = X_ue, Y_cv = -Y_ue, Z_cv = Z_ue  
                #        （UE 坐标系 Y 向上，CV 坐标系 Y 向下）  
                #     
                #   Step C: 相机 CV 坐标 -> 归一化平面坐标  
                #     6. 透视除法（归一化）：  
                #        x_norm = X_cv / Z_cv  # 归一化横坐标  
                #        y_norm = Y_cv / Z_cv  # 归一化纵坐标  
                #        这一步将 3D 点投影到 z=1 的归一化成像平面上  
                #     
                #   Step D: 归一化平面坐标 -> 像素坐标  
                #     7. 应用内参矩阵 K：  
                #        u = fx * x_norm + cx  # 像素横坐标（列）  
                #        v = fy * y_norm + cy  # 像素纵坐标（行）  
                #     8. 计算深度值：depth = Z_cv（沿相机光轴的距离，单位：米）  
                #     
                #   Step E: 有效性检查  
                #     9. 检查点是否在相机前方：Z_cv > 0（否则点在相机后面，不可见）  
                #     10. 检查点是否在视野范围内：  
                #         -margin <= u <= WINDOW_WIDTH + margin  
                #         -margin <= v <= WINDOW_HEIGHT + margin  
                #     11. 如果任一检查失败，返回 None（表示该点不在有效视野内）  
                # 
                # 输出：
                #   - 成功：三元组 (u, v, depth)，其中 u,v 为浮点数像素坐标，depth 为深度（米）  
                #   - 失败：None（点在视野外、被遮挡、或在相机后方）  
                # 
                # 注意事项：
                #   - 透视投影会产生近大远小的效果：同样大小的物体，距离越远在图像中越小  
                #   - 相机 FOV（视场角）决定了能看到的范围：FOV 越大，看到的场景越广，但畸变也越大  
                #   - 如果相机姿态变化（如车辆转向导致相机跟随转动），投影结果会相应改变  
                pixel = world_to_pixel(world_point, camera_tf, k, WINDOW_WIDTH, WINDOW_HEIGHT, margin=30.0)
                
                # 【子步骤 4】在 pygame 2D 图像上绘制投影后的标记点（可视化验证投影结果）
                # 
                # draw_pixel_marker() 函数会在 pygame 显示窗口上绘制：
                #   - 彩色实心圆圈：半径 7 像素，颜色为 pg_color（与 CARLA debug 颜色对应）  
                #   - 黑色边框圆环：半径 9 像素，线宽 2 像素，增强对比度和可见性  
                #   - 文字标签：显示 "标签名 深度值m"（如 "5m 5.0m"），位于圆圈右上方 10 像素处  
                # 
                # 关键验证点：
                #   - 如果 pygame 标记点与 CARLA 3D 点在视觉上完全对齐，说明投影算法正确！  
                #   - 你可以观察到：  
                #     * 5m 点比 10m 点更大、更靠下（透视效果：近大远小）  
                #     * left 点在图像左侧，right 点在图像右侧（横向偏移正确）  
                #     * 当车辆转向时，所有点的位置会相应移动（跟随相机姿态变化）  
                #   - 如果标记点位置异常（如在错误的一侧、大小不对），可能的原因：  
                #     * 相机内参 K 计算错误（FOV 或分辨率参数不对）  
                #     * 坐标轴方向混淆（UE vs CV 坐标系的 Y 轴翻转忘记处理）  
                #     * 相机外参变换矩阵计算错误（旋转或平移搞反）  
                draw_pixel_marker(pygame, display, font, pixel, pg_color, label)

            # ====================================================================
            # 第 5 步：绘制 HUD 信息
            # ====================================================================
            lines = [
                "Lesson 07 | world point -> pixel | ESC quit",
                "Camera: RGB lines | Vehicle: CMY lines | Compare positions",
                "Chain: world -> camera UE -> camera CV -> pixel.",
            ]
            draw_text_lines(pygame, display, font, lines)
            pygame.display.flip()

    finally:
        # ====================================================================
        # 第 6 步：清理资源
        # ====================================================================
        destroy_actors(actors)
        pygame.quit()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
