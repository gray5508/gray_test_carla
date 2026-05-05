# CARLA 实景融合与转弯路口贴地箭头 Tutorial

这份教程按你的当前需求整理：先在 CARLA 里建立一个能跑、能看、能点、能投影、能画贴地箭头的最小闭环，再逐步过渡到后续的车道线识别、转弯路口检测、传感器融合和标定。

我没有改你原来的 `多传感器融合测试/manual_drive_trajectory_compare.py`，而是在当前项目中新建了这个独立目录。

## 0. 当前环境确认

你说下载的是 `carla0.95`，但本机实际检测到的是：

```text
CARLA simulator: D:\HST_WORK\carla\WindowsNoEditor
ProjectVersion : 0.9.15
Python package : carla 0.9.15
Python env     : C:\Users\cicii\miniconda3\envs\carla_test
```

所以这套代码按 `CARLA 0.9.15 + Python 3.7` 写。你当前能跑 demo，说明基本依赖已经齐了。

先手动启动 server：

```powershell
D:\HST_WORK\carla\WindowsNoEditor\CarlaUE4.exe -carla-rpc-port=2000
```

再进入本目录运行 lesson：

```powershell
cd D:\HST_WORK\py_project\carla_test\carla_ar_turn_arrow_tutorial
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 00_environment_check.py
```

## 1. 你的需求拆解

你想做的不是单纯“画一个 2D UI 箭头”，而是类似 AR-HUD/实景融合：

```text
真实或仿真的相机画面
  + 感知模型检测到路面/路口上的某个点
  + 车辆自身位姿、相机外参、相机内参
  + 坐标转换和滤波预测
  -> 把转弯箭头稳定地画在指定地面位置
```

对应技术模块是：

```text
1. CARLA client/world/actor 基础
2. 车辆世界坐标和车辆局部坐标
3. camera sensor、pygame 显示与按键控制
4. 相机内参 K、相机外参 camera transform
5. world point -> image pixel 投影
6. image pixel -> ground world point 反投影
7. 路面点、检测点、预测点的平滑/融合
8. AR overlay：把地面多边形投影回图像画面
9. 同步传感器数据记录，为后续融合算法准备数据
```

## 2. 推荐学习顺序

### Lesson 00：环境检查

文件：

```text
00_environment_check.py
```

学什么：

```text
连接 CARLA server
打印地图、actor、blueprint
确认 Python 环境和 CARLA 版本
```

运行：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 00_environment_check.py
```

### Lesson 01：车辆生成和坐标轴

文件：

```text
01_spawn_vehicle_axes.py
```

学什么：

```text
车辆 world location / rotation
车辆 local +X/+Y/+Z
车辆前方 8 米如何变成 CARLA world 坐标
world.debug.draw_arrow / draw_point 调试
```

重点理解：

```text
CARLA world:
  x/y 是地图平面
  z 是向上

车辆 local:
  +X 是车头
  +Y 是车辆右侧
  +Z 是车辆上方
```

### Lesson 02：pygame 第一视角手动驾驶

文件：

```text
02_pygame_manual_drive_camera.py
```

学什么：

```text
sensor.camera.rgb 挂到车辆上
CARLA BGRA 图像转 RGB
pygame 显示 camera 画面
pygame 按键控制 vehicle.apply_control
```

为什么不用 UE spectator 当驾驶相机：

```text
UE 主窗口本身会响应 WASD/方向键移动 spectator。
如果 Python 又用这些键控制车辆，就容易出现视角和控制冲突。
pygame 窗口显示的是真正的 camera sensor 图像，按键只在 pygame 窗口焦点下生效。
```

### Lesson 03：世界点投影到相机图像

文件：

```text
03_camera_projection_basics.py
```

学什么：

```text
camera FOV -> 内参矩阵 K
camera.get_transform() -> 外参
world point -> camera local -> OpenCV camera coords -> pixel
```

核心坐标差异：

```text
CARLA camera local:   x forward, y right, z up
OpenCV camera coords: x right,   y down,  z forward

转换：
  (x_cv, y_cv, z_cv) = (y_ue, -z_ue, x_ue)
```

这个 lesson 会同时在：

```text
CARLA 世界里标点
pygame 图像里画投影点
```

你可以观察两者是否对齐。

### Lesson 04：核心闭环，贴地箭头 AR overlay

文件：

```text
04_ground_arrow_overlay.py
```

学什么：

```text
鼠标点击图像路面点，模拟“模型检测到的点”
pixel -> ground world point 反投影
车辆前方参考点 + 检测目标点
构造一个地面箭头多边形
把多边形世界点投影回 pygame 画面并半透明绘制
```

操作：

```text
W/A/S/D 或方向键   开车
鼠标左键           点击路面，生成检测目标点
C                  清除鼠标目标
T                  切换合成目标：左转/右转/直行
ESC                退出
```

这是目前最贴近你需求的 lesson。你可以把鼠标点击替换成模型输出：

```python
# 现在：
u, v = event.pos

# 后续：
u, v = lane_or_intersection_model_result.bottom_center
```

然后继续走：

```text
pixel_to_world_on_ground -> target_world -> make_arrow_polygon -> project_locations
```

### Lesson 05：同步传感器记录

文件：

```text
05_sensor_sync_recording.py
```

学什么：

```text
synchronous mode
fixed_delta_seconds
camera/IMU/GNSS frame 对齐
保存 CSV
```

输出：

```text
outputs/sensor_sync_recording.csv
```

注意：

```text
这个 lesson 会临时打开 synchronous mode，退出时会恢复原设置。
运行它时不要同时运行其他控制车辆的脚本。
```

### Lesson 06：检测点到地面点的算法骨架

文件：

```text
06_detection_to_ground_pipeline.py
```

学什么：

```text
模拟模型输出 noisy pixel
pixel -> ground world
世界坐标中做一阶低通滤波
用滤波后的目标点画更稳定的贴地箭头
```

操作：

```text
T  切换左转/右转/直行候选目标
N  开关像素噪声
R  重置滤波器
```

这一步开始接近后续真实感知模块的形态。

## 3. 与你现有脚本的关系

你已有的：

```text
多传感器融合测试/manual_drive_trajectory_compare.py
```

已经做了这些事情：

```text
pygame 第一视角
手动驾驶
IMU/GNSS
Ground Truth 轨迹
速度 + gyro 轨迹推算
GNSS 简单修正
保存 CSV/图像/summary
```

这份新 tutorial 的重点是补上另一条链：

```text
相机模型
投影/反投影
路面点标记
贴地箭头 AR overlay
检测点平滑
```

等你把 lesson 04/06 跑顺后，可以把这些模块迁回你的大脚本：

```text
manual_drive_trajectory_compare.py
  + build_camera_matrix
  + pixel_to_world_on_ground
  + make_arrow_polygon
  + project_locations
  + draw_transparent_polygon
  + model detection callback/result
```

## 4. 目前使用的两种“画箭头”方式

### 方式 A：pygame 客户端 AR overlay

这就是 lesson 04/06 的方式。

优点：

```text
直接叠加在 camera sensor 图像上
适合做实景融合、算法验证、录视频
不需要改 UE 材质或地图
```

缺点：

```text
箭头不是真正贴到 UE 世界的材质
只在你的 pygame/client 画面里存在
被其他物体遮挡的真实深度关系需要后续做深度/语义处理
```

### 方式 B：world.debug.draw_arrow

lesson 01/03/04 也用了这个。

优点：

```text
很适合确认世界坐标、方向、目标点是否正确
UE 主窗口里也能看到
```

缺点：

```text
它是 debug primitive，不适合作最终 AR 视觉效果
```

后续如果你要“真正贴在道路上”的 UE 效果，可以再研究：

```text
decal
static mesh plane
custom material
CARLA blueprint/UE editor 扩展
```

入门阶段先用 pygame overlay 更快。

## 5. 后续接真实模型时的接口建议

你的车道线/路口模型大概率会输出这些结果之一：

```text
1. 车道线像素点集合
2. 转弯路口候选区域 bbox/mask
3. 地面关键点 pixel，例如路口停止线、转弯入口点、目标车道中心点
4. BEV/鸟瞰坐标中的目标点
```

如果输出是图像像素点：

```text
pixel (u, v)
  -> pixel_to_world_on_ground
  -> world target point
```

如果输出是 segmentation mask：

```text
mask
  -> 选取底部中心点 / 骨架点 / 消失点附近点
  -> pixel_to_world_on_ground
```

如果输出已经是 BEV/车体坐标：

```text
vehicle local point
  -> transform_local_location(vehicle.get_transform(), local_point)
  -> world target point
```

最后统一进入：

```text
target_world
  -> filter / prediction
  -> make_arrow_polygon
  -> project_locations
  -> pygame overlay
```

## 6. 标定与坐标转换的学习重点

先掌握这三类变换：

```text
车辆 local -> world
world -> camera local
camera local -> image pixel
```

对应代码位置：

```text
common.py
  transform_local_location
  world_to_camera_ue
  world_to_pixel
  pixel_to_world_on_ground
```

入门阶段我们假设：

```text
相机外参 = CARLA 里 camera actor 的 transform
相机内参 = 根据 fov 和图像尺寸计算
路面局部 = z 固定的平面
```

真实系统里还要继续补：

```text
相机畸变参数
相机和车体的精确外参标定
地面不是完全平面的坡度问题
车辆悬挂/俯仰导致的相机姿态变化
检测延迟和传感器时间同步
```

## 7. 建议你先跑的最短路径

如果只想最快看到效果：

```powershell
cd D:\HST_WORK\py_project\carla_test\carla_ar_turn_arrow_tutorial

C:\Users\cicii\miniconda3\envs\carla_test\python.exe 00_environment_check.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 02_pygame_manual_drive_camera.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 03_camera_projection_basics.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 04_ground_arrow_overlay.py
```

如果你要开始做传感器数据分析：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 05_sensor_sync_recording.py
```

如果你要提前模拟模型输出的抖动和滤波：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 06_detection_to_ground_pipeline.py
```

## 8. 参考了哪些本地 CARLA 示例

本教程主要参考了你本机 CARLA 自带的官方示例：

```text
D:\HST_WORK\carla\WindowsNoEditor\PythonAPI\examples\tutorial.py
  actor / blueprint / spawn / sensor.listen 基础

D:\HST_WORK\carla\WindowsNoEditor\PythonAPI\examples\manual_control.py
  pygame UI、键盘控制、camera surface

D:\HST_WORK\carla\WindowsNoEditor\PythonAPI\examples\sensor_synchronization.py
  synchronous mode 和 Queue 对齐传感器

D:\HST_WORK\carla\WindowsNoEditor\PythonAPI\examples\lidar_to_camera.py
  camera K、world->camera、CARLA camera 坐标到 OpenCV camera 坐标
```

也参考了你已有脚本：

```text
D:\HST_WORK\py_project\carla_test\多传感器融合测试\manual_drive_trajectory_compare.py
```

它里面的 pygame 驾驶、IMU/GNSS、轨迹记录思路可以和这套 AR overlay 继续合并。
