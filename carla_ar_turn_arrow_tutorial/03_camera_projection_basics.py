"""
03_camera_projection_basics.py

目标：
1. 理解 camera 内参 K；
2. 理解 camera 外参 camera.get_transform()；
3. 把 CARLA world 里的路面点投影到 pygame 图像像素；
4. 为后续“把路面箭头固定在画面中的真实地面位置”做准备。

这个 lesson 会在车前方 5m/10m/15m 和左右偏移点上打标：
  1. CARLA 世界里用 world.debug.draw_point 标记；
  2. pygame 图像上用 world_to_pixel 投影后画圆。

运行：
  C:\\Users\\cicii\\miniconda3\\envs\\carla_test\\python.exe 03_camera_projection_basics.py
"""

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
from common import draw_debug_point
from common import draw_text_lines
from common import get_keyboard_vehicle_control
from common import ground_point_from_vehicle
from common import make_pygame_surface
from common import spawn_ego_vehicle
from common import world_to_pixel


def draw_projected_point(pygame, display, font, pixel, label, color):
    """在 pygame 图像上画一个投影点和标签。"""
    if pixel is None:
        return

    u, v, depth = pixel
    center = (int(u), int(v))
    pygame.draw.circle(display, color, center, 7, 0)
    pygame.draw.circle(display, (0, 0, 0), center, 8, 2)

    text = font.render("{} {:.1f}m".format(label, depth), True, color)
    display.blit(text, (center[0] + 10, center[1] - 10))


def main():
    pygame.init()
    pygame.font.init()

    display = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.HWSURFACE | pygame.DOUBLEBUF,
    )
    pygame.display.set_caption("Lesson 03 - camera projection basics")

    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    k = build_camera_matrix(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)
    print("Camera intrinsic K:")
    print(k)

    client, world = connect_client()

    actors = []
    current_steer = 0.0

    try:
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        camera = RgbCamera(world, vehicle, WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)
        actors.append(camera.actor)

        running = True
        while running:
            clock.tick(30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
                    running = False

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

            # 这些点都来自车辆局部坐标，再转成世界坐标：
            #   forward_m = 车头前方距离
            #   right_m   = 车辆右侧距离，负数表示左侧
            samples = [
                ("front 5m", 5.0, 0.0, (255, 255, 0), carla.Color(255, 255, 0)),
                ("front 10m", 10.0, 0.0, (255, 150, 0), carla.Color(255, 150, 0)),
                ("front 15m", 15.0, 0.0, (255, 80, 0), carla.Color(255, 80, 0)),
                ("left", 10.0, -2.5, (0, 220, 255), carla.Color(0, 220, 255)),
                ("right", 10.0, 2.5, (255, 0, 255), carla.Color(255, 0, 255)),
            ]

            for label, forward_m, right_m, pg_color, dbg_color in samples:
                world_point = ground_point_from_vehicle(world, vehicle, forward_m, right_m)
                draw_debug_point(world, world_point, dbg_color, label)
                pixel = world_to_pixel(
                    world_point,
                    camera_transform,
                    k,
                    WINDOW_WIDTH,
                    WINDOW_HEIGHT,
                    margin=20.0,
                )
                draw_projected_point(pygame, display, font, pixel, label, pg_color)

            lines = [
                "Lesson 03 | world ground points -> camera pixels | ESC quit",
                "If a debug point is visible in CARLA but not in pygame, it may be outside camera FOV.",
                "Projection uses: world point -> camera inverse transform -> UE-to-OpenCV axes -> K.",
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
