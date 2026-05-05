"""
06_detection_to_ground_pipeline.py

目标：
把“后续接车道线/路口检测模型”的接口提前搭出来：

  模型输出图像像素点 (u, v)
      -> pixel_to_world_on_ground 反投影到路面世界点
      -> 对世界点做简单滤波，减少检测抖动
      -> 用平滑后的目标点绘制 AR 贴地箭头

这里没有接真实模型，而是用一个“合成检测器”模拟模型输出：
  1. 先在车辆前方构造一个真实 world target；
  2. 投影到图像像素；
  3. 加一点像素噪声，模拟模型检测误差；
  4. 再从 noisy pixel 反投影回 world。

运行：
  C:\\Users\\cicii\\miniconda3\\envs\\carla_test\\python.exe 06_detection_to_ground_pipeline.py

操作：
  W/A/S/D 或方向键   开车
  T                  切换检测目标：左转/右转/直行
  N                  开关像素噪声
  R                  重置滤波器
  ESC                退出
"""

import random
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
    ("left turn candidate", 18.0, -5.5),
    ("right turn candidate", 18.0, 5.5),
    ("straight candidate", 24.0, 0.0),
]


class GroundTargetFilter(object):
    """
    一个最小的一阶低通滤波器。

    真实检测模型会抖：
      第 1 帧检测点在 (u=620, v=520)
      第 2 帧可能跳到 (u=626, v=517)

    像素抖动反投影到远处地面后，世界坐标会放大抖动。
    所以常见做法是在世界坐标或 BEV 坐标中做滤波/跟踪。

    这里用指数滑动平均：
      filtered = (1-alpha) * old + alpha * measurement
    """

    def __init__(self, alpha=0.28):
        self.alpha = alpha
        self.location = None

    def reset(self):
        self.location = None

    def update(self, measurement):
        if measurement is None:
            return self.location

        if self.location is None:
            self.location = carla.Location(
                x=measurement.x,
                y=measurement.y,
                z=measurement.z,
            )
            return self.location

        a = self.alpha
        self.location.x = (1.0 - a) * self.location.x + a * measurement.x
        self.location.y = (1.0 - a) * self.location.y + a * measurement.y
        self.location.z = measurement.z
        return self.location


def draw_cross(pygame, display, center, color, size=8):
    """画一个检测点十字。"""
    x, y = int(center[0]), int(center[1])
    pygame.draw.line(display, color, (x - size, y), (x + size, y), 2)
    pygame.draw.line(display, color, (x, y - size), (x, y + size), 2)


def draw_arrow_overlay(pygame, display, points):
    if not points:
        return
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(overlay, (30, 210, 255, 105), points)
    pygame.draw.lines(overlay, (210, 255, 255, 220), True, points, 2)
    display.blit(overlay, (0, 0))


def main():
    pygame.init()
    pygame.font.init()

    display = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.HWSURFACE | pygame.DOUBLEBUF,
    )
    pygame.display.set_caption("Lesson 06 - detection pixel to ground pipeline")

    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    k = build_camera_matrix(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)
    client, world = connect_client()

    actors = []
    current_steer = 0.0
    target_mode_index = 0
    add_noise = True
    target_filter = GroundTargetFilter(alpha=0.28)

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
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_t:
                        target_mode_index = (target_mode_index + 1) % len(TARGET_MODES)
                        target_filter.reset()
                    elif event.key == pygame.K_n:
                        add_noise = not add_noise
                    elif event.key == pygame.K_r:
                        target_filter.reset()

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
            ahead_point = ground_point_from_vehicle(world, vehicle, 9.0, 0.0)

            mode_name, forward_m, right_m = TARGET_MODES[target_mode_index]
            true_world_target = ground_point_from_vehicle(world, vehicle, forward_m, right_m)

            # 合成检测器：world target -> pixel。
            # 真实模型接入时，直接把模型输出的像素点填到 detected_pixel 即可。
            true_pixel = world_to_pixel(
                true_world_target,
                camera_transform,
                k,
                WINDOW_WIDTH,
                WINDOW_HEIGHT,
                margin=80.0,
            )

            detected_pixel = None
            raw_world_target = None
            if true_pixel is not None:
                u, v, depth = true_pixel
                if add_noise:
                    u += random.uniform(-4.0, 4.0)
                    v += random.uniform(-3.0, 3.0)
                detected_pixel = (u, v, depth)

                ground_z = get_ground_z(world, true_world_target) + 0.04
                raw_world_target = pixel_to_world_on_ground(
                    u,
                    v,
                    camera_transform,
                    k,
                    ground_z,
                )
                if raw_world_target is not None:
                    raw_world_target.z = ground_z

            filtered_world_target = target_filter.update(raw_world_target)

            if detected_pixel is not None:
                draw_cross(pygame, display, detected_pixel, (255, 80, 80))

            if raw_world_target is not None:
                raw_pixel = world_to_pixel(
                    raw_world_target,
                    camera_transform,
                    k,
                    WINDOW_WIDTH,
                    WINDOW_HEIGHT,
                    margin=80.0,
                )
                if raw_pixel is not None:
                    pygame.draw.circle(
                        display,
                        (255, 80, 80),
                        (int(raw_pixel[0]), int(raw_pixel[1])),
                        5,
                        0,
                    )
                draw_debug_point(world, raw_world_target, carla.Color(255, 80, 80), "raw")

            if filtered_world_target is not None:
                filtered_pixel = world_to_pixel(
                    filtered_world_target,
                    camera_transform,
                    k,
                    WINDOW_WIDTH,
                    WINDOW_HEIGHT,
                    margin=80.0,
                )
                if filtered_pixel is not None:
                    pygame.draw.circle(
                        display,
                        (30, 220, 255),
                        (int(filtered_pixel[0]), int(filtered_pixel[1])),
                        8,
                        0,
                    )

                arrow_polygon = make_arrow_polygon(ahead_point, filtered_world_target, width=1.25)
                arrow_pixels = project_locations(
                    arrow_polygon,
                    camera_transform,
                    k,
                    WINDOW_WIDTH,
                    WINDOW_HEIGHT,
                    margin=180.0,
                )
                if arrow_pixels is not None:
                    draw_arrow_overlay(pygame, display, arrow_pixels)

                draw_debug_ground_arrow(world, ahead_point, filtered_world_target)
                draw_debug_point(
                    world,
                    filtered_world_target,
                    carla.Color(30, 220, 255),
                    "filtered",
                )

            lines = [
                "Lesson 06 | synthetic detector pixel -> ground target -> filtered AR arrow",
                "T target mode | N noise {} | R reset filter | ESC quit".format(
                    "on" if add_noise else "off"
                ),
                "Mode: {} | red raw detection | cyan filtered target".format(mode_name),
                "Replace synthetic detector with your lane/intersection model output later.",
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
