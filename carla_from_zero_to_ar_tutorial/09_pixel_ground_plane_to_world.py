"""
09_pixel_ground_plane_to_world.py

本节目标：
  不使用 depth camera，只假设鼠标点击的是"路面上的点"，然后把 pixel 反投影
  到地面平面 z=ground_z。

为什么重要：
  你后续的路口/车道线模型很可能只从 RGB 图像输出一个像素点。
  如果这个点代表路面关键点，比如转弯入口点、车道中心点、停止线点，
  就可以用"像素射线与地面平面求交"估计它的世界坐标。

限制：
  如果道路有坡度、点不在地面、相机 pitch 不准，误差会明显。

核心知识点：
  - 不需要深度相机，只需要 RGB 图像
  - 假设检测到的点在路面上（已知 z 坐标）
  - 通过像素坐标和相机参数构造一条射线
  - 射线与地面平面相交，得到世界坐标
  
应用场景：
  - 车道线检测：模型输出像素坐标，需要转换为世界坐标用于路径规划
  - 交通标志定位：识别标志在图像中的位置，估算其真实位置
  - 任何只需要 RGB 相机的路面关键点检测任务
  
数学原理：
  1. 像素坐标 (u, v) 通过 K^-1 转换为相机坐标系下的射线方向
  2. 射线从相机光心出发，沿着该方向延伸
  3. 求解射线与平面 z=ground_z 的交点
  4. 将交点从相机坐标系转换到世界坐标系
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
from common import get_ground_z
from common import get_keyboard_vehicle_control
from common import ground_point_in_vehicle_frame
from common import make_pygame_surface
from common import pixel_to_world_on_ground
from common import spawn_ego_vehicle


def main():
    """
    主函数：演示如何仅使用 RGB 图像将像素点反投影到地面平面
    
    工作流程：
      1. 初始化 pygame 显示窗口
      2. 连接 CARLA 并生成车辆和 RGB 相机
      3. 监听鼠标点击事件
      4. 点击时估算地面的 z 坐标
      5. 通过像素坐标和地面高度计算世界坐标（射线-平面相交）
      6. 在屏幕上绘制标记点并在 CARLA 中 debug draw
      
    与 lesson 08 的区别：
      - lesson 08: 使用深度相机获取精确深度值
      - lesson 09: 假设点在地面上，通过几何计算估算位置
      - lesson 09 更实用，因为大多数检测模型只输出 RGB 图像的像素坐标
    """
    # 初始化 pygame 和字体系统
    pygame.init()
    pygame.font.init()

    # 创建显示窗口
    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("09 pixel to ground plane")
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    # 构建相机内参矩阵 K
    k = build_camera_intrinsic_k(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)
    
    # 连接到 CARLA server
    client, world = connect_to_carla()

    actors = []
    current_steer = 0.0  # 当前方向盘转角
    clicked_pixel = None  # 用户点击的像素坐标
    clicked_world = None  # 反算出的世界坐标
    last_info = "Click a road pixel."  # 最后一条信息显示

    try:
        # 生成自车
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)
        
        # 只需要 RGB 相机，不需要深度相机
        camera = CameraSensor(world, vehicle, "sensor.camera.rgb")
        actors.append(camera.actor)

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
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # 鼠标左键点击
                    # 记录点击的像素坐标
                    clicked_pixel = event.pos

                    # 关键步骤：估算地面的 z 坐标
                    # 方法：取车辆前方 10 米处的道路高度作为地面平面高度
                    # 这是假设局部路面近似水平
                    # ground_point_in_vehicle_frame 返回车辆前方某点的世界坐标
                    ahead = ground_point_in_vehicle_frame(world, vehicle, 10.0, 0.0)
                    
                    # get_ground_z 查询该位置的道路 waypoint 的 z 坐标
                    # +0.04 是为了让箭头稍微高于路面，避免 z-fighting（闪烁）
                    ground_z = get_ground_z(world, ahead) + 0.04

                    # 核心计算：像素坐标 -> 地面世界坐标
                    # 内部流程：
                    #   1. 通过 K^-1 将像素转换为相机坐标系下的射线方向
                    #   2. 将射线转换到世界坐标系
                    #   3. 求解射线与平面 z=ground_z 的交点
                    clicked_world = pixel_to_world_on_ground(
                        clicked_pixel[0],  # u 坐标
                        clicked_pixel[1],  # v 坐标
                        camera.get_transform(),  # 相机外参
                        k,  # 相机内参
                        ground_z,  # 地面高度
                    )

                    # 检查结果是否有效
                    if clicked_world is None:
                        # 射线没有与地面平面相交（可能指向天空或后方）
                        last_info = "Ray does not hit ground plane in front of camera."
                    else:
                        # 格式化显示结果
                        last_info = "pixel={} -> ground world=({:.2f},{:.2f},{:.2f})".format(
                            clicked_pixel,
                            clicked_world.x,
                            clicked_world.y,
                            clicked_world.z,
                        )
                    print(last_info)

            # 读取键盘状态，控制车辆
            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            # 渲染 RGB 相机图像
            if camera.latest_rgb is not None:
                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))
            else:
                display.fill((10, 10, 10))

            # 在点击位置绘制红色圆圈
            if clicked_pixel is not None:
                pygame.draw.circle(display, (255, 60, 60), clicked_pixel, 8, 2)

            # 在 CARLA 世界中绘制调试点
            if clicked_world is not None:
                debug_draw_point(world, clicked_world, text="ground hit")

            # 准备 HUD 显示的文字
            lines = [
                "Lesson 09 | pixel ray intersects ground plane | ESC quit",
                "This is useful for RGB-only road keypoint detection.",  # 这对纯 RGB 的路面关键点检测很有用
                last_info,
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
