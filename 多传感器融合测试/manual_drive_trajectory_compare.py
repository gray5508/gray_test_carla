import os
import csv
import math
import time
import weakref
from datetime import datetime

import carla
import pygame
import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# 0. 教学说明
# ============================================================
#
# 这个脚本用于 CARLA 手动驾驶 + 传感器轨迹对比实验。
#
# 它会绘制三条轨迹：
#
# 1. CARLA Ground Truth
#    直接从 vehicle.get_transform().location 读取。
#    这是 CARLA 给出的真实车辆位置，用作标准答案。
#
# 2. Speed + IMU Gyro Odometry
#    用车辆前向速度 + IMU gyro.z 积分 yaw 来估计轨迹。
#    这类似真实车上的 “轮速计 + IMU 陀螺仪”。
#
# 3. Speed + IMU Gyro + GNSS Fusion
#    在第 2 条轨迹基础上，用 GNSS 位置做简单修正。
#    这里不是严格 EKF，只是固定权重融合，方便入门理解。
#
# 按 ESC 退出后，会保存：
#
#   trajectory_plot.png
#   trajectory_error_plot.png
#   trajectory_data.csv
#   summary.txt
#
# ============================================================


# ============================================================
# 1. 车辆起点：保持你的原始固定位置不变
# ============================================================
START_TRANSFORM = carla.Transform(
    carla.Location(x=55.754353, y=130.663452, z=0.500000),
    carla.Rotation(pitch=0.000000, yaw=180.320450, roll=0.000000)
)


# ============================================================
# 2. 基本配置
# ============================================================
HOST = "localhost"
PORT = 2000
TIMEOUT = 30.0

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

PRINT_INTERVAL = 1.0


# ============================================================
# 3. 工具函数
# ============================================================

def normalize_angle_rad(angle):
    """
    把角度限制到 [-pi, pi]。

    为什么要做这个？
    因为 yaw 角会一直加，比如超过 180 度后可能变成 181、182。
    对计算来说，181 度和 -179 度其实差不多。
    所以我们把它统一归一化，避免角度越来越大。
    """
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def get_forward_speed(vehicle):
    """
    获取车辆沿车头方向的速度。

    以前我们可能会写：
        speed = sqrt(vx^2 + vy^2 + vz^2)

    但这个会把 z 方向速度也算进去。
    车辆刚生成、落地、颠簸时，z 方向可能会有速度，
    这会导致轨迹估计提前移动。

    所以这里用速度向量 dot 车辆前向向量：

        forward_speed = velocity · forward_vector

    好处：
    1. 只关心车头方向速度；
    2. 倒车时可以得到负速度；
    3. 更接近真实车上的轮速计。
    """
    velocity = vehicle.get_velocity()
    transform = vehicle.get_transform()
    forward = transform.get_forward_vector()

    speed = (
        velocity.x * forward.x +
        velocity.y * forward.y +
        velocity.z * forward.z
    )

    return speed


def get_planar_speed(vehicle):
    """
    获取水平面速度大小，只用 x/y，不用 z。

    这个主要用于显示，不参与核心 odometry。
    """
    velocity = vehicle.get_velocity()
    return math.sqrt(velocity.x ** 2 + velocity.y ** 2)


def get_3d_speed(vehicle):
    """
    获取三维速度大小，主要用于调试显示。
    """
    velocity = vehicle.get_velocity()
    return math.sqrt(velocity.x ** 2 + velocity.y ** 2 + velocity.z ** 2)


# ============================================================
# 4. 摄像头管理器：pygame 第一视角
# ============================================================

class DriverCameraManager:
    """
    把一个 RGB 摄像头挂在车辆前挡风玻璃/驾驶员位置，
    然后把图像显示在 pygame 窗口里。

    注意：
    这不是 UE spectator 视角。
    这是一个真正的 carla sensor.camera.rgb。
    所以不会和 UE 窗口 WASD 自由相机冲突。
    """

    def __init__(self, world, vehicle, width=1280, height=720):
        self.world = world
        self.vehicle = vehicle
        self.width = width
        self.height = height

        self.camera = None
        self.surface = None

        blueprint_library = self.world.get_blueprint_library()
        camera_bp = blueprint_library.find("sensor.camera.rgb")

        camera_bp.set_attribute("image_size_x", str(width))
        camera_bp.set_attribute("image_size_y", str(height))
        camera_bp.set_attribute("fov", "90")

        # ------------------------------------------------------------
        # 摄像头相对车辆的位置
        #
        # CARLA 车辆局部坐标：
        #   x 正方向：车头
        #   y 正方向：车辆右侧
        #   z 正方向：向上
        #
        # x=1.15: 稍微靠近车头
        # y=-0.35: 偏左，模拟左舵驾驶位
        # z=1.35: 眼睛高度
        #
        # 如果画面被车体挡住，可以把 x 调大：
        #   x=1.45 或 x=2.20
        # ------------------------------------------------------------
        camera_transform = carla.Transform(
            carla.Location(x=1.15, y=-0.35, z=1.35),
            carla.Rotation(pitch=-2.0, yaw=0.0, roll=0.0)
        )

        self.camera = self.world.spawn_actor(
            camera_bp,
            camera_transform,
            attach_to=self.vehicle,
            attachment_type=carla.AttachmentType.Rigid
        )

        weak_self = weakref.ref(self)
        self.camera.listen(lambda image: DriverCameraManager._parse_image(weak_self, image))

    @staticmethod
    def _parse_image(weak_self, image):
        self = weak_self()
        if self is None:
            return

        array = np.frombuffer(image.raw_data, dtype=np.uint8)
        array = np.reshape(array, (image.height, image.width, 4))

        # CARLA 图像格式是 BGRA。
        # pygame 显示需要 RGB。
        array = array[:, :, :3]
        array = array[:, :, ::-1]

        # pygame surface 需要 width, height 顺序，
        # 所以这里 swapaxes。
        self.surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))

    def render(self, display):
        if self.surface is not None:
            display.blit(self.surface, (0, 0))

    def destroy(self):
        if self.camera is not None:
            self.camera.stop()
            self.camera.destroy()
            self.camera = None


# ============================================================
# 5. 传感器管理器：IMU + GNSS
# ============================================================

class SensorManager:
    """
    管理 IMU 和 GNSS。

    IMU 提供：
      accelerometer: 加速度
      gyroscope: 角速度
      compass: 指南针方向

    GNSS 提供：
      latitude
      longitude
      altitude
    """

    def __init__(self, world, vehicle):
        self.world = world
        self.vehicle = vehicle

        self.imu_sensor = None
        self.gnss_sensor = None

        self.latest_imu = None
        self.latest_gnss = None

        self._spawn_imu()
        self._spawn_gnss()

    def _spawn_imu(self):
        blueprint_library = self.world.get_blueprint_library()
        imu_bp = blueprint_library.find("sensor.other.imu")

        # 20Hz
        imu_bp.set_attribute("sensor_tick", "0.05")

        imu_transform = carla.Transform(
            carla.Location(x=0.0, y=0.0, z=0.0),
            carla.Rotation()
        )

        self.imu_sensor = self.world.spawn_actor(
            imu_bp,
            imu_transform,
            attach_to=self.vehicle
        )

        weak_self = weakref.ref(self)
        self.imu_sensor.listen(lambda data: SensorManager._on_imu(weak_self, data))

    def _spawn_gnss(self):
        blueprint_library = self.world.get_blueprint_library()
        gnss_bp = blueprint_library.find("sensor.other.gnss")

        # 10Hz
        gnss_bp.set_attribute("sensor_tick", "0.1")

        gnss_transform = carla.Transform(
            carla.Location(x=0.0, y=0.0, z=0.0),
            carla.Rotation()
        )

        self.gnss_sensor = self.world.spawn_actor(
            gnss_bp,
            gnss_transform,
            attach_to=self.vehicle
        )

        weak_self = weakref.ref(self)
        self.gnss_sensor.listen(lambda data: SensorManager._on_gnss(weak_self, data))

    @staticmethod
    def _on_imu(weak_self, data):
        self = weak_self()
        if self is None:
            return
        self.latest_imu = data

    @staticmethod
    def _on_gnss(weak_self, data):
        self = weak_self()
        if self is None:
            return
        self.latest_gnss = data

    def print_latest_data(self):
        transform = self.vehicle.get_transform()
        location = transform.location
        rotation = transform.rotation

        forward_speed = get_forward_speed(self.vehicle)
        planar_speed = get_planar_speed(self.vehicle)
        speed_3d = get_3d_speed(self.vehicle)

        print("\n================ SENSOR DATA ================")

        print("Vehicle Location:")
        print("  x: {:.3f}, y: {:.3f}, z: {:.3f}".format(
            location.x, location.y, location.z
        ))

        print("Vehicle Rotation:")
        print("  pitch: {:.3f}, yaw: {:.3f}, roll: {:.3f}".format(
            rotation.pitch, rotation.yaw, rotation.roll
        ))

        print("Vehicle Speed:")
        print("  forward: {:.3f} m/s | {:.3f} km/h".format(
            forward_speed, forward_speed * 3.6
        ))
        print("  planar:  {:.3f} m/s".format(planar_speed))
        print("  3d:      {:.3f} m/s".format(speed_3d))

        if self.latest_imu is not None:
            imu = self.latest_imu
            accel = imu.accelerometer
            gyro = imu.gyroscope
            compass = imu.compass

            print("IMU:")
            print("  accelerometer:")
            print("    x: {:.6f}, y: {:.6f}, z: {:.6f}".format(
                accel.x, accel.y, accel.z
            ))
            print("  gyroscope:")
            print("    x: {:.6f}, y: {:.6f}, z: {:.6f}".format(
                gyro.x, gyro.y, gyro.z
            ))
            print("  compass:")
            print("    {:.6f} rad | {:.3f} deg".format(
                compass, math.degrees(compass)
            ))
        else:
            print("IMU: No data yet")

        if self.latest_gnss is not None:
            gnss = self.latest_gnss

            print("GNSS:")
            print("  latitude:  {:.8f}".format(gnss.latitude))
            print("  longitude: {:.8f}".format(gnss.longitude))
            print("  altitude:  {:.3f}".format(gnss.altitude))
        else:
            print("GNSS: No data yet")

        print("=============================================")

    def destroy(self):
        if self.imu_sensor is not None:
            self.imu_sensor.stop()
            self.imu_sensor.destroy()
            self.imu_sensor = None

        if self.gnss_sensor is not None:
            self.gnss_sensor.stop()
            self.gnss_sensor.destroy()
            self.gnss_sensor = None


# ============================================================
# 6. 坐标系调试器
# ============================================================

class CoordinateDebugger:
    """
    用来帮助理解 CARLA 的坐标系。

    它会打印：
      车辆世界坐标
      车辆 forward/right/up 在世界坐标中的方向
      yaw 对应的 cos/sin 是否等于 forward vector
      gyro.z 和 ground truth yaw 变化的符号是否一致

    如果 gyro.z 符号和 CARLA yaw 变化方向相反，
    它会自动选择 gyro_z_sign = -1。
    """

    def __init__(self):
        self.last_time = None
        self.last_yaw_rad = None

        self.samples = []
        self.gyro_z_sign = 1.0
        self.sign_locked = False

    def print_axis_info(self, vehicle):
        transform = vehicle.get_transform()
        loc = transform.location
        rot = transform.rotation

        forward = transform.get_forward_vector()
        right = transform.get_right_vector()
        up = transform.get_up_vector()

        yaw_rad = math.radians(rot.yaw)
        yaw_forward_x = math.cos(yaw_rad)
        yaw_forward_y = math.sin(yaw_rad)

        print("\n================ COORDINATE DEBUG ================")
        print("Vehicle world location:")
        print("  x={:.3f}, y={:.3f}, z={:.3f}".format(loc.x, loc.y, loc.z))
        print("Vehicle rotation:")
        print("  pitch={:.3f}, yaw={:.3f}, roll={:.3f}".format(
            rot.pitch, rot.yaw, rot.roll
        ))

        print("\nVehicle local axes expressed in world frame:")
        print("  local +X / forward -> world ({:.4f}, {:.4f}, {:.4f})".format(
            forward.x, forward.y, forward.z
        ))
        print("  local +Y / right   -> world ({:.4f}, {:.4f}, {:.4f})".format(
            right.x, right.y, right.z
        ))
        print("  local +Z / up      -> world ({:.4f}, {:.4f}, {:.4f})".format(
            up.x, up.y, up.z
        ))

        print("\nYaw check:")
        print("  cos(yaw), sin(yaw) -> ({:.4f}, {:.4f})".format(
            yaw_forward_x, yaw_forward_y
        ))
        print("  get_forward_vector -> ({:.4f}, {:.4f})".format(
            forward.x, forward.y
        ))

        print("\nExpected CARLA convention:")
        print("  world x/y: map plane")
        print("  world z: up")
        print("  vehicle local +X: front")
        print("  vehicle local +Y: right")
        print("  vehicle local +Z: up")
        print("==================================================\n")

    def update_gyro_sign_calibration(self, vehicle, imu):
        """
        判断 gyro.z 和 CARLA yaw 变化是否同号。

        原理：
          ground truth yaw 变化 = 当前 yaw - 上一帧 yaw
          gyro yaw 变化 = gyro.z * dt

        如果二者大多数时候同号：
          gyro_z_sign = +1

        如果二者大多数时候反号：
          gyro_z_sign = -1
        """
        if imu is None:
            return self.gyro_z_sign

        now = time.time()
        yaw_rad = math.radians(vehicle.get_transform().rotation.yaw)

        if self.last_time is None:
            self.last_time = now
            self.last_yaw_rad = yaw_rad
            return self.gyro_z_sign

        dt = now - self.last_time
        if dt <= 0.0:
            return self.gyro_z_sign

        gt_delta_yaw = normalize_angle_rad(yaw_rad - self.last_yaw_rad)
        gyro_delta_yaw = imu.gyroscope.z * dt

        self.last_time = now
        self.last_yaw_rad = yaw_rad

        # 只在明显转向时采样，避免静止噪声影响
        if abs(gt_delta_yaw) > math.radians(0.2) and abs(gyro_delta_yaw) > 1e-4:
            product = gt_delta_yaw * gyro_delta_yaw
            self.samples.append(product)

        if not self.sign_locked and len(self.samples) >= 10:
            score = sum(1.0 if s > 0 else -1.0 for s in self.samples)
            self.gyro_z_sign = 1.0 if score >= 0 else -1.0
            self.sign_locked = True

            print("\n================ GYRO SIGN CALIBRATION ================")
            print("Collected samples:", len(self.samples))
            print("Sign score:", score)
            print("Selected gyro_z_sign:", self.gyro_z_sign)
            print("Meaning:")
            print("  yaw_est = yaw_est + gyro_z_sign * imu.gyroscope.z * dt")
            print("=======================================================\n")

        return self.gyro_z_sign


# ============================================================
# 7. 轨迹估计器 V3
# ============================================================

class TrajectoryEstimatorV3:
    """
    轨迹估计器。

    三条轨迹：

    1. Ground Truth:
       gt_x, gt_y

    2. Odom:
       odom_x, odom_y
       使用：
         forward_speed + imu.gyro.z

    3. Fusion:
       fused_x, fused_y
       使用：
         odom prediction + GNSS correction

    这版的重要修复：
      GNSS y 方向取反：
        y = ref_gt_y - dy

    为什么？
      你前一份数据表明：
        longitude -> CARLA x 基本正确
        latitude  -> CARLA y 方向需要反号
    """

    def __init__(self, coord_debugger):
        self.coord_debugger = coord_debugger

        self.initialized = False
        self.start_time = None
        self.last_time = None

        # odometry estimate
        self.odom_x = 0.0
        self.odom_y = 0.0
        self.odom_yaw = 0.0

        # fusion estimate
        self.fused_x = 0.0
        self.fused_y = 0.0
        self.fused_yaw = 0.0

        # GNSS reference
        self.ref_lat = None
        self.ref_lon = None
        self.ref_gt_x = None
        self.ref_gt_y = None

        # GNSS 修正权重
        #
        # alpha 越大，越相信 GNSS，轨迹会更贴 GNSS，但可能更抖。
        # alpha 越小，越相信 odom，轨迹更平滑，但可能慢慢漂。
        #
        # 0.03 ~ 0.08 都可以试。
        self.gnss_correction_alpha = 0.05

        self.records = []

    def initialize(self, vehicle, gnss):
        transform = vehicle.get_transform()
        location = transform.location
        rotation = transform.rotation

        yaw_rad = math.radians(rotation.yaw)

        now = time.time()
        self.start_time = now
        self.last_time = now

        self.odom_x = location.x
        self.odom_y = location.y
        self.odom_yaw = yaw_rad

        self.fused_x = location.x
        self.fused_y = location.y
        self.fused_yaw = yaw_rad

        if gnss is not None:
            self.ref_lat = gnss.latitude
            self.ref_lon = gnss.longitude

        self.ref_gt_x = location.x
        self.ref_gt_y = location.y

        self.initialized = True

    def gnss_to_local_xy(self, latitude, longitude):
        """
        把 GNSS 经纬度转换到 CARLA world x/y 附近。

        用第一个 GNSS 点作为参考点：
            ref_lat, ref_lon

        常规近似：
            dx = longitude 变化对应的东西向米数
            dy = latitude 变化对应的南北向米数

        你的数据中发现：
            dx 对应 CARLA x 是正确的；
            dy 对应 CARLA y 需要取反。

        所以：
            x = ref_gt_x + dx
            y = ref_gt_y - dy
        """
        if self.ref_lat is None or self.ref_lon is None:
            return None, None

        earth_radius = 6378137.0

        lat0 = math.radians(self.ref_lat)
        lon0 = math.radians(self.ref_lon)

        lat = math.radians(latitude)
        lon = math.radians(longitude)

        dx = (lon - lon0) * math.cos(lat0) * earth_radius
        dy = (lat - lat0) * earth_radius

        x = self.ref_gt_x + dx

        # 关键修复：y 方向取反
        y = self.ref_gt_y - dy

        return x, y

    def update(self, vehicle, sensor_manager):
        imu = sensor_manager.latest_imu
        gnss = sensor_manager.latest_gnss

        if not self.initialized:
            self.initialize(vehicle, gnss)
            return

        now = time.time()
        dt = now - self.last_time

        if dt <= 0.0:
            return

        # 防止窗口卡顿导致单步积分过大
        if dt > 0.2:
            dt = 0.2

        self.last_time = now

        transform = vehicle.get_transform()
        location = transform.location
        rotation = transform.rotation

        gt_x = location.x
        gt_y = location.y
        gt_z = location.z
        gt_yaw_deg = rotation.yaw
        gt_yaw_rad = math.radians(rotation.yaw)

        forward_speed_mps = get_forward_speed(vehicle)
        planar_speed_mps = get_planar_speed(vehicle)
        speed_3d_mps = get_3d_speed(vehicle)

        imu_ax = None
        imu_ay = None
        imu_az = None
        gyro_x = None
        gyro_y = None
        gyro_z = None
        compass = None

        gyro_z_sign = self.coord_debugger.gyro_z_sign

        if imu is not None:
            accel = imu.accelerometer
            gyro = imu.gyroscope

            imu_ax = accel.x
            imu_ay = accel.y
            imu_az = accel.z

            gyro_x = gyro.x
            gyro_y = gyro.y
            gyro_z = gyro.z
            compass = imu.compass

            gyro_z_sign = self.coord_debugger.update_gyro_sign_calibration(vehicle, imu)

            # ------------------------------------------------------------
            # 1. Odometry prediction
            #
            # 用 IMU gyro.z 积分 yaw。
            # 用车辆前向速度积分位置。
            # ------------------------------------------------------------
            self.odom_yaw = normalize_angle_rad(
                self.odom_yaw + gyro_z_sign * gyro_z * dt
            )

            self.odom_x += forward_speed_mps * math.cos(self.odom_yaw) * dt
            self.odom_y += forward_speed_mps * math.sin(self.odom_yaw) * dt

            # ------------------------------------------------------------
            # 2. Fusion prediction
            # ------------------------------------------------------------
            self.fused_yaw = normalize_angle_rad(
                self.fused_yaw + gyro_z_sign * gyro_z * dt
            )

            self.fused_x += forward_speed_mps * math.cos(self.fused_yaw) * dt
            self.fused_y += forward_speed_mps * math.sin(self.fused_yaw) * dt

        else:
            # 没有 IMU 时，不更新 yaw，只用已有 yaw + forward speed 预测
            self.odom_x += forward_speed_mps * math.cos(self.odom_yaw) * dt
            self.odom_y += forward_speed_mps * math.sin(self.odom_yaw) * dt

            self.fused_x += forward_speed_mps * math.cos(self.fused_yaw) * dt
            self.fused_y += forward_speed_mps * math.sin(self.fused_yaw) * dt

        # 如果启动时还没有 GNSS，则后面第一次拿到 GNSS 时初始化参考点
        if gnss is not None and self.ref_lat is None:
            self.ref_lat = gnss.latitude
            self.ref_lon = gnss.longitude
            self.ref_gt_x = gt_x
            self.ref_gt_y = gt_y

        gnss_x = None
        gnss_y = None
        gnss_lat = None
        gnss_lon = None
        gnss_alt = None

        if gnss is not None and self.ref_lat is not None:
            gnss_lat = gnss.latitude
            gnss_lon = gnss.longitude
            gnss_alt = gnss.altitude

            gnss_x, gnss_y = self.gnss_to_local_xy(gnss.latitude, gnss.longitude)

            # ------------------------------------------------------------
            # 3. GNSS correction
            #
            # 简单固定权重融合：
            #   fused = (1 - alpha) * prediction + alpha * gnss
            #
            # 这不是 EKF，只是为了教学理解。
            # ------------------------------------------------------------
            if gnss_x is not None and gnss_y is not None:
                a = self.gnss_correction_alpha
                self.fused_x = (1.0 - a) * self.fused_x + a * gnss_x
                self.fused_y = (1.0 - a) * self.fused_y + a * gnss_y

        elapsed = now - self.start_time

        odom_error = math.sqrt(
            (self.odom_x - gt_x) ** 2 +
            (self.odom_y - gt_y) ** 2
        )

        fused_error = math.sqrt(
            (self.fused_x - gt_x) ** 2 +
            (self.fused_y - gt_y) ** 2
        )

        gnss_error = None
        if gnss_x is not None and gnss_y is not None:
            gnss_error = math.sqrt(
                (gnss_x - gt_x) ** 2 +
                (gnss_y - gt_y) ** 2
            )

        self.records.append({
            "time": elapsed,
            "dt": dt,

            "gt_x": gt_x,
            "gt_y": gt_y,
            "gt_z": gt_z,
            "gt_yaw_deg": gt_yaw_deg,
            "gt_yaw_rad": gt_yaw_rad,

            "forward_speed_mps": forward_speed_mps,
            "planar_speed_mps": planar_speed_mps,
            "speed_3d_mps": speed_3d_mps,

            "odom_x": self.odom_x,
            "odom_y": self.odom_y,
            "odom_yaw_rad": self.odom_yaw,
            "odom_error_m": odom_error,

            "fused_x": self.fused_x,
            "fused_y": self.fused_y,
            "fused_yaw_rad": self.fused_yaw,
            "fused_error_m": fused_error,

            "gnss_x": gnss_x,
            "gnss_y": gnss_y,
            "gnss_lat": gnss_lat,
            "gnss_lon": gnss_lon,
            "gnss_alt": gnss_alt,
            "gnss_error_m": gnss_error,

            "imu_ax": imu_ax,
            "imu_ay": imu_ay,
            "imu_az": imu_az,

            "gyro_x": gyro_x,
            "gyro_y": gyro_y,
            "gyro_z": gyro_z,
            "gyro_z_sign": gyro_z_sign,

            "compass": compass
        })

    def save_results(self, output_root=None):
        if len(self.records) == 0:
            print("No trajectory records to save.")
            return None

        if output_root is None:
            output_root = os.getcwd()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(output_root, "trajectory_results_v3_{}".format(timestamp))
        os.makedirs(output_dir, exist_ok=True)

        csv_path = os.path.join(output_dir, "trajectory_data.csv")
        plot_path = os.path.join(output_dir, "trajectory_plot.png")
        error_plot_path = os.path.join(output_dir, "trajectory_error_plot.png")
        summary_path = os.path.join(output_dir, "summary.txt")

        fieldnames = [
            "time", "dt",

            "gt_x", "gt_y", "gt_z", "gt_yaw_deg", "gt_yaw_rad",

            "forward_speed_mps", "planar_speed_mps", "speed_3d_mps",

            "odom_x", "odom_y", "odom_yaw_rad", "odom_error_m",

            "fused_x", "fused_y", "fused_yaw_rad", "fused_error_m",

            "gnss_x", "gnss_y", "gnss_lat", "gnss_lon", "gnss_alt", "gnss_error_m",

            "imu_ax", "imu_ay", "imu_az",

            "gyro_x", "gyro_y", "gyro_z", "gyro_z_sign",

            "compass"
        ]

        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.records:
                writer.writerow(row)

        gt_x = [r["gt_x"] for r in self.records]
        gt_y = [r["gt_y"] for r in self.records]

        odom_x = [r["odom_x"] for r in self.records]
        odom_y = [r["odom_y"] for r in self.records]

        fused_x = [r["fused_x"] for r in self.records]
        fused_y = [r["fused_y"] for r in self.records]

        gnss_x = [r["gnss_x"] for r in self.records if r["gnss_x"] is not None]
        gnss_y = [r["gnss_y"] for r in self.records if r["gnss_y"] is not None]

        times = [r["time"] for r in self.records]
        odom_errors = [r["odom_error_m"] for r in self.records]
        fused_errors = [r["fused_error_m"] for r in self.records]

        gnss_error_times = [
            r["time"] for r in self.records
            if r["gnss_error_m"] is not None
        ]
        gnss_errors = [
            r["gnss_error_m"] for r in self.records
            if r["gnss_error_m"] is not None
        ]

        # ------------------------------------------------------------
        # 保存轨迹图
        # ------------------------------------------------------------
        plt.figure(figsize=(10, 8))
        plt.plot(gt_x, gt_y, label="CARLA Ground Truth", linewidth=2)
        plt.plot(odom_x, odom_y, label="Forward Speed + IMU Gyro Odometry", linewidth=2)
        plt.plot(fused_x, fused_y, label="Forward Speed + IMU Gyro + GNSS Fusion", linewidth=2)

        if len(gnss_x) > 0:
            plt.scatter(gnss_x, gnss_y, label="GNSS converted points, y flipped", s=8)

        plt.xlabel("x / meter")
        plt.ylabel("y / meter")
        plt.title("Trajectory Comparison V3")
        plt.axis("equal")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.savefig(plot_path, dpi=200)
        plt.close()

        # ------------------------------------------------------------
        # 保存误差图
        # ------------------------------------------------------------
        plt.figure(figsize=(10, 6))
        plt.plot(times, odom_errors, label="Odometry Error", linewidth=2)
        plt.plot(times, fused_errors, label="Fusion Error", linewidth=2)

        if len(gnss_errors) > 0:
            plt.scatter(gnss_error_times, gnss_errors, label="GNSS Error", s=8)

        plt.xlabel("time / second")
        plt.ylabel("position error / meter")
        plt.title("Position Error Compared with CARLA Ground Truth")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.savefig(error_plot_path, dpi=200)
        plt.close()

        # ------------------------------------------------------------
        # 计算统计信息
        # ------------------------------------------------------------
        final_gt_x = gt_x[-1]
        final_gt_y = gt_y[-1]

        final_odom_x = odom_x[-1]
        final_odom_y = odom_y[-1]

        final_fused_x = fused_x[-1]
        final_fused_y = fused_y[-1]

        final_odom_error = odom_errors[-1]
        final_fused_error = fused_errors[-1]

        mean_odom_error = sum(odom_errors) / len(odom_errors)
        mean_fused_error = sum(fused_errors) / len(fused_errors)

        max_odom_error = max(odom_errors)
        max_fused_error = max(fused_errors)

        if len(gnss_errors) > 0:
            mean_gnss_error = sum(gnss_errors) / len(gnss_errors)
            max_gnss_error = max(gnss_errors)
            final_gnss_error = gnss_errors[-1]
        else:
            mean_gnss_error = None
            max_gnss_error = None
            final_gnss_error = None

        duration = self.records[-1]["time"]
        final_gyro_sign = self.records[-1]["gyro_z_sign"]

        with open(summary_path, "w") as f:
            f.write("Trajectory comparison summary V3\n")
            f.write("================================\n\n")

            f.write("What this experiment compares:\n")
            f.write("  1. CARLA Ground Truth\n")
            f.write("  2. Forward Speed + IMU Gyro Odometry\n")
            f.write("  3. Forward Speed + IMU Gyro + GNSS Simple Fusion\n\n")

            f.write("Important fixes in V3:\n")
            f.write("  - GNSS y direction is flipped: y = ref_gt_y - dy\n")
            f.write("  - Speed uses vehicle forward projection, not 3D speed magnitude\n\n")

            f.write("Record count: {}\n".format(len(self.records)))
            f.write("Duration: {:.3f} seconds\n".format(duration))
            f.write("GNSS correction alpha: {:.3f}\n".format(self.gnss_correction_alpha))
            f.write("Final gyro_z_sign: {:.1f}\n\n".format(final_gyro_sign))

            f.write("Final CARLA Ground Truth:\n")
            f.write("  x: {:.3f}, y: {:.3f}\n\n".format(final_gt_x, final_gt_y))

            f.write("Final Odometry:\n")
            f.write("  x: {:.3f}, y: {:.3f}\n".format(final_odom_x, final_odom_y))
            f.write("  final error: {:.3f} m\n".format(final_odom_error))
            f.write("  mean error:  {:.3f} m\n".format(mean_odom_error))
            f.write("  max error:   {:.3f} m\n\n".format(max_odom_error))

            f.write("Final Fusion:\n")
            f.write("  x: {:.3f}, y: {:.3f}\n".format(final_fused_x, final_fused_y))
            f.write("  final error: {:.3f} m\n".format(final_fused_error))
            f.write("  mean error:  {:.3f} m\n".format(mean_fused_error))
            f.write("  max error:   {:.3f} m\n\n".format(max_fused_error))

            if mean_gnss_error is not None:
                f.write("GNSS converted points:\n")
                f.write("  final error: {:.3f} m\n".format(final_gnss_error))
                f.write("  mean error:  {:.3f} m\n".format(mean_gnss_error))
                f.write("  max error:   {:.3f} m\n\n".format(max_gnss_error))

            f.write("Notes:\n")
            f.write("  This is still a simplified educational fusion method.\n")
            f.write("  It is not an EKF or production-grade INS/GNSS system.\n")
            f.write("  Real systems need bias estimation, noise modeling, coordinate transforms,\n")
            f.write("  wheel odometry, map matching, and possibly EKF/UKF/factor graph optimization.\n")

        print("\nSaved trajectory results:")
        print("  Folder:     {}".format(output_dir))
        print("  Trajectory: {}".format(plot_path))
        print("  Error plot: {}".format(error_plot_path))
        print("  CSV:        {}".format(csv_path))
        print("  Summary:    {}".format(summary_path))

        return output_dir


# ============================================================
# 8. 车辆生成
# ============================================================

def spawn_vehicle(world):
    blueprint_library = world.get_blueprint_library()

    vehicle_bp = blueprint_library.filter("vehicle.tesla.model3")[0]
    vehicle_bp.set_attribute("role_name", "hero")

    vehicle = world.try_spawn_actor(vehicle_bp, START_TRANSFORM)

    if vehicle is None:
        raise RuntimeError(
            "车辆生成失败。可能是该位置被其他 actor 占用，"
            "或者车辆与地面/障碍物发生碰撞。可以尝试把 START_TRANSFORM 的 z 改成 1.0。"
        )

    vehicle.set_autopilot(False)

    # 保证车辆位置就是你指定的位置
    vehicle.set_transform(START_TRANSFORM)

    return vehicle


# ============================================================
# 9. 键盘控制
# ============================================================

def get_keyboard_control(keys, current_steer):
    """
    pygame 输入版本。

    ↑ / W       前进
    ↓ / S       倒车
    ← / A       左转
    → / D       右转
    SPACE       刹车
    ESC         保存并退出

    注意：
    pygame 只会接收 pygame 窗口焦点下的按键。
    运行后请点击 pygame 窗口。
    """
    control = carla.VehicleControl()

    throttle = 0.0
    brake = 0.0
    reverse = False

    if keys[pygame.K_UP] or keys[pygame.K_w]:
        throttle = 0.55
        reverse = False

    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        throttle = 0.45
        reverse = True

    if keys[pygame.K_SPACE]:
        throttle = 0.0
        brake = 1.0
        reverse = False

    steer_increment = 0.04

    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        current_steer -= steer_increment
    elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        current_steer += steer_increment
    else:
        # 松开方向键后方向盘慢慢回正
        if current_steer > 0:
            current_steer -= steer_increment
        elif current_steer < 0:
            current_steer += steer_increment

    current_steer = max(-0.75, min(0.75, current_steer))

    if abs(current_steer) < 0.03:
        current_steer = 0.0

    control.throttle = throttle
    control.brake = brake
    control.steer = current_steer
    control.reverse = reverse
    control.hand_brake = False
    control.manual_gear_shift = False

    return control, current_steer


# ============================================================
# 10. pygame HUD 显示
# ============================================================

def draw_text_lines(display, font, lines, x=20, y=20, line_height=24):
    for i, line in enumerate(lines):
        text_surface = font.render(line, True, (255, 255, 255))
        display.blit(text_surface, (x, y + i * line_height))


def draw_hud(display, font, control, vehicle, sensor_manager, estimator, coord_debugger):
    lines = []

    lines.append("CARLA Trajectory Compare V3 | ESC save & quit")
    lines.append("UP/W throttle | DOWN/S reverse | LEFT/A RIGHT/D steer | SPACE brake")
    lines.append(
        "Control | throttle: {:.2f}  brake: {:.2f}  steer: {:.2f}  reverse: {}".format(
            control.throttle,
            control.brake,
            control.steer,
            control.reverse
        )
    )

    transform = vehicle.get_transform()
    location = transform.location
    rotation = transform.rotation

    forward_speed = get_forward_speed(vehicle)
    planar_speed = get_planar_speed(vehicle)
    speed_3d = get_3d_speed(vehicle)

    lines.append(
        "GT Location | x: {:.2f}  y: {:.2f}  z: {:.2f}".format(
            location.x,
            location.y,
            location.z
        )
    )

    lines.append(
        "GT Rotation | pitch: {:.2f}  yaw: {:.2f}  roll: {:.2f}".format(
            rotation.pitch,
            rotation.yaw,
            rotation.roll
        )
    )

    lines.append(
        "Speed | forward: {:.2f} m/s  planar: {:.2f}  3d: {:.2f}".format(
            forward_speed,
            planar_speed,
            speed_3d
        )
    )

    imu = sensor_manager.latest_imu
    if imu is not None:
        accel = imu.accelerometer
        gyro = imu.gyroscope
        compass = imu.compass

        lines.append(
            "IMU Accel | x: {:.3f}  y: {:.3f}  z: {:.3f}".format(
                accel.x,
                accel.y,
                accel.z
            )
        )

        lines.append(
            "IMU Gyro  | x: {:.3f}  y: {:.3f}  z: {:.3f}".format(
                gyro.x,
                gyro.y,
                gyro.z
            )
        )

        lines.append(
            "IMU Compass | {:.3f} rad  {:.2f} deg".format(
                compass,
                math.degrees(compass)
            )
        )
    else:
        lines.append("IMU | No data yet")

    gnss = sensor_manager.latest_gnss
    if gnss is not None:
        lines.append(
            "GNSS | lat: {:.8f}  lon: {:.8f}  alt: {:.2f}".format(
                gnss.latitude,
                gnss.longitude,
                gnss.altitude
            )
        )
    else:
        lines.append("GNSS | No data yet")

    lines.append(
        "Gyro z sign | {:.1f}  locked: {}".format(
            coord_debugger.gyro_z_sign,
            coord_debugger.sign_locked
        )
    )

    if estimator is not None:
        lines.append("Trajectory records | {}".format(len(estimator.records)))

        if estimator.initialized:
            lines.append(
                "Odom Est | x: {:.2f}  y: {:.2f}".format(
                    estimator.odom_x,
                    estimator.odom_y
                )
            )

            lines.append(
                "Fusion Est | x: {:.2f}  y: {:.2f}".format(
                    estimator.fused_x,
                    estimator.fused_y
                )
            )

            if len(estimator.records) > 0:
                last = estimator.records[-1]
                lines.append(
                    "Error | odom: {:.2f} m  fusion: {:.2f} m".format(
                        last["odom_error_m"],
                        last["fused_error_m"]
                    )
                )

                if last["gnss_error_m"] is not None:
                    lines.append(
                        "GNSS converted error | {:.2f} m".format(
                            last["gnss_error_m"]
                        )
                    )

    draw_text_lines(display, font, lines, x=20, y=20, line_height=24)


# ============================================================
# 11. 主程序
# ============================================================

def main():
    pygame.init()
    pygame.font.init()

    display = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.HWSURFACE | pygame.DOUBLEBUF
    )
    pygame.display.set_caption("CARLA Trajectory Compare V3")

    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    client = carla.Client(HOST, PORT)
    client.set_timeout(TIMEOUT)

    try:
        world = client.get_world()
        print("成功连接到 CARLA server")
        print("当前地图:", world.get_map().name)
    except RuntimeError as e:
        print("连接 CARLA 失败")
        print("请确认 CarlaUE4.exe 已经启动，并且地图已经加载完成")
        print("当前连接地址: {}:{}".format(HOST, PORT))
        print("原始错误:", e)
        pygame.quit()
        raise

    vehicle = None
    camera_manager = None
    sensor_manager = None
    coord_debugger = None
    estimator = None

    current_steer = 0.0
    last_print_time = time.time()

    try:
        vehicle = spawn_vehicle(world)
        camera_manager = DriverCameraManager(world, vehicle, WINDOW_WIDTH, WINDOW_HEIGHT)
        sensor_manager = SensorManager(world, vehicle)

        coord_debugger = CoordinateDebugger()
        estimator = TrajectoryEstimatorV3(coord_debugger)

        coord_debugger.print_axis_info(vehicle)

        print("\nVehicle spawned at:")
        print(START_TRANSFORM)

        print("\n当前视角:")
        print("  pygame 窗口显示 vehicle 上挂载的 RGB 第一视角 camera")
        print("  UE 主窗口不再强制跟随车辆，可用于外部观察")

        print("\nControls:")
        print("  UP / W       : 前进")
        print("  DOWN / S     : 倒车")
        print("  LEFT / A     : 左转")
        print("  RIGHT / D    : 右转")
        print("  SPACE        : 刹车")
        print("  ESC          : 保存轨迹图、误差图和 CSV，然后退出")

        print("\nV3 轨迹:")
        print("  1. CARLA Ground Truth")
        print("  2. Forward Speed + IMU Gyro Odometry")
        print("  3. Forward Speed + IMU Gyro + GNSS Fusion")

        print("\nV3 修复:")
        print("  - GNSS y 方向取反：y = ref_gt_y - dy")
        print("  - 使用车辆前向速度，不使用 3D 速度")
        print("  - 保存误差曲线 trajectory_error_plot.png")

        print("\n注意:")
        print("  运行后请点击 pygame 图像窗口，让 pygame 获得键盘焦点。")
        print("  开车时多做几次转弯，脚本会自动判断 gyro.z 符号。")
        print("  按 ESC 后会保存结果文件夹。")

        running = True

        while running:
            clock.tick(30)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            keys = pygame.key.get_pressed()

            control, current_steer = get_keyboard_control(keys, current_steer)
            vehicle.apply_control(control)

            estimator.update(vehicle, sensor_manager)

            camera_manager.render(display)
            draw_hud(display, font, control, vehicle, sensor_manager, estimator, coord_debugger)
            pygame.display.flip()

            now = time.time()
            if now - last_print_time >= PRINT_INTERVAL:
                print(
                    "\nControl: throttle={:.2f}, brake={:.2f}, steer={:.2f}, reverse={}".format(
                        control.throttle,
                        control.brake,
                        control.steer,
                        control.reverse
                    )
                )

                sensor_manager.print_latest_data()

                if estimator is not None:
                    print("Trajectory records:", len(estimator.records))

                    if estimator.initialized:
                        print(
                            "Gyro z sign: {} locked: {}".format(
                                coord_debugger.gyro_z_sign,
                                coord_debugger.sign_locked
                            )
                        )
                        print(
                            "Odom est:   x={:.3f}, y={:.3f}".format(
                                estimator.odom_x,
                                estimator.odom_y
                            )
                        )
                        print(
                            "Fusion est: x={:.3f}, y={:.3f}".format(
                                estimator.fused_x,
                                estimator.fused_y
                            )
                        )

                        if len(estimator.records) > 0:
                            last = estimator.records[-1]
                            print(
                                "Errors: odom={:.3f} m, fusion={:.3f} m".format(
                                    last["odom_error_m"],
                                    last["fused_error_m"]
                                )
                            )

                            if last["gnss_error_m"] is not None:
                                print(
                                    "GNSS converted error={:.3f} m".format(
                                        last["gnss_error_m"]
                                    )
                                )

                last_print_time = now

    finally:
        print("\nSaving trajectory results...")

        if estimator is not None:
            try:
                estimator.save_results(output_root=os.getcwd())
            except Exception as e:
                print("保存轨迹结果失败:", e)

        print("\nCleaning up actors...")

        if camera_manager is not None:
            camera_manager.destroy()

        if sensor_manager is not None:
            sensor_manager.destroy()

        if vehicle is not None:
            vehicle.destroy()

        pygame.quit()
        print("Done.")


if __name__ == "__main__":
    main()