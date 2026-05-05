"""
02_transform_location_rotation.py

本节目标：
  1. 理解 Transform = Location + Rotation；
  2. 理解 Location 的 x/y/z；
  3. 理解 Rotation 的 pitch/yaw/roll；
  4. 改变车辆 yaw，观察 forward vector 怎么变化。

Location:
  x/y/z 是 CARLA 世界坐标，单位通常是米。

Rotation:
  yaw   ：绕 z 轴转，决定车头朝向。平面行驶最常用。
  pitch ：绕 y 轴转，车头抬起/低下。
  roll  ：绕 x 轴转，车辆左右倾斜。

Transform:
  同时包含位置和姿态。
"""

import math
import time

from common import carla
from common import connect_to_carla
from common import destroy_actors
from common import print_transform_details
from common import spawn_ego_vehicle


def print_forward_from_yaw(transform):
    """
    验证 CARLA 的 forward vector 和 yaw 角度的关系。
    
    这个函数帮助你理解：
      - yaw 角度如何影响车辆朝向
      - get_forward_vector() 返回什么
      - cos/sin 和 forward vector 的关系
    
    CARLA 里 transform.get_forward_vector() 应该和 yaw 的 cos/sin 对齐。
    这对后续轨迹积分和"车辆前方点"计算都很重要。
    
    数学原理：
      在 2D 平面中，如果 yaw=0° 指向 +X 轴（东），那么：
        forward.x = cos(yaw)
        forward.y = sin(yaw)
      
      CARLA 的坐标系：
        yaw=0°   -> 指向 +X（东）
        yaw=90°  -> 指向 +Y（南）
        yaw=180° -> 指向 -X（西）
        yaw=270° -> 指向 -Y（北）
    """
    # 获取车辆当前的前向向量（单位向量，长度为1）
    forward = transform.get_forward_vector()
    
    # 把 yaw 从度转换成弧度（math.cos/sin 需要弧度）
    yaw_rad = math.radians(transform.rotation.yaw)
    
    print("  forward vector      = ({:.4f}, {:.4f}, {:.4f})".format(
        forward.x, forward.y, forward.z
    ))
    print("  cos(yaw), sin(yaw)  = ({:.4f}, {:.4f})".format(
        math.cos(yaw_rad), math.sin(yaw_rad)
    ))
    # 如果两者一致，说明 CARLA 的 forward vector 计算正确


def main():
    """
    主函数：演示 Transform、Location、Rotation 的关系。
    
    学习重点：
      1. Transform = Location（位置）+ Rotation（旋转）
      2. Rotation 包含 pitch/yaw/roll 三个角度
      3. yaw 决定车头朝向，是最常用的旋转角度
      4. get_forward_vector() 根据 rotation 计算前向向量
    
    实验流程：
      1. 生成车辆
      2. 打印初始状态
      3. 每隔2秒改变一次 yaw 角度
      4. 观察 forward vector 的变化
      5. 验证 cos(yaw)/sin(yaw) 和 forward vector 的关系
    """
    # ========================================================================
    # 第 1 步：连接 CARLA
    # ========================================================================
    client, world = connect_to_carla()
    actors = []

    try:
        # ====================================================================
        # 第 2 步：生成车辆并记录初始状态
        # ====================================================================
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        # 获取车辆的初始 Transform（位置 + 旋转）
        original_transform = vehicle.get_transform()

        # 打印详细的 Transform 信息
        # 包括：location (x, y, z) 和 rotation (pitch, yaw, roll)
        print_transform_details("Original vehicle", original_transform)

        # 验证 forward vector 和 yaw 的关系
        print_forward_from_yaw(original_transform)

        #test
        for i in range(50):  # 循环 50 次，每次停留 0.1 秒
            transform = vehicle.get_transform()
            location = transform.location

            # --- 关键步骤：计算前方 10 米的坐标 ---
            forward_vector = transform.get_forward_vector()

            # 目标位置 = 当前位置 + (前向向量 * 距离)
            target_location = location + carla.Location(
                x=forward_vector.x * 10.0,
                y=forward_vector.y * 10.0,
                z=forward_vector.z + 1.5  # +1.5 是为了让字浮在空中，方便观察
            )

            # --- 方法 A：绘制一个红色的点 ---
            world.debug.draw_point(
                target_location,
                size=0.5,
                color=carla.Color(255, 0, 0),  # 红色
                life_time=0.1  # 持续时间，设为很短以便下一帧刷新位置
            )

            # --- 方法 B：绘制一段文字 ---
            world.debug.draw_string(
                target_location,
                '前方 10 米',
                draw_shadow=False,
                color=carla.Color(0, 255, 0),  # 绿色
                life_time=0.1
            )

            # 如果车辆移动了，这个标志会实时跟着动
            time.sleep(0.1)


        # ====================================================================
        # 第 3 步：循环改变 yaw 角度，观察变化
        # ====================================================================
        print("\n现在每 2 秒改变一次 yaw，观察 forward vector。")
        print("请在 CARLA UE4 窗口中观察车辆朝向的变化。\n")

        # 保存原始位置，只改变旋转，不改变位置
        base_location = original_transform.location

        # 测试不同的 yaw 角度
        # yaw 是绕 Z 轴的旋转，决定车头朝向（水平面内）
        # for yaw in [180.0, 135.0, 90.0, 45.0, 0.0, -45.0]:
        #     # 创建新的 Transform：位置不变，只改变 yaw
        #     new_transform = carla.Transform(
        #         carla.Location(base_location.x, base_location.y, base_location.z),
        #         carla.Rotation(pitch=0.0, yaw=yaw, roll=0.0),
        #     )
        #
        #     # 应用新的 Transform 到车辆
        #     # 车辆会瞬间旋转到新的朝向
        #     vehicle.set_transform(new_transform)
        #
        #     print("\nSet yaw = {:.1f} deg".format(yaw))
        #     # 打印当前车辆的 Transform 详情
        #     print_transform_details("Vehicle", vehicle.get_transform())
        #     # 验证 forward vector 是否和 yaw 匹配
        #     print_forward_from_yaw(vehicle.get_transform())
        #
        #     # 等待 2 秒，让你有时间观察
        #     time.sleep(2.0)

    finally:
        # ====================================================================
        # 第 4 步：清理资源
        # ====================================================================
        destroy_actors(actors)
        print("Cleaned up.")


if __name__ == "__main__":
    main()
