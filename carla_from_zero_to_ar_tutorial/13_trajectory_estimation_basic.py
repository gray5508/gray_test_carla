"""
13_trajectory_estimation_basic.py

本节目标：
  1. 用 CARLA ground truth 记录真实轨迹；
  2. 用 forward speed + yaw 做最基础轨迹积分；
  3. 保存 CSV；
  4. 理解轨迹估计为什么会漂。

这一节故意不用复杂 EKF，只用最基础公式：

  x = x + speed * cos(yaw) * dt
  y = y + speed * sin(yaw) * dt

其中：
  speed 来自车辆前向速度
  yaw 来自车辆当前 ground truth yaw

这不是完整定位算法，只是帮助你理解：
  坐标、速度、角度、dt 是怎么共同决定轨迹的。

核心知识点：
  - Dead Reckoning (航位推算): 通过速度和方向积分估算位置
  - 轨迹漂移: 由于传感器噪声、积分误差累积，估计位置会偏离真实位置
  - Ground Truth: CARLA 提供的真实位置和姿态，用于对比验证
  - CSV 日志: 记录轨迹数据，方便后续分析和可视化
  
为什么轨迹会漂移？
  1. 速度测量误差：即使很小的速度误差，经过长时间积分也会累积
  2. 角度测量误差：yaw 角的微小误差会导致方向偏差，随距离增加而放大
  3. 时间步长不均匀：dt 不准确会影响积分精度
  4. 没有校正机制：纯积分没有外部参考（如 GPS）来修正误差
  
应用场景：
  - 短期轨迹预测：在 GPS 信号丢失时提供短时定位
  - 传感器融合基础：作为 EKF/粒子滤波的状态预测步骤
  - 自动驾驶测试：验证明感系统的准确性
"""

import csv
import math
import os
import time

import pygame

from common import CameraSensor
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import connect_to_carla
from common import destroy_actors
from common import draw_text_lines
from common import get_forward_speed
from common import get_keyboard_vehicle_control
from common import make_pygame_surface
from common import spawn_ego_vehicle


class BasicTrajectoryEstimator(object):
    """
    一个最小轨迹积分器。

    初始化时把估计位置设为车辆真实位置。
    每帧根据速度、yaw、dt 往前积分。
    
    Attributes:
        initialized: 是否已初始化（第一帧设置为 True）
        last_time: 上一帧的时间戳
        est_x: 估计的 x 坐标
        est_y: 估计的 y 坐标
        records: 历史记录列表，用于保存 CSV
    """

    def __init__(self):
        """初始化轨迹估计器"""
        self.initialized = False  # 标记是否已完成初始化
        self.last_time = None  # 上一帧的时间戳
        self.est_x = 0.0  # 估计的 x 坐标
        self.est_y = 0.0  # 估计的 y 坐标
        self.records = []  # 存储历史记录的列表

    def update(self, vehicle):
        """
        更新轨迹估计
        
        使用简单的航位推算公式：
          est_x += speed * cos(yaw) * dt
          est_y += speed * sin(yaw) * dt
        
        Args:
            vehicle: CARLA 车辆对象，用于获取真实位置和速度
        """
        now = time.time()  # 当前时间戳
        transform = vehicle.get_transform()  # 获取车辆当前的位姿
        loc = transform.location  # 真实位置（ground truth）
        yaw_rad = math.radians(transform.rotation.yaw)  # 将 yaw 从度转换为弧度
        speed = get_forward_speed(vehicle)  # 获取前向速度

        if not self.initialized:
            # 第一帧：用真实位置初始化估计位置
            self.initialized = True
            self.last_time = now
            self.est_x = loc.x
            self.est_y = loc.y
            return

        # 计算时间间隔
        dt = now - self.last_time
        self.last_time = now

        # 防止窗口卡顿时 dt 过大，导致一次积分跳很远
        # 如果 dt > 0.2 秒，限制为 0.2 秒
        if dt > 0.2:
            dt = 0.2

        # 航位推算：根据速度和方向积分
        # speed * cos(yaw) 是 x 方向的速度分量
        # speed * sin(yaw) 是 y 方向的速度分量
        self.est_x += speed * math.cos(yaw_rad) * dt
        self.est_y += speed * math.sin(yaw_rad) * dt

        # 计算估计位置与真实位置的误差（欧氏距离）
        error = math.sqrt((self.est_x - loc.x) ** 2 + (self.est_y - loc.y) ** 2)
        
        # 记录当前帧的数据
        self.records.append({
            "time": now,  # 时间戳
            "dt": dt,  # 时间间隔
            "gt_x": loc.x,  # 真实 x 坐标 (ground truth)
            "gt_y": loc.y,  # 真实 y 坐标
            "yaw_deg": transform.rotation.yaw,  # 偏航角（度）
            "forward_speed_mps": speed,  # 前向速度 (m/s)
            "est_x": self.est_x,  # 估计 x 坐标
            "est_y": self.est_y,  # 估计 y 坐标
            "error_m": error,  # 估计误差 (米)
        })

    def save_csv(self):
        """
        将轨迹记录保存为 CSV 文件
        
        文件保存在 outputs/basic_trajectory_estimation.csv
        可以用 Excel、Python pandas 或其他工具分析
        
        Returns:
            str: CSV 文件的路径
        """
        # 创建输出目录
        output_dir = os.path.join(os.path.dirname(__file__), "outputs")
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        output_path = os.path.join(output_dir, "basic_trajectory_estimation.csv")

        # 如果没有记录，直接返回
        if not self.records:
            print("No trajectory records to save.")
            return output_path

        # CSV 文件的列名
        fieldnames = [
            "time", "dt", "gt_x", "gt_y", "yaw_deg",
            "forward_speed_mps", "est_x", "est_y", "error_m",
        ]
        
        # 写入 CSV 文件
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()  # 写入表头
            writer.writerows(self.records)  # 写入所有记录

        print("Saved:", output_path)
        return output_path


def main():
    """
    主函数：演示基本的轨迹估计并记录数据
    
    工作流程：
      1. 初始化 pygame 显示窗口
      2. 连接 CARLA 并生成车辆和 RGB 相机
      3. 创建轨迹估计器
      4. 每帧更新轨迹估计（使用航位推算）
      5. 在 HUD 中显示真实位置、估计位置和误差
      6. 退出时保存轨迹数据到 CSV 文件
      
    观察要点：
      - 随着行驶距离增加，误差会逐渐累积
      - 转弯时误差增长更快（角度误差的影响更大）
      - 可以通过 CSV 文件分析误差随时间的变化
    """
    # 初始化 pygame 和字体系统
    pygame.init()
    pygame.font.init()

    # 创建显示窗口
    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("13 basic trajectory estimation")
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    # 连接到 CARLA server
    client, world = connect_to_carla()
    
    actors = []
    current_steer = 0.0  # 当前方向盘转角
    estimator = BasicTrajectoryEstimator()  # 创建轨迹估计器

    try:
        # 生成自车
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)
        
        # 创建 RGB 相机用于显示
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
                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:  # ESC 退出并保存数据
                    running = False

            # 读取键盘状态，控制车辆
            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            # 更新轨迹估计
            estimator.update(vehicle)

            # 渲染 RGB 相机图像
            if camera.latest_rgb is not None:
                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))
            else:
                display.fill((10, 10, 10))

            # 获取车辆当前的位姿
            transform = vehicle.get_transform()
            loc = transform.location
            
            # 获取最新的误差值
            last_error = estimator.records[-1]["error_m"] if estimator.records else 0.0
            
            # 准备 HUD 显示的文字
            lines = [
                "Lesson 13 | basic trajectory estimation | ESC save and quit",
                "GT x={:.2f} y={:.2f} yaw={:.2f}".format(loc.x, loc.y, transform.rotation.yaw),
                "EST x={:.2f} y={:.2f} | error {:.2f}m".format(
                    estimator.est_x, estimator.est_y, last_error
                ),
                "Records: {}".format(len(estimator.records)),
                "This uses ground-truth yaw. Later you can replace yaw with IMU gyro integration.",  # 提示：后续可以用 IMU 陀螺仪积分替代真实 yaw
            ]
            draw_text_lines(pygame, display, font, lines)
            
            # 更新屏幕显示
            pygame.display.flip()

    finally:
        estimator.save_csv()
        destroy_actors(actors)
        pygame.quit()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
