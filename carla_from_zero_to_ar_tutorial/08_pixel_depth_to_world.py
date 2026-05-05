"""
08_pixel_depth_to_world.py

本节目标：
  1. 鼠标点击 RGB 图像得到 pixel；
  2. 从 Depth 图读取同一 pixel 的 depth；
  3. pixel + depth -> camera coordinate（相机坐标系）；
  4. camera coordinate -> world coordinate（世界坐标系）；
  5. debug draw 反算出的世界点。

这条链适合"我有深度图"的情况。

核心知识点：
  - 像素坐标 (u, v) + 深度值 depth -> 相机坐标系下的 3D 点
  - 相机坐标系 -> 世界坐标系需要用到相机的外参（位置和姿态）
  - 这是完整的"像素到世界"的反投影链路
  
应用场景：
  - 当你有 RGB-D 相机（同时输出彩色图和深度图）时
  - 可以从图像中检测物体，并通过深度信息还原其真实世界位置
  - 适用于障碍物检测、距离测量等任务
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
from common import pixel_depth_to_camera_cv
from common import pixel_depth_to_world
from common import spawn_ego_vehicle


def main():
    """
    主函数：演示如何从像素坐标和深度值反算出世界坐标
    
    工作流程：
      1. 初始化 pygame 显示窗口
      2. 连接 CARLA 并生成车辆和相机
      3. 监听鼠标点击事件
      4. 点击时获取该像素的深度值
      5. 通过内参矩阵 K 将像素+深度转换为相机坐标
      6. 通过相机外参将相机坐标转换为世界坐标
      7. 在屏幕上绘制标记点并在 CARLA 中 debug draw
    """
    # 初始化 pygame 和字体系统
    pygame.init()
    pygame.font.init()

    # 创建显示窗口，设置标题
    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("08 pixel + depth to world")
    font = pygame.font.SysFont("Arial", 18)  # 用于 HUD 显示的字体
    clock = pygame.time.Clock()  # 控制帧率的时钟

    # 构建相机内参矩阵 K
    # K 包含焦距 fx/fy 和主点 cx/cy，用于像素坐标和相机坐标的转换
    k = build_camera_intrinsic_k(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)
    
    # 连接到 CARLA server
    client, world = connect_to_carla()

    # actors 列表用于跟踪所有生成的 actor，方便最后清理
    actors = []
    current_steer = 0.0  # 当前方向盘转角，用于平滑转向
    last_info = "Click a road pixel."  # 最后一条信息显示
    clicked_pixel = None  # 用户点击的像素坐标 (u, v)
    clicked_world = None  # 反算出的世界坐标

    try:
        # 生成自车（ego vehicle）
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        # 创建两个相机传感器：RGB 相机和深度相机
        # 两者安装在相同位置，保证像素一一对应
        rgb_camera = CameraSensor(world, vehicle, "sensor.camera.rgb")
        depth_camera = CameraSensor(world, vehicle, "sensor.camera.depth")
        actors.extend([rgb_camera.actor, depth_camera.actor])

        running = True
        while running:
            # 限制循环频率为 30 FPS
            clock.tick(30)

            # 处理 pygame 事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:  # 窗口关闭按钮
                    running = False
                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:  # ESC 键退出
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # 鼠标左键点击
                    # 记录点击的像素坐标
                    clicked_pixel = event.pos
                    
                    # 只有当深度图可用时才进行计算
                    if depth_camera.latest_depth_m is not None:
                        u, v = clicked_pixel
                        
                        # 从深度图中读取该像素的深度值（单位：米）
                        # latest_depth_m 是一个 numpy 数组，shape=(height, width)
                        depth = float(depth_camera.latest_depth_m[v, u])
                        
                        # 步骤 1：像素坐标 + 深度 -> 相机坐标系（OpenCV 风格）
                        # 使用内参矩阵 K 进行反投影
                        # 返回的是 [x, y, z]，表示点在相机坐标系中的位置
                        point_cv = pixel_depth_to_camera_cv(u, v, depth, k)
                        
                        # 步骤 2：相机坐标 -> 世界坐标
                        # 需要相机的外参（位置和姿态），通过 get_transform() 获取
                        # 这个函数内部会：camera CV -> camera UE -> world
                        clicked_world = pixel_depth_to_world(u, v, depth, rgb_camera.get_transform(), k)
                        
                        # 格式化显示信息
                        last_info = (
                            "pixel=({}, {}) depth={:.2f}m camera_cv=({:.2f},{:.2f},{:.2f}) "
                            "world=({:.2f},{:.2f},{:.2f})"
                        ).format(
                            u, v, depth,
                            point_cv[0], point_cv[1], point_cv[2],  # 相机坐标系
                            clicked_world.x, clicked_world.y, clicked_world.z,  # 世界坐标系
                        )
                        print(last_info)

            # 读取键盘状态，生成车辆控制指令
            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            # 渲染 RGB 相机图像到屏幕
            if rgb_camera.latest_rgb is not None:
                # make_pygame_surface 将 numpy RGB 数组转换为 pygame surface
                display.blit(make_pygame_surface(pygame, rgb_camera.latest_rgb), (0, 0))
            else:
                display.fill((10, 10, 10))  # 如果还没有图像，显示深色背景

            # 如果用户点击过，在点击位置绘制红色圆圈标记
            if clicked_pixel is not None:
                pygame.draw.circle(display, (255, 60, 60), clicked_pixel, 8, 2)

            # 如果已经计算出世界坐标，在 CARLA 世界中绘制调试点
            if clicked_world is not None:
                debug_draw_point(world, clicked_world, text="pixel+depth")

            # 准备 HUD 显示的文字信息
            lines = [
                "Lesson 08 | pixel + depth -> camera -> world | ESC quit",
                last_info,  # 显示最后一次点击的详细信息
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
