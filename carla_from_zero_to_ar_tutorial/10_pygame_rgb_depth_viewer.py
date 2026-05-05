"""
10_pygame_rgb_depth_viewer.py

本节目标：
  1. 同时显示 RGB 和 Depth；
  2. 鼠标移动时读取当前像素和 depth；
  3. 建立"同一个像素在 RGB/Depth 中一一对应"的直觉。

显示布局：
  左半屏：RGB camera
  右半屏：Depth camera 灰度可视化

核心知识点：
  - RGB 相机和深度相机安装在相同位置，保证像素一一对应
  - 深度图需要解码才能看到实际的深度值（CARLA 使用特殊编码）
  - 通过鼠标悬停可以实时查看任意像素的深度信息
  
应用场景：
  - 调试深度相机数据质量
  - 理解 RGB-D 数据的对应关系
  - 验证深度值的准确性
  - 为后续的 3D 重建、障碍物检测等任务做准备
"""

import pygame

from common import CameraSensor
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import connect_to_carla
from common import destroy_actors
from common import draw_text_lines
from common import get_keyboard_vehicle_control
from common import make_pygame_surface
from common import spawn_ego_vehicle


def scale_surface_half(pygame, surface):
    """
    把 1280x720 surface 缩放成半屏宽。
    
    因为我们要左右并排显示两个图像，每个图像宽度是窗口的一半。
    smoothscale 使用双线性插值，比普通的 scale 更平滑。
    
    Args:
        pygame: pygame 模块
        surface: 原始的 pygame surface (1280x720)
        
    Returns:
        缩放后的 surface (640x720)
    """
    return pygame.transform.smoothscale(surface, (WINDOW_WIDTH // 2, WINDOW_HEIGHT))


def main():
    """
    主函数：同时显示 RGB 和深度图像，支持鼠标悬停查看深度值
    
    工作流程：
      1. 初始化 pygame 显示窗口
      2. 连接 CARLA 并生成车辆、RGB 相机、深度相机
      3. 将 RGB 图像显示在左半屏，深度图像显示在右半屏
      4. 监听鼠标移动事件，在右半屏时显示对应像素的深度值
      5. 实时更新显示
      
    注意：
      - 深度图像经过缩放显示，需要将鼠标坐标映射回原始图像坐标
      - 深度值以米为单位，近处亮（白色），远处暗（黑色）
    """
    # 初始化 pygame 和字体系统
    pygame.init()
    pygame.font.init()

    # 创建显示窗口
    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("10 RGB + Depth viewer")
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    # 连接到 CARLA server
    client, world = connect_to_carla()
    
    actors = []
    current_steer = 0.0  # 当前方向盘转角
    mouse_info = "Move mouse over right half to inspect depth."  # 鼠标信息显示

    try:
        # 生成自车
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        # 创建 RGB 相机和深度相机
        # 两者使用相同的安装位置和参数，保证像素一一对应
        rgb_camera = CameraSensor(world, vehicle, "sensor.camera.rgb")
        depth_camera = CameraSensor(world, vehicle, "sensor.camera.depth")
        actors.extend([rgb_camera.actor, depth_camera.actor])

        running = True
        while running:
            # 限制循环频率为 30 FPS
            clock.tick(30)

            # 处理 pygame 事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:  # 窗口关闭
                    running = False
                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:  # ESC 退出
                    running = False
                elif event.type == pygame.MOUSEMOTION:  # 鼠标移动
                    mx, my = event.pos
                    
                    # 右半屏显示的是缩放后的 depth，x 要映射回原始图像坐标
                    # 因为深度图被缩放到一半宽度，所以需要将鼠标 x 坐标乘以 2
                    if mx >= WINDOW_WIDTH // 2 and depth_camera.latest_depth_m is not None:
                        # 计算在原始深度图中的 u 坐标
                        u = int((mx - WINDOW_WIDTH // 2) * 2)
                        v = int(my)  # y 坐标不需要变换，因为没有垂直缩放
                        
                        # 确保坐标在有效范围内
                        if 0 <= u < WINDOW_WIDTH and 0 <= v < WINDOW_HEIGHT:
                            # 从深度图中读取该像素的深度值（单位：米）
                            depth = depth_camera.latest_depth_m[v, u]
                            mouse_info = "Depth pixel original=({}, {}) depth={:.2f}m".format(u, v, depth)

            # 读取键盘状态，控制车辆
            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            # 清空屏幕
            display.fill((0, 0, 0))
            
            # 渲染 RGB 图像到左半屏
            if rgb_camera.latest_rgb is not None:
                # 先转换为 pygame surface，再缩放到半屏宽度
                rgb_surface = scale_surface_half(pygame, make_pygame_surface(pygame, rgb_camera.latest_rgb))
                display.blit(rgb_surface, (0, 0))  # 左上角 (0, 0)
            
            # 渲染深度图像到右半屏
            if depth_camera.latest_rgb is not None:
                # depth_camera.latest_rgb 已经是灰度图（由深度值转换而来）
                depth_surface = scale_surface_half(pygame, make_pygame_surface(pygame, depth_camera.latest_rgb))
                display.blit(depth_surface, (WINDOW_WIDTH // 2, 0))  # 右上角 (640, 0)

            # 在中间画一条白线，分隔左右两屏
            pygame.draw.line(display, (255, 255, 255), (WINDOW_WIDTH // 2, 0), (WINDOW_WIDTH // 2, WINDOW_HEIGHT), 2)

            # 准备 HUD 显示的文字
            lines = [
                "Lesson 10 | left RGB | right Depth visualization | ESC quit",
                mouse_info,  # 显示鼠标所在位置的深度信息
            ]
            draw_text_lines(pygame, display, font, lines)
            
            # 更新屏幕显示
            pygame.display.flip()

    finally:
        destroy_actors(actors)
        pygame.quit()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
