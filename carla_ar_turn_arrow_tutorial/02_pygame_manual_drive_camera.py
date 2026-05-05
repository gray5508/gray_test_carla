"""
02_pygame_manual_drive_camera.py

目标：
1. 用 sensor.camera.rgb 做真正的驾驶画面；
2. 用 pygame 窗口接收键盘控制车辆；
3. 避免 UE 主窗口 spectator 的 WASD/方向键和你的脚本抢输入；
4. 为后续“在相机画面上叠加 AR 箭头”打基础。

运行：
  C:\\Users\\cicii\\miniconda3\\envs\\carla_test\\python.exe 02_pygame_manual_drive_camera.py

操作：
  W / ↑       前进
  S / ↓       倒车
  A / ←       左转
  D / →       右转
  SPACE       刹车
  ESC         退出并清理 actor

注意：
  pygame 只有在自己的窗口获得焦点时才接收键盘。
  运行后请点击 pygame 窗口，不要点击 UE 主窗口开车。
"""

import time

import pygame

from common import RgbCamera
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import connect_client
from common import destroy_actors
from common import draw_text_lines
from common import get_forward_speed
from common import get_keyboard_vehicle_control
from common import make_pygame_surface
from common import spawn_ego_vehicle


def main():
    pygame.init()
    pygame.font.init()

    display = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.HWSURFACE | pygame.DOUBLEBUF,
    )
    pygame.display.set_caption("Lesson 02 - pygame manual drive camera")

    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    client, world = connect_client()

    actors = []
    camera = None
    current_steer = 0.0

    try:
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        camera = RgbCamera(world, vehicle, WINDOW_WIDTH, WINDOW_HEIGHT)
        actors.append(camera.actor)

        print("Lesson 02 started.")
        print("Click the pygame window, then drive with W/A/S/D or arrow keys.")

        running = True
        while running:
            # 30 FPS 足够做入门驾驶，也方便观察 HUD。
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

            transform = vehicle.get_transform()
            velocity = get_forward_speed(vehicle)

            lines = [
                "Lesson 02 | pygame camera + manual drive | ESC quit",
                "W/UP throttle | S/DOWN reverse | A/LEFT D/RIGHT steer | SPACE brake",
                "Control throttle={:.2f} brake={:.2f} steer={:.2f} reverse={}".format(
                    control.throttle,
                    control.brake,
                    control.steer,
                    control.reverse,
                ),
                "Vehicle x={:.2f} y={:.2f} z={:.2f} yaw={:.2f}".format(
                    transform.location.x,
                    transform.location.y,
                    transform.location.z,
                    transform.rotation.yaw,
                ),
                "Forward speed {:.2f} m/s | {:.1f} km/h".format(
                    velocity,
                    velocity * 3.6,
                ),
                "Camera frame {}".format(
                    camera.latest_image.frame if camera.latest_image is not None else "-"
                ),
            ]
            draw_text_lines(pygame, display, font, lines)

            pygame.display.flip()

    finally:
        # 给 CARLA 一点点时间处理最后一次控制，随后清理。
        time.sleep(0.1)
        destroy_actors(actors)
        pygame.quit()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
