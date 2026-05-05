"""
03_vehicle_local_coordinate.py

本节目标：
  1. 理解车辆局部坐标；
  2. 把“车辆前方/左侧/右侧”的点转换到 CARLA world；
  3. 用 world.debug.draw_point/draw_arrow 在 CARLA 世界里可视化。

车辆局部坐标非常重要，因为你后面会频繁表达：
  车前方 10 米
  车左侧 2 米
  相机挂在车头前方 1.25 米、左侧 0.35 米、高 1.35 米

CARLA 车辆局部坐标：
  +X：车头方向
  +Y：车辆右侧
  +Z：车辆上方
"""

import time

from common import carla
from common import connect_to_carla
from common import debug_draw_point
from common import destroy_actors
from common import ground_point_in_vehicle_frame
from common import print_vehicle_local_axes
from common import spawn_ego_vehicle


def draw_vehicle_axes(world, vehicle, life_time=0.12):
    """
    在 CARLA 世界里画出车辆局部 +X/+Y/+Z 轴。
    
    这个函数帮助你可视化车辆的局部坐标系：
      - 红色箭头：+X 轴（车头方向，forward）
      - 绿色箭头：+Y 轴（车辆右侧，right）
      - 蓝色箭头：+Z 轴（车辆上方，up）
    
    参数：
      world: CARLA 世界对象
      vehicle: 车辆 actor
      life_time: 调试图形存活时间（秒），0.12 表示每帧重绘
    
    为什么需要这个？
      - 帮助你理解车辆局部坐标和世界坐标的关系
      - 直观看到 get_forward_vector/get_right_vector/get_up_vector 的方向
      - 验证坐标系是否正确
    """
    # 获取车辆当前的 Transform
    transform = vehicle.get_transform()
    # 车辆的位置（坐标原点）
    origin = transform.location
    # 车辆的三个局部轴在世界坐标中的方向（单位向量）
    forward = transform.get_forward_vector()  # +X 轴
    right = transform.get_right_vector()      # +Y 轴
    up = transform.get_up_vector()            # +Z 轴

    # 辅助函数：从原点沿某个向量方向延伸一定距离
    def add_vector(vector, scale):
        """
        计算从原点沿 vector 方向延伸 scale 米后的位置。
        
        例如：
          origin = (10, 20, 0)
          vector = (1, 0, 0)  # +X 方向
          scale = 5
          返回: (15, 20, 0)  # 原点向 +X 方向移动 5 米
        """
        return carla.Location(
            origin.x + vector.x * scale,
            origin.y + vector.y * scale,
            origin.z + vector.z * scale,
        )

    # 绘制红色箭头：+X 轴（车头方向），长度 5 米
    world.debug.draw_arrow(
        origin, add_vector(forward, 6.0),
        thickness=0.08, arrow_size=0.6,
        color=carla.Color(255, 0, 0), life_time=life_time,
    )
    # 绘制绿色箭头：+Y 轴（车辆右侧），长度 3 米
    world.debug.draw_arrow(
        origin, add_vector(right, 6.0),
        thickness=0.08, arrow_size=0.6,
        color=carla.Color(0, 255, 0), life_time=life_time,
    )
    # 绘制蓝色箭头：+Z 轴（车辆上方），长度 2.5 米
    world.debug.draw_arrow(
        origin, add_vector(up, 6),
        thickness=0.08, arrow_size=0.6,
        color=carla.Color(0, 80, 255), life_time=life_time,
    )


def main():
    """
    主函数：演示车辆局部坐标和世界坐标的转换。
    
    学习重点：
      1. 理解车辆局部坐标系（+X 前，+Y 右，+Z 上）
      2. 学会把“车前方 X 米、左侧 Y 米”转换成世界坐标
      3. 使用 debug_draw 在 CARLA 世界中可视化点
    
    实际应用场景：
      - AR 导航：在车前方地面画箭头
      - 障碍物检测：标记车左侧 2 米的物体
      - 传感器安装：相机挂在车头前方 1.25 米、左侧 0.35 米
    
    实验流程：
      1. 生成车辆并打印局部坐标轴信息
      2. 定义几个测试点（车前方、左侧、右侧）
      3. 把这些局部坐标点转换成世界坐标
      4. 在 CARLA 窗口中用箭头和点可视化
    """
    # ========================================================================
    # 第 1 步：连接 CARLA
    # ========================================================================
    client, world = connect_to_carla()
    actors = []

    try:
        # ====================================================================
        # 第 2 步：生成车辆
        # ====================================================================
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        # 打印车辆局部坐标轴的详细信息
        # 包括：车辆位置、旋转、以及三个轴在世界坐标中的方向
        print_vehicle_local_axes(vehicle)

        # ====================================================================
        # 第 3 步：定义测试点
        # ====================================================================
        # 定义几个典型的局部坐标点，用于测试转换
        # 格式：(名称, 前方距离, 右侧距离, 颜色)
        #   前方距离：正数表示车头前，负数表示车尾后
        #   右侧距离：正数表示右侧，负数表示左侧
        samples = [
            ("front 8m", 8.0, 0.0, carla.Color(255, 255, 0)),     # 车前方 8 米（黄色）
            ("front 12m", 12.0, 0.0, carla.Color(255, 160, 0)),   # 车前方 12 米（橙色）
            ("left", 10.0, -2.5, carla.Color(0, 220, 255)),       # 车前方 10 米、左侧 2.5 米（青色）
            ("right", 10.0, 2.5, carla.Color(255, 0, 255)),       # 车前方 10 米、右侧 2.5 米（紫色）
        ]

        print("\nLocal point -> world point:")
        # 遍历每个测试点，进行坐标转换
        for name, forward_m, right_m, color in samples:
            # ground_point_in_vehicle_frame() 来自 common.py
            # 它会把局部坐标点转换成世界坐标，并且自动调整 z 到地面高度
            point = ground_point_in_vehicle_frame(world, vehicle, forward_m, right_m)
            
            # 打印转换结果
            print("  {:10s} local(x={:.1f}, y={:.1f}) -> world({:.3f}, {:.3f}, {:.3f})".format(
                name, forward_m, right_m, point.x, point.y, point.z
            ))

        # ====================================================================
        # 第 4 步：可视化观察
        # ====================================================================
        print("\nCARLA 窗口里观察 15 秒。红色轴是车头 +X，绿色轴是右侧 +Y。")
        print("你会看到：")
        print("  - 红色箭头：车辆前向（+X）")
        print("  - 绿色箭头：车辆右侧（+Y）")
        print("  - 蓝色箭头：车辆上方（+Z）")
        print("  - 彩色点：测试点在地面上的位置\n")
        
        # 持续 15 秒刷新显示
        end_time = time.time() + 15.0
        while time.time() < end_time:
            # 每帧重绘车辆坐标轴（因为 life_time 很短，需要不断重绘）
            draw_vehicle_axes(world, vehicle)
            
            # 重绘所有测试点
            for name, forward_m, right_m, color in samples:
                # 重新计算点的位置（车辆可能移动了）
                point = ground_point_in_vehicle_frame(world, vehicle, forward_m, right_m)
                # 在 CARLA 世界中绘制点和标签
                debug_draw_point(world, point, color, name)
            
            # 每 0.05 秒刷新一次（20 FPS）
            time.sleep(0.05)

    finally:
        # ====================================================================
        # 第 5 步：清理资源
        # ====================================================================
        destroy_actors(actors)
        print("Cleaned up.")


if __name__ == "__main__":
    main()
