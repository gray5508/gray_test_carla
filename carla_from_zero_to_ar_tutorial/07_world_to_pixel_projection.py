"""
07_world_to_pixel_projection.py

本节目标：
  1. 把 CARLA 世界坐标点投影到 RGB camera 图像；
  2. 理解 world -> camera UE -> camera CV -> pixel；
  3. 在 pygame 画面上标记车辆前方的地面点。

这就是 AR overlay 的半条链：
  world ground point -> image pixel
"""

import pygame

from common import CAMERA_FOV
from common import CameraSensor
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import build_camera_intrinsic_k
from common import carla
from common import connect_to_carla
from common import debug_draw_point
from common import destroy_actors
from common import draw_text_lines
from common import get_keyboard_vehicle_control
from common import ground_point_in_vehicle_frame
from common import make_pygame_surface
from common import spawn_ego_vehicle
from common import world_to_pixel


def draw_pixel_marker(pygame, display, font, pixel, color, label):
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
            # 第 4 步：定义测试点并投影
            # ====================================================================
            # 定义 5 个测试点：不同距离和方向
            # 格式：(标签, 前方距离, 右侧距离, pygame颜色, CARLA调试颜色)
            samples = [
                ("5m", 5.0, 0.0, (255, 255, 0), carla.Color(255, 255, 0)),     # 黄色
                ("10m", 10.0, 0.0, (255, 150, 0), carla.Color(255, 150, 0)),   # 橙色
                ("15m", 15.0, 0.0, (255, 80, 0), carla.Color(255, 80, 0)),     # 深橙色
                ("left", 10.0, -2.5, (0, 220, 255), carla.Color(0, 220, 255)), # 青色（左侧）
                ("right", 10.0, 2.5, (255, 0, 255), carla.Color(255, 0, 255)), # 紫色（右侧）
            ]

            # 获取相机当前的世界坐标 Transform
            camera_tf = camera.get_transform()
            
            # 遍历每个测试点
            for label, forward_m, right_m, pg_color, dbg_color in samples:
                # 1. 把局部坐标点转换成世界坐标（并调整到地面高度）
                world_point = ground_point_in_vehicle_frame(world, vehicle, forward_m, right_m)
                
                # 2. 在 CARLA 世界中绘制调试点（绿色点 + 文字标签）
                debug_draw_point(world, world_point, dbg_color, label)
                
                # 3. 把世界坐标点投影到像素坐标
                # world_to_pixel() 来自 common.py
                # 它会执行：world -> camera UE -> camera CV -> pixel
                # margin=30.0 允许点稍微超出屏幕边界
                pixel = world_to_pixel(world_point, camera_tf, k, WINDOW_WIDTH, WINDOW_HEIGHT, margin=30.0)
                
                # 4. 在 pygame 图像上绘制标记（圆圈 + 文字）
                draw_pixel_marker(pygame, display, font, pixel, pg_color, label)

            # ====================================================================
            # 第 5 步：绘制 HUD 信息
            # ====================================================================
            lines = [
                "Lesson 07 | world point -> pixel | ESC quit",
                "CARLA debug points and pygame markers should match visually.",
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
