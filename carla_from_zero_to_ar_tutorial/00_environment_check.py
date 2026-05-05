"""
00_environment_check.py

本节目标：
  1. 确认正在使用你指定的 conda Python；
  2. 确认可以 import carla；
  3. 确认可以连接 CARLA server；
  4. 打印地图、actor、blueprint 等基础信息。

如果这一节跑不通，后面所有 lesson 都不用急着跑。

运行前：
  先启动 CARLA server：
    D:\\HST_WORK\\carla\\WindowsNoEditor\\CarlaUE4.exe -carla-rpc-port=2000

运行：
  C:\\Users\\cicii\\miniconda3\\envs\\carla_test\\python.exe 00_environment_check.py
"""

import os
import sys

from common import carla
from common import connect_to_carla
from common import print_world_summary


def main():
    """
    主函数：检查 CARLA 开发环境是否配置正确。
    
    这个脚本是教程的第一步，用于验证：
      1. Python 环境是否正确
      2. CARLA 包是否能导入
      3. 能否连接到 CARLA server
      4. 地图、actor、blueprint 等基础功能是否正常
    """
    # ========================================================================
    # 1. 检查 Python 环境信息
    # ========================================================================
    print("Python executable:")
    # sys.executable: 当前运行的 Python 解释器路径
    # 确认你使用的是 conda 环境中的 Python，而不是系统 Python
    print("  {}".format(sys.executable))
    
    print("Python version:")
    # sys.version: Python 版本信息字符串
    # 替换换行符是为了让输出更紧凑
    print("  {}".format(sys.version.replace("\n", " ")))

    # ========================================================================
    # 2. 检查 CARLA Python 包
    # ========================================================================
    print("\nCARLA Python package:")
    # getattr(carla, "__file__", "unknown"): 获取 carla 模块的文件路径
    # 如果成功显示路径，说明 import carla 成功
    print("  {}".format(getattr(carla, "__file__", "unknown")))

    # ========================================================================
    # 3. 检查 CARLA 安装目录
    # ========================================================================
    print("\nExpected CARLA root:")
    # 从环境变量或默认值获取 CARLA 根目录
    # 这个目录应该包含 CarlaUE4.exe、PythonAPI 等
    print("  {}".format(os.environ.get("CARLA_ROOT", r"D:\HST_WORK\carla\WindowsNoEditor")))

    # ========================================================================
    # 4. 连接 CARLA server
    # ========================================================================
    # connect_to_carla() 来自 common.py
    # 内部会创建 carla.Client 并连接到 localhost:2000
    client, world = connect_to_carla()

    # ========================================================================
    # 5. 打印世界基本信息
    # ========================================================================
    print("")
    # print_world_summary() 来自 common.py
    # 会打印：地图名称、actor 数量、同步模式、固定时间步长
    print_world_summary(world)

    # ========================================================================
    # 6. 检查 Blueprint Library（蓝图库）
    # ========================================================================
    # Blueprint 是 CARLA 中可生成对象的模板
    # 类似面向对象编程中的"类"，spawn_actor 时根据 blueprint 创建具体实例
    blueprint_library = world.get_blueprint_library()
    
    # 使用通配符过滤不同类型的 blueprint
    # vehicle.*: 所有车辆类型
    vehicle_bps = blueprint_library.filter("vehicle.*")
    # sensor.camera.*: 所有相机传感器（RGB、深度、语义分割等）
    camera_bps = blueprint_library.filter("sensor.camera.*")
    # sensor.other.*: 其他传感器（IMU、GNSS、激光雷达等）
    other_sensor_bps = blueprint_library.filter("sensor.other.*")

    print("\nBlueprint 是 CARLA 里可生成对象的模板。")
    print("Blueprint counts:")
    print("  vehicle.*       :", len(vehicle_bps))
    print("  sensor.camera.* :", len(camera_bps))
    print("  sensor.other.*  :", len(other_sensor_bps))

    # ========================================================================
    # 7. 展示部分车辆 blueprint
    # ========================================================================
    print("\nSome vehicle blueprints:")
    # 只显示前 8 个车辆 blueprint，避免输出太多
    # 注意：BlueprintLibrary 不支持切片，需要先转成 list
    for bp in list(vehicle_bps)[:8]:
        # bp.id: blueprint 的唯一标识符，例如 "vehicle.tesla.model3"
        print("  {}".format(bp.id))

    # ========================================================================
    # 8. 展示部分传感器 blueprint
    # ========================================================================
    print("\nSome sensor blueprints:")
    # 显示前 5 个相机传感器
    for bp in list(camera_bps)[:5]:
        print("  {}".format(bp.id))
    # 显示前 8 个其他传感器
    for bp in list(other_sensor_bps)[:8]:
        print("  {}".format(bp.id))

    # ========================================================================
    # 9. 检查地图出生点
    # ========================================================================
    # get_spawn_points(): 获取地图上预定义的可用出生点
    # 这些点是 CARLA 官方设计的适合生成车辆的位置
    spawn_points = world.get_map().get_spawn_points()
    print("\nSpawn points on current map:", len(spawn_points))
    if spawn_points:
        print("First spawn point:")
        # 显示第一个出生点的 Transform（位置 + 旋转）
        print("  {}".format(spawn_points[0]))

    # ========================================================================
    # 10. 完成检查
    # ========================================================================
    print("\nOK：环境、连接、地图、blueprint 都能访问。")


if __name__ == "__main__":
    main()
