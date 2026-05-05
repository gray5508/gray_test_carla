"""
04_rgb_camera_sensor.py

本节目标：
  1. 创建 sensor.camera.rgb；
  2. 把 camera attach 到车辆；
  3. 理解 camera transform 是车辆局部坐标；
  4. 把 CARLA BGRA 图像转换成 RGB；
  5. 用 pygame 显示第一视角，并用 pygame 控车。

这就是你后续实景融合的“画布”。
AR 箭头、检测点、HUD 都会叠加在这个 camera 图像上。
"""

import pygame

from common import CameraSensor
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import connect_to_carla
from common import destroy_actors
from common import draw_text_lines
from common import get_forward_speed
from common import get_keyboard_vehicle_control
from common import make_pygame_surface
from common import print_transform_details
from common import spawn_ego_vehicle


def main():
    """
    主函数：演示 RGB 相机传感器和 pygame 显示。
    
    学习重点：
      1. 创建 sensor.camera.rgb 并 attach 到车辆
      2. 理解 camera transform 是相对车辆的局部坐标
      3. 把 CARLA BGRA 图像转换成 RGB
      4. 用 pygame 显示第一视角画面
      5. 用 pygame 键盘控制车辆
    
    实际应用场景：
      - 这是 AR 实景融合的“画布”
      - AR 箭头、检测点、HUD 都会叠加在这个 camera 图像上
      - 后续所有视觉相关的 lesson 都基于这个框架
    
    实验流程：
      1. 初始化 pygame 窗口
      2. 连接 CARLA 并生成车辆
      3. 创建 RGB 相机并 attach 到车辆
      4. 进入游戏循环（30 FPS）
      5. 读取键盘输入，控制车辆
      6. 获取相机图像，显示在 pygame 窗口
      7. 显示 HUD 信息（位置、速度等）
    """
    # ========================================================================
    # 第 1 步：初始化 pygame
    # ========================================================================
    # 初始化 pygame 核心模块
    pygame.init()
    # 初始化 pygame 字体模块（用于显示 HUD 文字）
    pygame.font.init()

    # 创建显示窗口，大小为 WINDOW_WIDTH x WINDOW_HEIGHT（1280x720）
    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    # 设置窗口标题
    pygame.display.set_caption("04 RGB camera sensor")
    # 创建字体对象，用于渲染 HUD 文字
    font = pygame.font.SysFont("Arial", 18)
    # 创建时钟对象，用于控制帧率
    clock = pygame.time.Clock()

    # ========================================================================
    # 第 2 步：连接 CARLA 并生成车辆
    # ========================================================================
    client, world = connect_to_carla()
    # 记录需要清理的 actor 列表
    actors = []
    # 当前方向盘转角（用于平滑转向）
    current_steer = 0.0

    try:
        # 生成 ego vehicle（主车）
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        # ====================================================================
        # 第 3 步：创建 RGB 相机
        # ====================================================================
        # CameraSensor 来自 common.py，它会：
        #   1. 创建 sensor.camera.rgb blueprint
        #   2. 设置分辨率（1280x720）和 FOV（90度）
        #   3. 把相机 attach 到车辆（使用 DRIVER_CAMERA_TRANSFORM）
        #   4. 启动异步回调，持续接收图像数据
        camera = CameraSensor(world, vehicle, camera_type="sensor.camera.rgb")
        # 把相机 actor 也加入清理列表
        actors.append(camera.actor)

        # 打印相机的安装位置（相对车辆的局部坐标）
        print_transform_details("Camera local mount", camera.transform)
        print("Camera actor world transform will change as vehicle moves.")
        print("\n说明：")
        print("  - 相机安装在车辆局部坐标中（车头前 1.25m，左侧 0.35m，高 1.35m）")
        print("  - 随着车辆移动，相机的世界坐标会不断变化")
        print("  - 按 W/A/S/D 或方向键在 pygame 窗口中开车")
        print("  - 按 ESC 退出\n")

        # ====================================================================
        # 第 4 步：游戏主循环
        # ====================================================================
        running = True
        while running:
            # 控制帧率为 30 FPS
            # clock.tick(30) 会等待足够的时间，使每秒不超过 30 帧
            clock.tick(60)

            # ---------------------------------------------------------------
            # 4.1 处理 pygame 事件
            # ---------------------------------------------------------------
            for event in pygame.event.get():
                # 如果点击窗口关闭按钮，退出
                if event.type == pygame.QUIT:
                    running = False
                # 如果按下 ESC 键，退出
                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
                    running = False

            # ---------------------------------------------------------------
            # 4.2 读取键盘输入，控制车辆
            # ---------------------------------------------------------------
            # 获取当前所有按键的状态
            keys = pygame.key.get_pressed()
            # 根据按键状态生成 VehicleControl 命令
            # get_keyboard_vehicle_control() 来自 common.py
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            # 应用控制命令到车辆
            vehicle.apply_control(control)

            # ---------------------------------------------------------------
            # 4.3 获取相机图像并显示
            # ---------------------------------------------------------------
            if camera.latest_rgb is not None:
                # 如果收到了相机图像，转换成 pygame surface
                # make_pygame_surface() 来自 common.py
                surface = make_pygame_surface(pygame, camera.latest_rgb)
                # 把图像绘制到窗口上（从左上角 (0,0) 开始）
                display.blit(surface, (0, 0))
            else:
                # 如果还没有收到图像，显示黑色背景
                display.fill((10, 10, 10))

            # ---------------------------------------------------------------
            # 4.4 绘制 HUD 信息
            # ---------------------------------------------------------------
            # 获取车辆和相机的当前 Transform
            vehicle_tf = vehicle.get_transform()
            camera_tf = camera.get_transform()
            
            # 准备要显示的文本行
            lines = [
                "Lesson 04 | RGB camera sensor | ESC quit",
                "W/A/S/D or arrow keys drive in pygame window",
                # 车辆位置和朝向
                "Vehicle: x={:.2f} y={:.2f} yaw={:.2f}".format(
                    vehicle_tf.location.x, vehicle_tf.location.y, vehicle_tf.rotation.yaw
                ),
                # 相机世界坐标
                "Camera world: x={:.2f} y={:.2f} z={:.2f}".format(
                    camera_tf.location.x, camera_tf.location.y, camera_tf.location.z
                ),
                # 车辆前向速度（m/s）
                "Forward speed: {:.2f} m/s".format(get_forward_speed(vehicle)),
                # 相机图像的帧号（用于调试同步问题）
                "Image frame: {}".format(
                    camera.latest_image.frame if camera.latest_image is not None else "-"
                ),
            ]
            # 在窗口左上角绘制所有文本行
            draw_text_lines(pygame, display, font, lines)
            
            # 翻转显示缓冲区，把绘制的内容显示到屏幕上
            pygame.display.flip()

    finally:
        # ====================================================================
        # 第 5 步：清理资源
        # ====================================================================
        # 销毁所有 actor（车辆、相机等）
        destroy_actors(actors)
        # 退出 pygame
        pygame.quit()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
