"""
12_vehicle_imu_gnss_speed.py

本节目标：
  1. 读取 vehicle.get_transform()；
  2. 读取 vehicle.get_velocity()；
  3. 计算 forward speed；
  4. 挂载 IMU / GNSS；
  5. 在 pygame HUD 里实时显示数据。

为什么这属于"融合层"？
  因为后续 AR overlay 不只依赖图像，还依赖车辆当前位姿、速度、IMU/GNSS。
  真正稳定的贴地箭头需要知道：
    车在哪里（transform/location）
    车朝哪（rotation/yaw）
    车速多少（velocity/speed）
    传感器数据是否对齐（sensor synchronization）

核心知识点：
  - Transform: 车辆的位姿（位置和姿态），包含 location (x,y,z) 和 rotation (pitch,yaw,roll)
  - Velocity: 车辆的速度向量，在世界坐标系中表示
  - Forward speed: 沿车头方向的速度分量，通过速度向量与前进方向的点积计算
  - IMU (Inertial Measurement Unit): 惯性测量单元，提供加速度、角速度、指南针数据
  - GNSS (Global Navigation Satellite System): 全球导航卫星系统，提供经纬度和高度
  
应用场景：
  - 车辆状态监控：实时显示车辆的位置、速度、姿态
  - 传感器融合：结合视觉、IMU、GNSS 数据进行更准确的定位
  - 轨迹估计：使用速度和角度积分估算车辆轨迹
  - 自动驾驶控制：基于车辆状态做出控制决策
"""

import math
import weakref

import pygame

from common import CameraSensor
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import carla
from common import connect_to_carla
from common import destroy_actors
from common import draw_text_lines
from common import get_forward_speed
from common import get_keyboard_vehicle_control
from common import get_planar_speed
from common import make_pygame_surface
from common import spawn_ego_vehicle


class ImuGnssBundle(object):
    """
    管理 IMU 和 GNSS 传感器的类。

    这里仍然使用 sensor.listen 的异步回调。
    对入门显示和手动驾驶足够。
    后续严谨实验可以转到 synchronous mode（同步模式）。
    
    Attributes:
        latest_imu: 最新的 IMU 数据，包含加速度计、陀螺仪、指南针
        latest_gnss: 最新的 GNSS 数据，包含纬度、经度、高度
        imu: IMU sensor actor
        gnss: GNSS sensor actor
    """

    def __init__(self, world, vehicle):
        """
        初始化 IMU 和 GNSS 传感器
        
        Args:
            world: CARLA world 对象
            vehicle: 要附加传感器的车辆
        """
        self.latest_imu = None  # 最新的 IMU 数据
        self.latest_gnss = None  # 最新的 GNSS 数据

        # 获取 blueprint 库
        bp_lib = world.get_blueprint_library()

        # 创建 IMU 传感器
        # IMU 提供：
        #   - accelerometer: 三轴加速度 (m/s^2)
        #   - gyroscope: 三轴角速度 (rad/s)
        #   - compass: 指南针方向 (弧度)
        imu_bp = bp_lib.find("sensor.other.imu")
        imu_bp.set_attribute("sensor_tick", "0.05")  # 每 0.05 秒更新一次 (20 Hz)

        # 创建 GNSS 传感器
        # GNSS 提供：
        #   - latitude: 纬度 (度)
        #   - longitude: 经度 (度)
        #   - altitude: 海拔高度 (米)
        gnss_bp = bp_lib.find("sensor.other.gnss")
        gnss_bp.set_attribute("sensor_tick", "0.10")  # 每 0.10 秒更新一次 (10 Hz)

        # 将 IMU 附加到车辆上
        # transform 指定传感器相对于车辆的位置，这里设为 (0,0,0) 表示在车辆中心
        self.imu = world.spawn_actor(
            imu_bp,
            carla.Transform(carla.Location(x=0.0, y=0.0, z=0.0)),
            attach_to=vehicle,
        )
        
        # 将 GNSS 附加到车辆上
        self.gnss = world.spawn_actor(
            gnss_bp,
            carla.Transform(carla.Location(x=0.0, y=0.0, z=0.0)),
            attach_to=vehicle,
        )

        # 使用 weakref 避免循环引用导致的内存泄漏
        # 当 ImuGnssBundle 对象被销毁时，weakref 会自动失效
        weak_self = weakref.ref(self)
        
        # 注册回调函数，当传感器有新数据时会被调用
        self.imu.listen(lambda data: ImuGnssBundle._on_imu(weak_self, data))
        self.gnss.listen(lambda data: ImuGnssBundle._on_gnss(weak_self, data))

    @staticmethod
    def _on_imu(weak_self, data):
        """
        IMU 数据回调函数
        
        Args:
            weak_self: ImuGnssBundle 的弱引用
            data: IMU 传感器数据，包含 accelerometer, gyroscope, compass
        """
        self = weak_self()
        if self is not None:
            self.latest_imu = data  # 保存最新的 IMU 数据

    @staticmethod
    def _on_gnss(weak_self, data):
        """
        GNSS 数据回调函数
        
        Args:
            weak_self: ImuGnssBundle 的弱引用
            data: GNSS 传感器数据，包含 latitude, longitude, altitude
        """
        self = weak_self()
        if self is not None:
            self.latest_gnss = data  # 保存最新的 GNSS 数据

    def actors(self):
        """
        返回所有传感器 actor 列表，方便统一清理
        
        Returns:
            list: 包含 imu 和 gnss actor 的列表
        """
        return [self.imu, self.gnss]


def main():
    """
    主函数：实时显示车辆状态和传感器数据
    
    工作流程：
      1. 初始化 pygame 显示窗口
      2. 连接 CARLA 并生成车辆、RGB 相机、IMU、GNSS
      3. 每帧读取车辆状态（位置、姿态、速度）
      4. 从 IMU 获取加速度、角速度、指南针数据
      5. 从 GNSS 获取经纬度和高度
      6. 在 HUD 中实时显示所有信息
      
    显示内容：
      - 车辆控制指令：油门、刹车、转向、倒挡
      - 车辆位置：世界坐标 (x, y, z)
      - 车辆姿态：俯仰角 pitch、偏航角 yaw、翻滚角 roll
      - 车辆速度：前向速度 forward speed、水平速度 planar speed
      - IMU 数据：三轴加速度、三轴角速度、指南针方向
      - GNSS 数据：纬度、经度、高度
    """
    # 初始化 pygame 和字体系统
    pygame.init()
    pygame.font.init()

    # 创建显示窗口
    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("12 vehicle IMU GNSS speed")
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    # 连接到 CARLA server
    client, world = connect_to_carla()
    
    actors = []
    current_steer = 0.0  # 当前方向盘转角

    try:
        # 生成自车
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        # 创建 RGB 相机用于显示
        camera = CameraSensor(world, vehicle, "sensor.camera.rgb")
        actors.append(camera.actor)

        # 创建 IMU 和 GNSS 传感器 bundle
        sensors = ImuGnssBundle(world, vehicle)
        actors.extend(sensors.actors())

        running = True
        while running:
            # 限制循环频率为 30 FPS
            clock.tick(30)

            # 处理 pygame 事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:  # 窗口关闭
                    running = False
                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:  # ESC 退出
                    running = False

            # 读取键盘状态，控制车辆
            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            # 渲染 RGB 相机图像
            if camera.latest_rgb is not None:
                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))
            else:
                display.fill((10, 10, 10))

            # 获取车辆当前的位姿（位置和姿态）
            transform = vehicle.get_transform()
            location = transform.location  # 位置 (x, y, z)
            rotation = transform.rotation  # 姿态 (pitch, yaw, roll)

            # 准备 HUD 显示的文字列表
            lines = [
                "Lesson 12 | vehicle transform + speed + IMU/GNSS | ESC quit",
                "Control throttle={:.2f} brake={:.2f} steer={:.2f} reverse={}".format(
                    control.throttle, control.brake, control.steer, control.reverse
                ),
                "Vehicle loc x={:.2f} y={:.2f} z={:.2f}".format(location.x, location.y, location.z),
                "Vehicle rot pitch={:.2f} yaw={:.2f} roll={:.2f}".format(
                    rotation.pitch, rotation.yaw, rotation.roll
                ),
                "Speed forward={:.2f} m/s planar={:.2f} m/s".format(
                    get_forward_speed(vehicle), get_planar_speed(vehicle)
                ),
            ]

            # 添加 IMU 数据到 HUD
            imu = sensors.latest_imu
            if imu is None:
                lines.append("IMU: waiting...")  # 等待 IMU 数据
            else:
                # 显示三轴加速度 (m/s^2)
                lines.append("IMU accel x={:.3f} y={:.3f} z={:.3f}".format(
                    imu.accelerometer.x, imu.accelerometer.y, imu.accelerometer.z
                ))
                # 显示三轴角速度 (rad/s) 和指南针方向 (度)
                lines.append("IMU gyro  x={:.3f} y={:.3f} z={:.3f} | compass {:.2f}deg".format(
                    imu.gyroscope.x, imu.gyroscope.y, imu.gyroscope.z,
                    math.degrees(imu.compass),  # 将弧度转换为度
                ))

            # 添加 GNSS 数据到 HUD
            gnss = sensors.latest_gnss
            if gnss is None:
                lines.append("GNSS: waiting...")  # 等待 GNSS 数据
            else:
                # 显示纬度、经度、高度
                lines.append("GNSS lat={:.8f} lon={:.8f} alt={:.2f}".format(
                    gnss.latitude, gnss.longitude, gnss.altitude
                ))

            # 绘制 HUD 文字
            draw_text_lines(pygame, display, font, lines)
            
            # 更新屏幕显示
            pygame.display.flip()

    finally:
        destroy_actors(actors)
        pygame.quit()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
