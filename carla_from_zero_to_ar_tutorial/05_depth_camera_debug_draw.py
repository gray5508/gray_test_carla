"""
05_depth_camera_debug_draw.py

本节目标：
  1. 创建 RGB camera 和 Depth camera；
  2. 解码 depth image 到米；
  3. 鼠标点击 RGB 图像中的一个像素；
  4. 读取同一像素的 depth；
  5. 用 pixel + depth 反算世界坐标；
  6. 在 CARLA 世界里 debug draw 这个点。

这是“像素坐标 + 深度 -> 世界坐标”的第一次完整实践。
后面如果你的模型能得到某个像素点，同时你有深度图，就可以用这个链路定位它。
"""

import pygame

from common import CAMERA_FOV
from common import CameraSensor
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import build_camera_intrinsic_k
from common import connect_to_carla
from common import debug_draw_point
from common import destroy_actors
from common import draw_text_lines
from common import get_keyboard_vehicle_control
from common import make_pygame_surface
from common import pixel_depth_to_world
from common import spawn_ego_vehicle


def main():
    """
    主函数：演示深度相机和像素到世界坐标的转换。
    
    学习重点：
      1. 同时创建 RGB camera 和 Depth camera
      2. 解码 depth image 到米（从 CARLA 编码格式）
      3. 鼠标点击 RGB 图像中的像素
      4. 读取同一像素的深度值
      5. 用 pixel + depth 反算世界坐标
      6. 在 CARLA 世界里 debug draw 这个点
    
    实际应用场景：
      - 这是"像素坐标 + 深度 -> 世界坐标"的第一次完整实践
      - 如果你的模型能检测到某个像素点，同时你有深度图，就可以定位它
      - AR 导航、障碍物检测、3D 重建等都基于这个原理
    
    实验流程：
      1. 初始化 pygame 窗口
      2. 连接 CARLA 并生成车辆
      3. 创建 RGB 和 Depth 两个相机
      4. 进入游戏循环
      5. 鼠标点击像素，计算世界坐标
      6. 在 CARLA 世界中绘制该点
    """
    # ========================================================================
    # 第 1 步：初始化 pygame
    # ========================================================================
    pygame.init()
    pygame.font.init()

    # 创建显示窗口
    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("05 Depth camera debug draw")
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    # ========================================================================
    # 第 2 步：构建相机内参矩阵 K
    # ========================================================================
    # build_camera_intrinsic_k() 来自 common.py
    # 根据窗口大小和 FOV 计算相机的内参矩阵
    # K 矩阵用于像素坐标和相机坐标之间的转换
    k = build_camera_intrinsic_k(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)
    
    # 连接 CARLA
    client, world = connect_to_carla()

    # 记录需要清理的 actor
    actors = []
    # 当前方向盘转角
    current_steer = 0.0
    # 鼠标点击的像素坐标 (u, v)
    clicked_pixel = None
    # 点击点对应的世界坐标
    clicked_world = None
    # 点击点的深度值（米）
    clicked_depth = None

    try:
        # ====================================================================
        # 第 3 步：生成车辆和相机
        # ====================================================================
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        # 创建 RGB 相机（用于显示和鼠标点击）
        rgb_camera = CameraSensor(world, vehicle, "sensor.camera.rgb")
        # 创建 Depth 相机（用于获取深度信息）
        # 注意：两个相机使用相同的安装位置和参数，确保像素一一对应
        depth_camera = CameraSensor(world, vehicle, "sensor.camera.depth")
        # 把两个相机都加入清理列表
        actors.extend([rgb_camera.actor, depth_camera.actor])

        print("\n说明：")
        print("  - 左键点击 RGB 图像中的任意像素")
        print("  - 程序会读取该像素的深度值")
        print("  - 然后用 pixel + depth 计算世界坐标")
        print("  - 最后在 CARLA 世界中用绿点标记该位置")
        print("  - 按 ESC 退出\n")

        # ====================================================================
        # 第 4 步：游戏主循环
        # ====================================================================
        running = True
        while running:
            # 控制帧率为 30 FPS
            clock.tick(30)

            # ---------------------------------------------------------------
            # 4.1 处理 pygame 事件
            # ---------------------------------------------------------------
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
                    running = False
                # 鼠标左键点击事件
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # 记录点击的像素坐标 (u, v)
                    clicked_pixel = event.pos
                    
                    # 如果已经收到了深度图像
                    if depth_camera.latest_depth_m is not None:
                        u, v = clicked_pixel
                        # 检查点击位置是否在图像范围内
                        if 0 <= u < WINDOW_WIDTH and 0 <= v < WINDOW_HEIGHT:
                            # 从深度图中读取该像素的深度值（米）
                            # latest_depth_m 是一个 numpy 数组，shape=(height, width)
                            print("Reading depth at ({}, {})".format(u, v))
                            clicked_depth = float(depth_camera.latest_depth_m[v, u])
                            
                            # pixel_depth_to_world() 来自 common.py
                            # 它会：
                            #   1. 把像素坐标 + 深度 -> OpenCV 相机坐标
                            #   2. OpenCV 相机坐标 -> CARLA 相机坐标
                            #   3. CARLA 相机坐标 -> 世界坐标
                            clicked_world = pixel_depth_to_world(
                                u, v, clicked_depth, rgb_camera.get_transform(), k
                            )
                            
                            # 打印计算结果
                            print("Click pixel ({}, {}) depth {:.3f}m -> world x={:.3f}, y={:.3f}, z={:.3f}".format(
                                u, v, clicked_depth,
                                clicked_world.x, clicked_world.y, clicked_world.z
                            ))

            # ---------------------------------------------------------------
            # 4.2 读取键盘输入，控制车辆
            # ---------------------------------------------------------------
            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            # ---------------------------------------------------------------
            # 4.3 显示 RGB 图像
            # ---------------------------------------------------------------
            if rgb_camera.latest_rgb is not None:
                display.blit(make_pygame_surface(pygame, rgb_camera.latest_rgb), (0, 0))
            else:
                display.fill((10, 10, 10))

            # ---------------------------------------------------------------
            # 4.4 绘制点击标记
            # ---------------------------------------------------------------
            # 如果有点击过，在 RGB 图像上画一个红色圆圈标记点击位置
            if clicked_pixel is not None:
                pygame.draw.circle(display, (255, 60, 60), clicked_pixel, 8, 2)

            # 如果计算出了世界坐标，在 CARLA 世界中绘制该点
            if clicked_world is not None:
                # debug_draw_point() 来自 common.py
                # 它会在 CARLA 世界中画一个绿色的点和文字标签
                debug_draw_point(world, clicked_world, text="depth hit")

            # ---------------------------------------------------------------
            # 4.5 绘制 HUD 信息
            # ---------------------------------------------------------------
            lines = [
                "Lesson 05 | RGB + Depth | left click pixel -> world point | ESC quit",
                "Depth camera is decoded from CARLA BGRA to meters.",
                "Clicked pixel: {} depth: {}".format(
                    clicked_pixel,
                    "{:.3f}m".format(clicked_depth) if clicked_depth is not None else "-",
                ),
            ]
            draw_text_lines(pygame, display, font, lines)
            pygame.display.flip()

    finally:
        # ====================================================================
        # 第 5 步：清理资源
        # ====================================================================
        destroy_actors(actors)
        pygame.quit()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
