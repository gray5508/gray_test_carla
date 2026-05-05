"""
05_sensor_sync_recording.py

目标：
1. 认识 CARLA synchronous mode；
2. 让 world tick、camera、IMU、GNSS 尽量按同一个 frame 对齐；
3. 保存一个 CSV，作为后续传感器融合/标定算法的输入样例。

这个 lesson 不用 pygame 手动驾驶，而是脚本自动给车辆一段简单控制：
  直行 -> 左转 -> 直行

运行：
  C:\\Users\\cicii\\miniconda3\\envs\\carla_test\\python.exe 05_sensor_sync_recording.py

输出：
  carla_ar_turn_arrow_tutorial\\outputs\\sensor_sync_recording.csv

为什么重要：
  你后续做视觉检测 + IMU/GNSS/车辆位姿融合时，必须知道每条数据属于哪一帧。
  异步回调适合入门显示；严肃实验建议用 synchronous mode + frame/timestamp 对齐。
"""

import csv
import os
import time
from queue import Empty
from queue import Queue

from common import CAMERA_FOV
from common import DRIVER_CAMERA_TRANSFORM
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import carla
from common import connect_client
from common import destroy_actors
from common import get_forward_speed
from common import spawn_ego_vehicle


FIXED_DELTA_SECONDS = 0.05  # 20 Hz
TOTAL_FRAMES = 320


def sensor_callback(data, queue, name):
    """传感器回调只做一件事：把数据放进线程安全队列。"""
    queue.put((name, data))


def wait_sensor_data(queue, expected_frame, timeout=2.0):
    """
    等待某个传感器给出 expected_frame 对应的数据。

    如果队列里先来了旧帧，就丢掉继续等。
    如果来了比 expected_frame 更新的帧，也返回它并让主循环记录 frame mismatch。
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        remaining = max(0.01, end_time - time.time())
        try:
            name, data = queue.get(True, remaining)
        except Empty:
            return None

        if data.frame >= expected_frame:
            return data

    return None


def make_output_path():
    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    return os.path.join(output_dir, "sensor_sync_recording.csv")


def main():
    client, world = connect_client()

    original_settings = world.get_settings()
    actors = []

    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = FIXED_DELTA_SECONDS
        world.apply_settings(settings)

        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        blueprints = world.get_blueprint_library()

        camera_bp = blueprints.find("sensor.camera.rgb")
        camera_bp.set_attribute("image_size_x", str(WINDOW_WIDTH))
        camera_bp.set_attribute("image_size_y", str(WINDOW_HEIGHT))
        camera_bp.set_attribute("fov", str(CAMERA_FOV))
        camera_bp.set_attribute("sensor_tick", str(FIXED_DELTA_SECONDS))

        imu_bp = blueprints.find("sensor.other.imu")
        imu_bp.set_attribute("sensor_tick", str(FIXED_DELTA_SECONDS))

        gnss_bp = blueprints.find("sensor.other.gnss")
        gnss_bp.set_attribute("sensor_tick", str(FIXED_DELTA_SECONDS))

        camera = world.spawn_actor(
            camera_bp,
            DRIVER_CAMERA_TRANSFORM,
            attach_to=vehicle,
            attachment_type=carla.AttachmentType.Rigid,
        )
        imu = world.spawn_actor(
            imu_bp,
            carla.Transform(carla.Location(x=0.0, y=0.0, z=0.0)),
            attach_to=vehicle,
        )
        gnss = world.spawn_actor(
            gnss_bp,
            carla.Transform(carla.Location(x=0.0, y=0.0, z=0.0)),
            attach_to=vehicle,
        )
        actors.extend([camera, imu, gnss])

        camera_queue = Queue()
        imu_queue = Queue()
        gnss_queue = Queue()

        camera.listen(lambda data: sensor_callback(data, camera_queue, "camera"))
        imu.listen(lambda data: sensor_callback(data, imu_queue, "imu"))
        gnss.listen(lambda data: sensor_callback(data, gnss_queue, "gnss"))

        output_path = make_output_path()

        fieldnames = [
            "world_frame",
            "sim_time",
            "camera_frame",
            "imu_frame",
            "gnss_frame",
            "gt_x",
            "gt_y",
            "gt_z",
            "yaw_deg",
            "forward_speed_mps",
            "imu_accel_x",
            "imu_accel_y",
            "imu_accel_z",
            "imu_gyro_x",
            "imu_gyro_y",
            "imu_gyro_z",
            "imu_compass",
            "gnss_latitude",
            "gnss_longitude",
            "gnss_altitude",
            "frame_match",
        ]

        print("Recording synchronized sensor data...")
        print("Output:", output_path)

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for i in range(TOTAL_FRAMES):
                # 一个简单自动控制序列：
                # 前 100 帧直行，中间 120 帧左转，最后直行并减速。
                if i < 100:
                    control = carla.VehicleControl(throttle=0.38, steer=0.0)
                elif i < 220:
                    control = carla.VehicleControl(throttle=0.34, steer=-0.42)
                else:
                    control = carla.VehicleControl(throttle=0.22, steer=0.0)

                vehicle.apply_control(control)

                world_frame = world.tick()
                snapshot = world.get_snapshot()
                sim_time = snapshot.timestamp.elapsed_seconds

                image_data = wait_sensor_data(camera_queue, world_frame)
                imu_data = wait_sensor_data(imu_queue, world_frame)
                gnss_data = wait_sensor_data(gnss_queue, world_frame)

                transform = vehicle.get_transform()
                location = transform.location
                rotation = transform.rotation

                frame_match = (
                    image_data is not None and image_data.frame == world_frame and
                    imu_data is not None and imu_data.frame == world_frame and
                    gnss_data is not None and gnss_data.frame == world_frame
                )

                row = {
                    "world_frame": world_frame,
                    "sim_time": "{:.6f}".format(sim_time),
                    "camera_frame": image_data.frame if image_data is not None else "",
                    "imu_frame": imu_data.frame if imu_data is not None else "",
                    "gnss_frame": gnss_data.frame if gnss_data is not None else "",
                    "gt_x": "{:.6f}".format(location.x),
                    "gt_y": "{:.6f}".format(location.y),
                    "gt_z": "{:.6f}".format(location.z),
                    "yaw_deg": "{:.6f}".format(rotation.yaw),
                    "forward_speed_mps": "{:.6f}".format(get_forward_speed(vehicle)),
                    "frame_match": int(frame_match),
                }

                if imu_data is not None:
                    row.update({
                        "imu_accel_x": "{:.9f}".format(imu_data.accelerometer.x),
                        "imu_accel_y": "{:.9f}".format(imu_data.accelerometer.y),
                        "imu_accel_z": "{:.9f}".format(imu_data.accelerometer.z),
                        "imu_gyro_x": "{:.9f}".format(imu_data.gyroscope.x),
                        "imu_gyro_y": "{:.9f}".format(imu_data.gyroscope.y),
                        "imu_gyro_z": "{:.9f}".format(imu_data.gyroscope.z),
                        "imu_compass": "{:.9f}".format(imu_data.compass),
                    })

                if gnss_data is not None:
                    row.update({
                        "gnss_latitude": "{:.9f}".format(gnss_data.latitude),
                        "gnss_longitude": "{:.9f}".format(gnss_data.longitude),
                        "gnss_altitude": "{:.6f}".format(gnss_data.altitude),
                    })

                writer.writerow(row)

                if i % 40 == 0:
                    print(
                        "frame {:4d} | world {} | match {} | x {:.2f} y {:.2f}".format(
                            i,
                            world_frame,
                            frame_match,
                            location.x,
                            location.y,
                        )
                    )

        print("Done.")

    finally:
        destroy_actors(actors)
        world.apply_settings(original_settings)
        print("Cleaned up and restored original world settings.")


if __name__ == "__main__":
    main()
