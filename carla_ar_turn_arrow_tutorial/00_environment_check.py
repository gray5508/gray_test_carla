"""
00_environment_check.py

目标：
1. 确认 Python 能 import carla；
2. 确认能连接到你手动启动的 CARLA server；
3. 打印地图、actor、常用 blueprint；
4. 提醒当前实际版本是 0.9.15。

运行：
  C:\\Users\\cicii\\miniconda3\\envs\\carla_test\\python.exe 00_environment_check.py
"""

import os
import sys

from common import carla
from common import connect_client
from common import print_environment_summary


def main():
    print("Python executable:")
    print("  {}".format(sys.executable))
    print("Python version:")
    print("  {}".format(sys.version.replace("\n", " ")))

    print("\nCARLA Python package:")
    print("  file: {}".format(getattr(carla, "__file__", "unknown")))
    print("  pip version may be visible with: python -m pip show carla")

    carla_root = os.environ.get("CARLA_ROOT", r"D:\HST_WORK\carla\WindowsNoEditor")
    print("\nExpected CARLA root:")
    print("  {}".format(carla_root))
    print("Detected packaged simulator version:")
    print("  D:\\HST_WORK\\carla\\WindowsNoEditor\\CarlaUE4\\Config\\DefaultGame.ini -> 0.9.15")

    client, world = connect_client()
    print("")
    print_environment_summary(world)

    blueprints = world.get_blueprint_library()
    vehicle_bps = blueprints.filter("vehicle.*")
    camera_bps = blueprints.filter("sensor.camera.*")
    other_sensor_bps = blueprints.filter("sensor.other.*")

    print("\nBlueprint counts:")
    print("  vehicles:", len(vehicle_bps))
    print("  cameras: ", len(camera_bps))
    print("  other sensors:", len(other_sensor_bps))

    print("\nSome vehicle blueprints:")
    for bp in vehicle_bps[:8]:
        print("  {}".format(bp.id))

    print("\nSome camera/sensor blueprints:")
    for bp in (camera_bps[:6] + other_sensor_bps[:8]):
        print("  {}".format(bp.id))

    spawn_points = world.get_map().get_spawn_points()
    print("\nSpawn points:", len(spawn_points))
    if spawn_points:
        print("First spawn point:")
        print("  {}".format(spawn_points[0]))

    print("\nOK. 如果这里能正常打印，后面的 lesson 就可以继续。")


if __name__ == "__main__":
    main()
