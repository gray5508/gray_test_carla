"""
04_ground_arrow_overlay.py

目标：
把你的核心设想跑成一个最小闭环：

  图像里识别到一个路面点
      -> 反投影成 CARLA world 地面点
      -> 选取车辆前方一个参考点
      -> 在 pygame 相机画面上绘制贴地箭头

为了不依赖真实模型，本 lesson 用“鼠标点击”模拟检测结果：
  左键点击画面中的路面位置 = 模型检测到的路面点。

运行：
  C:\\Users\\cicii\\miniconda3\\envs\\carla_test\\python.exe 04_ground_arrow_overlay.py

操作：
  W/A/S/D 或方向键   开车
  鼠标左键           把图像像素点反投影成地面目标点
  C                  清除鼠标目标，回到合成目标
  T                  切换合成目标：左转/右转/直行
  ESC                退出

重要理解：
  这里画的是“客户端 AR 叠加层”，不是把材质真正贴进 UE 世界。
  但它使用真实 CARLA camera 的内参/外参和世界坐标，所以视觉上会跟着路面运动。
"""

import math
import time

import pygame

from common import CAMERA_FOV
from common import RgbCamera
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import build_camera_matrix
from common import carla
from common import connect_client
from common import destroy_actors
from common import draw_debug_ground_arrow
from common import draw_debug_point
from common import draw_text_lines
from common import get_ground_z
from common import get_keyboard_vehicle_control
from common import ground_point_from_vehicle
from common import make_arrow_polygon
from common import make_pygame_surface
from common import pixel_to_world_on_ground
from common import project_locations
from common import spawn_ego_vehicle
from common import world_to_pixel


TARGET_MODES = [
    ("synthetic left turn", 18.0, -5.0),
    ("synthetic right turn", 18.0, 5.0),
    ("synthetic straight", 22.0, 0.0),
]


def draw_transparent_polygon(pygame, display, points, fill_color, outline_color):
    """在 pygame 上画半透明多边形。"""
    if not points:
        return

    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(overlay, fill_color, points)
    pygame.draw.lines(overlay, outline_color, True, points, 2)
    display.blit(overlay, (0, 0))


def draw_screen_marker(pygame, display, font, pixel, color, label):
    """在屏幕上标记一个投影点。"""
    if pixel is None:
        return

    u, v, depth = pixel
    center = (int(u), int(v))
    pygame.draw.circle(display, color, center, 7, 0)
    pygame.draw.circle(display, (0, 0, 0), center, 8, 2)

    text = font.render("{} {:.1f}m".format(label, depth), True, color)
    display.blit(text, (center[0] + 10, center[1] - 9))


def distance_2d(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def main():
    pygame.init()
    pygame.font.init()

    display = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.HWSURFACE | pygame.DOUBLEBUF,
    )
    pygame.display.set_caption("Lesson 04 - ground arrow AR overlay")

    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    k = build_camera_matrix(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)
    client, world = connect_client()

    actors = []
    current_steer = 0.0
    manual_target_world = None
    target_mode_index = 0

    try:
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        camera = RgbCamera(world, vehicle, WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)
        actors.append(camera.actor)

        print("Lesson 04 started.")
        print("Left click on the road in pygame window to simulate a detected road point.")

        running = True
        while running:
            clock.tick(30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_c:
                        manual_target_world = None
                        print("Manual target cleared.")
                    elif event.key == pygame.K_t:
                        target_mode_index = (target_mode_index + 1) % len(TARGET_MODES)
                        manual_target_world = None
                        print("Target mode:", TARGET_MODES[target_mode_index][0])

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # 鼠标点击点是图像里的像素。
                    # 这里假设它落在路面上，求它与地面平面的交点。
                    u, v = event.pos
                    camera_transform = camera.get_transform()

                    front_ground = ground_point_from_vehicle(world, vehicle, 10.0, 0.0)
                    ground_z = get_ground_z(world, front_ground) + 0.04

                    hit = pixel_to_world_on_ground(u, v, camera_transform, k, ground_z)
                    if hit is None:
                        print("Click did not intersect the ground plane.")
                    else:
                        hit.z = ground_z
                        manual_target_world = hit
                        print(
                            "Manual target world point: x={:.3f}, y={:.3f}, z={:.3f}".format(
                                hit.x, hit.y, hit.z
                            )
                        )

            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(
                pygame, keys, current_steer
            )
            vehicle.apply_control(control)

            if camera.latest_rgb is not None:
                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))
            else:
                display.fill((10, 10, 10))

            camera_transform = camera.get_transform()

            # 当前车辆前方的道路参考点。
            # 你后续可以把它换成“当前车道中心线前方 N 米点”。
            ahead_point = ground_point_from_vehicle(world, vehicle, 9.0, 0.0)

            # 目标点：
            # 1. 如果用户鼠标点过，就用反投影得到的 manual_target_world；
            # 2. 否则用一个合成的左转/右转/直行点，方便不用模型也能看效果。
            mode_name, forward_m, right_m = TARGET_MODES[target_mode_index]
            synthetic_target = ground_point_from_vehicle(world, vehicle, forward_m, right_m)
            target_point = manual_target_world if manual_target_world is not None else synthetic_target

            # CARLA 世界调试：让你在 UE 主窗口也能看到点和箭头。
            draw_debug_point(world, ahead_point, carla.Color(0, 255, 0), "ahead")
            draw_debug_point(world, target_point, carla.Color(255, 0, 255), "target")
            draw_debug_ground_arrow(world, ahead_point, target_point)

            # 屏幕投影点：绿色是车前方参考点，紫色是检测/目标点。
            ahead_pixel = world_to_pixel(
                ahead_point, camera_transform, k, WINDOW_WIDTH, WINDOW_HEIGHT, margin=30.0
            )
            target_pixel = world_to_pixel(
                target_point, camera_transform, k, WINDOW_WIDTH, WINDOW_HEIGHT, margin=30.0
            )
            draw_screen_marker(pygame, display, font, ahead_pixel, (0, 255, 0), "ahead")
            draw_screen_marker(pygame, display, font, target_pixel, (255, 0, 255), "target")

            # 构造并投影贴地箭头多边形。
            arrow_polygon = make_arrow_polygon(ahead_point, target_point, width=1.25)
            arrow_pixels = project_locations(
                arrow_polygon,
                camera_transform,
                k,
                WINDOW_WIDTH,
                WINDOW_HEIGHT,
                margin=180.0,
            )
            if arrow_pixels is not None:
                draw_transparent_polygon(
                    pygame,
                    display,
                    arrow_pixels,
                    fill_color=(255, 170, 20, 115),
                    outline_color=(255, 245, 180, 210),
                )

            target_source = "mouse click" if manual_target_world is not None else mode_name
            lines = [
                "Lesson 04 | AR ground arrow overlay | ESC quit",
                "Left click road pixel -> world ground target | C clear | T switch synthetic target",
                "Target source: {} | distance ahead->target {:.2f}m".format(
                    target_source,
                    distance_2d(ahead_point, target_point),
                ),
                "This is client-side AR overlay: camera K + camera pose + world ground points.",
            ]
            draw_text_lines(pygame, display, font, lines)

            pygame.display.flip()

    finally:
        time.sleep(0.1)
        destroy_actors(actors)
        pygame.quit()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
