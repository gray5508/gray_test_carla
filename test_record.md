### 经过测试脚本生成的一个合适的固定起点
START_TRANSFORM = carla.Transform(
    carla.Location(x=55.754353, y=130.663452, z=0.500000),
    carla.Rotation(pitch=0.000000, yaw=180.320450, roll=0.000000)
)

### sensor 理解
Yaw   = 左右转头，看方向
Pitch = 上下点头，看坡度
Roll  = 左右歪头，看侧倾

### IMU Gyroscope：陀螺仪角速度
gyro.x：绕车辆前后方向旋转的速度，对应 roll 变化
gyro.y：绕车辆左右方向旋转的速度，对应 pitch 变化
gyro.z：绕车辆上下方向旋转的速度，对应 yaw 变化