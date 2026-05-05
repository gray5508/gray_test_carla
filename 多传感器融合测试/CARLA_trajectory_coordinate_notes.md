# CARLA 车辆轨迹估计与传感器坐标系说明文档

## 1. 这个实验在做什么

这个实验的目标是：在 CARLA 中手动驾驶车辆，同时记录车辆的传感器数据和真实位姿，然后绘制并比较不同来源得到的车辆轨迹。

目前主要比较三条轨迹：

```text
1. CARLA Ground Truth
   CARLA 直接给出的真实车辆位置。

2. Speed + IMU Gyro Odometry
   用车辆前向速度 + IMU 陀螺仪 gyro.z 积分出来的估计轨迹。

3. Speed + IMU Gyro + GNSS Fusion
   在第 2 条轨迹基础上，加入 GNSS 位置修正后的融合轨迹。
```

CSV 数据中通常会包含这些关键列：

```text
gt_x / gt_y
odom_x / odom_y
fused_x / fused_y
gnss_x / gnss_y
gyro_z
gyro_z_sign
forward_speed_mps
planar_speed_mps
speed_3d_mps
```

这些数据可以用来分析：

```text
1. 真实轨迹是什么样；
2. 纯里程计轨迹是否漂移；
3. GNSS 转换后的方向是否正确；
4. 融合轨迹是否比单独 odometry 更接近真实轨迹。
```

---

## 2. CARLA 世界坐标系

CARLA 世界坐标可以理解为：

```text
world x：地图平面中的一个水平轴
world y：地图平面中的另一个水平轴
world z：竖直向上
```

车辆的位置通过下面代码获得：

```python
transform = vehicle.get_transform()
location = transform.location
```

返回：

```python
location.x
location.y
location.z
```

单位通常是米。

例如固定起点：

```python
START_TRANSFORM = carla.Transform(
    carla.Location(x=55.754353, y=130.663452, z=0.500000),
    carla.Rotation(pitch=0.000000, yaw=180.320450, roll=0.000000)
)
```

表示车辆出生在 CARLA 世界坐标：

```text
x = 55.754353 m
y = 130.663452 m
z = 0.500000 m
```

注意：这里的 `x/y/z` 是地图坐标，不是车辆自身的前后左右。

---

## 3. 车辆局部坐标系

车辆自身也有一个局部坐标系。通常可以这样理解：

```text
车辆 local +X：车头方向
车辆 local +Y：车辆右侧
车辆 local +Z：车辆上方
```

所以如果把摄像头挂到车辆上：

```python
carla.Location(x=1.15, y=-0.35, z=1.35)
```

含义是：

```text
x = 1.15   摄像头向车头方向移动 1.15 米
y = -0.35  摄像头向车辆左侧移动 0.35 米
z = 1.35   摄像头向上移动 1.35 米
```

这就是我们用来模拟司机第一视角的原因：

```python
camera_transform = carla.Transform(
    carla.Location(x=1.15, y=-0.35, z=1.35),
    carla.Rotation(pitch=-2.0, yaw=0.0, roll=0.0)
)
```

解释：

```text
x=1.15    靠近前挡风玻璃
y=-0.35   偏左，模拟左舵驾驶位
z=1.35    接近眼睛高度
pitch=-2  摄像头稍微向下看路面
```

如果画面被车体挡住，可以尝试：

```python
carla.Location(x=1.45, y=-0.30, z=1.35)
```

或者更像车头第一视角：

```python
carla.Location(x=2.20, y=0.0, z=1.25)
```

---

## 4. yaw / pitch / roll 的含义

车辆姿态通过：

```python
rotation = vehicle.get_transform().rotation
```

得到：

```text
pitch
yaw
roll
```

含义如下：

```text
yaw   ：车辆绕 z 轴旋转，表示车头在水平面上的朝向
pitch ：车辆绕 y 轴旋转，表示车头抬起或低下
roll  ：车辆绕 x 轴旋转，表示车身左右倾斜
```

轨迹估计里最重要的是 `yaw`，因为它决定车辆往哪个方向走。

轨迹积分时常用：

```python
x = x + speed * math.cos(yaw) * dt
y = y + speed * math.sin(yaw) * dt
```

这个公式是否正确，关键取决于：

```text
cos(yaw), sin(yaw)
```

是否和 CARLA 的车辆 forward vector 一致。

之前我们通过调试输出确认过：

```text
local +X / forward -> world (-1.0000, -0.0056, 0.0000)
cos(yaw), sin(yaw) -> (-1.0000, -0.0056)
```

这说明在当前环境里：

```text
车辆 forward vector 的 x/y
和
cos(yaw), sin(yaw)
是对齐的。
```

因此下面的轨迹积分方向是合理的：

```python
x += speed * math.cos(yaw) * dt
y += speed * math.sin(yaw) * dt
```

---

## 5. Ground Truth 轨迹

Ground Truth 是 CARLA 直接给出的车辆真实位置：

```python
transform = vehicle.get_transform()
location = transform.location

gt_x = location.x
gt_y = location.y
```

绘图中的：

```text
CARLA Ground Truth
```

就是：

```text
gt_x, gt_y
```

它不是传感器估计值，而是仿真器内部真实值，所以我们把它当作标准答案。

---

## 6. 为什么纯 IMU 加速度积分容易漂移

最开始可以尝试用 IMU 加速度积分：

```python
speed = speed + imu.accelerometer.x * dt
x = x + speed * math.cos(yaw) * dt
y = y + speed * math.sin(yaw) * dt
```

理论上，惯性导航确实会用加速度积分速度，再积分位置。

但真实使用时必须处理很多问题：

```text
重力补偿
坐标系转换
IMU bias 估计
噪声滤波
异常值处理
姿态解算
```

否则加速度只要有一点误差，积分两次后位置就会快速漂移。

在前面的实验数据里，IMU 加速度出现过很大的尖峰，例如几百甚至上千 `m/s²`。这种值如果直接积分，轨迹会很快飞掉。

所以后续版本不再直接使用：

```text
accel.x -> speed -> position
```

而是改用：

```text
车辆前向速度 + IMU gyro.z
```

---

## 7. 为什么使用车辆前向速度

新版中使用车辆前向速度：

```python
def get_forward_speed(vehicle):
    velocity = vehicle.get_velocity()
    transform = vehicle.get_transform()
    forward = transform.get_forward_vector()

    speed = (
        velocity.x * forward.x +
        velocity.y * forward.y +
        velocity.z * forward.z
    )

    return speed
```

这个计算的含义是：

```text
把车辆的世界速度向量投影到车头方向上。
```

它比 3D 总速度更适合轨迹积分。

不要直接用：

```python
speed = math.sqrt(vx ** 2 + vy ** 2 + vz ** 2)
```

因为它会把 z 方向速度也算进去。

车辆刚生成时，可能会从 `z=0.5` 落到地面，这时即使车没有真正向前开，`z` 方向也可能有速度。如果使用 3D speed，轨迹会被错误推进。

推荐：

```text
用于轨迹积分：forward_speed
用于显示参考：planar_speed / speed_3d
```

---

## 8. IMU gyro.z 的使用方式

IMU 陀螺仪数据：

```python
imu.gyroscope
```

包含：

```text
gyro.x
gyro.y
gyro.z
```

其中 `gyro.z` 通常对应车辆绕竖直轴的角速度，也就是 yaw rate。

我们用它更新估计 yaw：

```python
yaw = yaw + gyro_z_sign * gyro.z * dt
```

这里 `gyro_z_sign` 很重要。

不同仿真器、坐标系或传感器定义中，`gyro.z` 的正方向可能和 CARLA 的 `yaw` 增大方向一致，也可能相反。

所以我们加入了自动判断。

---

## 9. gyro_z_sign 的判断方式

自动判断逻辑如下：

```text
1. 读取 CARLA ground truth yaw
2. 计算当前 yaw 和上一帧 yaw 的差值
3. 读取 IMU gyro.z
4. 计算 gyro.z * dt
5. 看两者符号是否一致
```

如果大多数时候：

```text
ground truth yaw delta
和
gyro.z * dt
同号
```

则：

```python
gyro_z_sign = +1
```

如果大多数时候反号，则：

```python
gyro_z_sign = -1
```

在当前实验环境里，我们看到：

```text
Gyro z sign: 1.0 locked: True
```

说明当前环境中：

```text
imu.gyroscope.z 的方向
和
CARLA yaw 的变化方向
基本一致。
```

因此使用：

```python
yaw = yaw + gyro.z * dt
```

是合理的。

---

## 10. Odometry 轨迹的估计方式

Odometry 使用两个量：

```text
forward_speed
gyro.z
```

更新公式：

```python
odom_yaw = odom_yaw + gyro_z_sign * gyro.z * dt

odom_x = odom_x + forward_speed * math.cos(odom_yaw) * dt
odom_y = odom_y + forward_speed * math.sin(odom_yaw) * dt
```

它本质上模拟：

```text
车速计 + 陀螺仪
```

这种方法短时间通常效果不错，但会逐渐漂移。

漂移原因：

```text
gyro.z 有微小误差
yaw 是积分出来的
yaw 误差会影响 x/y 积分方向
开得越久，误差越明显
```

例如 yaw 只差 3 度，车辆开几十米后，横向误差就可能达到几米。

---

## 11. GNSS 为什么需要转换

GNSS 传感器给的是：

```text
latitude
longitude
altitude
```

也就是经纬度。

但轨迹图用的是：

```text
CARLA world x
CARLA world y
```

所以要把经纬度转换成局部米制坐标。

基本近似：

```python
dx = (lon - lon0) * math.cos(lat0) * earth_radius
dy = (lat - lat0) * earth_radius
```

其中：

```text
lon0, lat0：起点 GNSS 经纬度
dx：经度变化对应的水平距离
dy：纬度变化对应的水平距离
```

然后平移到 CARLA 起点附近。

---

## 12. GNSS y 方向为什么需要取反

最开始我们写的是：

```python
x = ref_gt_x + dx
y = ref_gt_y + dy
```

但根据实验数据发现：

```text
GNSS x 和 ground truth x 基本同向
GNSS y 和 ground truth y 呈镜像关系
```

也就是：

```text
longitude -> CARLA x 基本正确
latitude  -> CARLA y 方向需要反号
```

所以 V3 中改成：

```python
x = ref_gt_x + dx
y = ref_gt_y - dy
```

这是本项目里非常关键的修复。

---

## 13. 为什么会出现 GNSS y 反号

真实地理坐标里：

```text
latitude 增大通常表示向北
longitude 增大通常表示向东
```

但 CARLA 的 world x/y 不一定严格对应：

```text
world x = east
world y = north
```

它可能是：

```text
world x = east
world y = south
```

或者经过旋转、镜像、偏移。

在当前 Town10HD_Opt 实验里，数据表现为：

```text
longitude -> CARLA x 正方向
latitude  -> CARLA y 反方向
```

所以采用：

```python
x = ref_gt_x + dx
y = ref_gt_y - dy
```

注意：这个结论和地图有关。换地图后不一定仍然成立。

---

## 14. Fusion 轨迹的计算方式

Fusion 轨迹的逻辑是：

```text
先用 odometry 预测
再用 GNSS 轻微修正
```

代码形式：

```python
fused_x = (1.0 - alpha) * fused_x + alpha * gnss_x
fused_y = (1.0 - alpha) * fused_y + alpha * gnss_y
```

其中：

```python
alpha = 0.05
```

表示：

```text
95% 相信 odometry 预测
5% 相信 GNSS 修正
```

这不是严格 EKF，只是教学版简单融合。

如果 GNSS 坐标方向是错的，fusion 会被错误的 GNSS 拉偏。

这也是之前出现：

```text
绿色 fusion 有时不如橙色 odometry
```

的原因之一。

---

## 15. alpha 参数怎么调

`alpha` 是 GNSS 修正权重。

```python
self.gnss_correction_alpha = 0.05
```

如果 alpha 大：

```text
更相信 GNSS
修正更快
但 GNSS 有噪声时轨迹会更抖
```

如果 alpha 小：

```text
更相信 odometry
轨迹更平滑
但长期漂移可能更明显
```

建议测试：

```text
0.03
0.05
0.08
```

然后比较：

```text
trajectory_plot.png
trajectory_error_plot.png
summary.txt
```

重点看：

```text
mean error
max error
final error
```

---

## 16. 轨迹图方向偏差的排查方式

如果几条线趋势类似，但方向不同，可以按下面方式判断。

### 情况 A：左右镜像

可能是 x 方向反了。

检查：

```python
x = ref_gt_x + dx
```

是否应该改成：

```python
x = ref_gt_x - dx
```

### 情况 B：上下镜像

可能是 y 方向反了。

检查：

```python
y = ref_gt_y + dy
```

是否应该改成：

```python
y = ref_gt_y - dy
```

当前项目遇到的就是这个问题。

### 情况 C：轨迹整体旋转 90 度

可能是 x/y 轴交换了。

可能需要：

```python
x = ref_gt_x + dy
y = ref_gt_y + dx
```

或者带符号：

```python
x = ref_gt_x + dy
y = ref_gt_y - dx
```

### 情况 D：形状像，但越开越偏

通常是 odometry 漂移。

可能原因：

```text
gyro.z 积分误差
速度误差
dt 不稳定
```

### 情况 E：转弯处偏差最大

通常和 yaw 有关。

可能原因：

```text
gyro.z 符号问题
gyro 积分误差
速度方向和 yaw 更新不同步
传感器异步导致时间误差
```

---

## 17. 如何系统判断 GNSS 到 CARLA 的映射

换地图后，不要默认 V3 的：

```python
x = ref_gt_x + dx
y = ref_gt_y - dy
```

一定正确。

建议用一小段数据判断。

比较：

```text
gt_dx = gt_x - gt_x0
gt_dy = gt_y - gt_y0
```

和：

```text
gnss_dx = dx
gnss_dy = dy
```

如果：

```text
gt_dx ≈ +gnss_dx
gt_dy ≈ -gnss_dy
```

使用：

```python
x = ref_x + dx
y = ref_y - dy
```

如果：

```text
gt_dx ≈ +gnss_dx
gt_dy ≈ +gnss_dy
```

使用：

```python
x = ref_x + dx
y = ref_y + dy
```

如果：

```text
gt_dx ≈ +gnss_dy
gt_dy ≈ +gnss_dx
```

说明 x/y 可能交换了。

总结：GNSS 转换最好通过短距离 ground truth 标定，不要靠猜。

---

## 18. dt 的注意事项

轨迹积分中 `dt` 非常重要。

每帧计算：

```python
dt = now - last_time
```

然后：

```python
x += speed * math.cos(yaw) * dt
y += speed * math.sin(yaw) * dt
```

如果电脑卡顿，某一帧 `dt` 突然很大，会导致一次积分跳很远。

所以代码里有保护：

```python
if dt > 0.2:
    dt = 0.2
```

这不是最严格的做法，但能避免 pygame 卡顿时轨迹爆炸。

更严谨的方式是使用 CARLA synchronous mode 和 fixed_delta_seconds。

---

## 19. 异步传感器的注意事项

CARLA 传感器通过回调更新：

```python
sensor.listen(callback)
```

这意味着主循环每帧拿到的是：

```text
最近一次 IMU
最近一次 GNSS
```

它们不一定和当前：

```python
vehicle.get_transform()
```

完全同一时刻。

所以在急转弯、急加速时，会有轻微时间不同步误差。

入门阶段可以接受。后续严谨实验可以研究：

```text
synchronous mode
fixed_delta_seconds
sensor timestamp alignment
```

---

## 20. pygame 视角和 UE spectator 的区别

我们最后采用 pygame 版本，因为：

```text
pygame 显示的是 carla sensor.camera.rgb
UE spectator 是 CARLA 自带观察相机
```

之前 UE 第一视角会抖，是因为：

```text
UE 窗口本身会响应 WASD 或方向键移动 spectator
Python 脚本又每帧把 spectator 拉回车内
两边抢同一个相机
```

所以画面会抖。

pygame 版本不抖，因为它用的是：

```python
sensor.camera.rgb
```

这是一个真正挂在车上的摄像头。

推荐：

```text
驾驶画面 / 图像采集 / 算法输入：sensor.camera.rgb + pygame
外部观察：UE 窗口
不要用 UE spectator 当正式传感器数据
```

---

## 21. CSV 里常见字段说明

### gt_x / gt_y

CARLA 真实位置，用作标准答案。

### odom_x / odom_y

车速 + IMU gyro 推算轨迹。用于观察 odometry 漂移。

### fused_x / fused_y

odometry + GNSS 简单融合轨迹。用于观察 GNSS 修正是否减少漂移。

### gnss_x / gnss_y

GNSS 经纬度转换成的 CARLA 平面坐标。最容易出现方向问题。

### gyro_z

IMU 测得的 yaw rate，用于积分航向角。

### gyro_z_sign

自动判断 gyro.z 和 CARLA yaw 方向是否一致。

当前环境里通常是：

```text
gyro_z_sign = +1
```

### forward_speed_mps

车辆沿车头方向的速度，推荐用于轨迹积分。

### planar_speed_mps

车辆水平速度大小，适合显示和参考。

### speed_3d_mps

三维速度大小，会受 z 方向影响，不推荐直接用于平面轨迹积分。

---

## 22. 推荐调试流程

以后换地图、换车辆、换传感器位置，可以按这个顺序排查。

### 第一步：确认 yaw 和 forward vector 是否一致

打印：

```python
forward = transform.get_forward_vector()
yaw_rad = math.radians(rotation.yaw)

print(forward.x, forward.y)
print(math.cos(yaw_rad), math.sin(yaw_rad))
```

如果两者接近，说明：

```python
x += speed * math.cos(yaw) * dt
y += speed * math.sin(yaw) * dt
```

方向公式可用。

### 第二步：确认 gyro.z 符号

比较：

```text
delta_ground_truth_yaw
gyro.z * dt
```

如果大多数同号：

```python
gyro_z_sign = +1
```

如果大多数反号：

```python
gyro_z_sign = -1
```

### 第三步：确认 GNSS x/y 映射

比较：

```text
gt_x - gt_x0
gt_y - gt_y0
```

和：

```text
gnss_dx
gnss_dy
```

判断：

```text
是否 x 反号
是否 y 反号
是否 x/y 交换
```

当前地图结论是：

```python
x = ref_gt_x + dx
y = ref_gt_y - dy
```

### 第四步：看误差曲线

不要只看轨迹图，还要看：

```text
trajectory_error_plot.png
summary.txt
```

关注：

```text
mean error
max error
final error
```

---

## 23. 常见踩坑总结

### 坑 1：把 IMU acceleration 直接积分成位置

容易发散。除非做完整惯导算法，否则不建议直接使用。

### 坑 2：用 3D speed 做平面轨迹

会把车辆落地、颠簸、跳动的 z 速度算进去。推荐使用 forward speed。

### 坑 3：默认 GNSS latitude 对应 CARLA +y

不一定。当前数据里 latitude 对应 CARLA y 的反方向。

### 坑 4：认为 fusion 一定比 odometry 好

如果 GNSS 坐标转换错了，fusion 会更差。

### 坑 5：只看轨迹图，不看误差图

轨迹线靠得近不代表误差稳定。要看 error plot 和 summary。

### 坑 6：用 UE spectator 当驾驶相机

容易和 UE 原生输入冲突导致抖动。正式采集请用 sensor.camera.rgb。

### 坑 7：忘记 pygame 窗口焦点

pygame 只有在窗口获得焦点时才接收键盘。运行后需要点击 pygame 窗口。

### 坑 8：不同地图坐标系可能不同

Town10HD_Opt 上的 GNSS y 反号结论，换地图后不一定仍然成立。

---

## 24. 当前项目推荐配置

基于目前实验，推荐配置如下：

```text
显示：
  pygame + sensor.camera.rgb

轨迹估计：
  forward_speed + gyro.z

gyro 符号：
  自动判断 gyro_z_sign

GNSS 转换：
  x = ref_gt_x + dx
  y = ref_gt_y - dy

融合权重：
  alpha = 0.03 ~ 0.08
  默认先用 0.05

保存结果：
  trajectory_plot.png
  trajectory_error_plot.png
  trajectory_data.csv
  summary.txt
```

---

## 25. 多图层轨迹展示说明

当多条轨迹非常接近时，普通 2D 图会出现“线黏在一起”的问题。

可以把不同轨迹人为放在不同 z 图层上显示，例如：

```text
z = 0   CARLA Ground Truth
z = 10  Odometry
z = 20  Fusion
z = 30  GNSS converted points
```

注意：这个 z 轴不是车辆真实高度，只是为了看清不同轨迹而人为加的“图层高度”。

这种图适合观察：

```text
各条轨迹形状是否类似
哪条轨迹在转弯处偏差更大
GNSS 点是否出现镜像或方向错误
```

---

## 26. 最核心的理解

可以记住这句话：

```text
CARLA Ground Truth 是标准答案；
Odometry 是靠速度和陀螺仪推出来的，会漂；
GNSS 可以修正漂移，但前提是经纬度到 CARLA x/y 的方向映射必须正确。
```

在当前数据里，最关键的修正是：

```python
x = ref_gt_x + dx
y = ref_gt_y - dy
```

也就是：

```text
GNSS 经度变化对应 CARLA x；
GNSS 纬度变化对应 CARLA y 的反方向。
```

这就是之前“几条线趋势类似，但方向不一样”的根本原因。

