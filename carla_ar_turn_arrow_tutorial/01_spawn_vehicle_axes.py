"""
01_spawn_vehicle_axes.py

目标：
1. 在固定起点生成一辆 ego vehicle；
2. 打印车辆世界坐标和局部坐标轴；
3. 在 CARLA 世界里用 debug arrow 画出车辆 local +X/+Y/+Z；
4. 理解“车辆前方 8 米”如何从 local 坐标变成 world 坐标。

运行：
  C:\\Users\\cicii\\miniconda3\\envs\\carla_test\\python.exe 01_spawn_vehicle_axes.py
"""

import time

from common import carla
from common import connect_client
from common import destroy_actors
from common import draw_debug_point
from common import ground_point_from_vehicle
from common import print_environment_summary
from common import print_vehicle_axes
from common import spawn_ego_vehicle


def add_vector(location, vector, scale):
    """location + vector * scale，手写出来便于看清楚。"""
    return carla.Location(
        x=location.x + vector.x * scale,
        y=location.y + vector.y * scale,
        z=location.z + vector.z * scale,
    )


def draw_vehicle_axes(world, vehicle, life_time=0.12):
    """
    在世界里画出车辆局部坐标轴：
      红色：local +X，车头方向
      绿色：local +Y，车辆右侧
      蓝色：local +Z，车辆上方
    """
    transform = vehicle.get_transform()
    origin = transform.location

    forward = transform.get_forward_vector()
    right = transform.get_right_vector()
    up = transform.get_up_vector()

    world.debug.draw_arrow(
        origin,
        add_vector(origin, forward, 5.0),
        thickness=0.08,
        arrow_size=0.6,
        color=carla.Color(255, 0, 0),
        life_time=life_time,
    )
    world.debug.draw_arrow(
        origin,
        add_vector(origin, right, 3.0),
        thickness=0.08,
        arrow_size=0.6,
        color=carla.Color(0, 255, 0),
        life_time=life_time,
    )
    world.debug.draw_arrow(
        origin,
        add_vector(origin, up, 2.5),
        thickness=0.08,
        arrow_size=0.6,
        color=carla.Color(0, 80, 255),
        life_time=life_time,
    )


def main():
    client, world = connect_client()
    print_environment_summary(world)

    actors = []
    try:
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        print_vehicle_axes(vehicle)

        print("\nLocal ground points:")
        examples = [
            ("front_8m", 8.0, 0.0),
            ("front_8m_left_2m", 8.0, -2.0),
            ("front_8m_right_2m", 8.0, 2.0),
        ]
        for name, forward_m, right_m in examples:
            point = ground_point_from_vehicle(world, vehicle, forward_m, right_m)
            print("  {} -> x={:.3f}, y={:.3f}, z={:.3f}".format(
                name, point.x, point.y, point.z
            ))

        print("\nCARLA 窗口里会显示 12 秒 debug 坐标轴和前方点。")
        print("红色 local +X 是车头，绿色 local +Y 是车辆右侧，蓝色 local +Z 向上。")

        end_time = time.time() + 12.0
        while time.time() < end_time:
            draw_vehicle_axes(world, vehicle)

            front = ground_point_from_vehicle(world, vehicle, 8.0, 0.0)
            left = ground_point_from_vehicle(world, vehicle, 8.0, -2.0)
            right = ground_point_from_vehicle(world, vehicle, 8.0, 2.0)

            draw_debug_point(world, front, carla.Color(255, 255, 0), "front 8m")
            draw_debug_point(world, left, carla.Color(0, 255, 255), "left")
            draw_debug_point(world, right, carla.Color(255, 0, 255), "right")

            time.sleep(0.05)

    finally:
        destroy_actors(actors)
        print("Cleaned up.")


if __name__ == "__main__":
    main()
