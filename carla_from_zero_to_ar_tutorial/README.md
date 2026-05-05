# CARLA 从零到 AR 贴地箭头详细教程

这份教程是一个更细的版本，按你提出的方向分成四层：

```text
1. CARLA 层面
   world / map / actor
   Transform / Location / Rotation
   vehicle local coordinate
   camera sensor
   depth camera
   debug draw

2. 几何层面
   相机内参 K
   相机外参 T
   世界坐标 -> 相机坐标
   相机坐标 -> 像素坐标
   像素坐标 + depth -> 相机坐标
   相机坐标 -> 世界坐标

3. 图像层面
   RGB image
   Depth image 解码
   pygame 显示
   OpenCV 检测点
   鼠标点击获取像素点

4. 融合层面
   车辆 transform
   IMU / GNSS
   车速
   坐标对齐
   轨迹估计
   AR overlay 稳定性
```

它是给“小白逐步上手”的，所以代码注释会比较详细，有些看似简单的地方也会解释为什么这么写。

## 0. 先确认环境

你的本机路径：

```text
Python 环境:
  C:\Users\cicii\miniconda3\envs\carla_test

CARLA 目录:
  D:\HST_WORK\carla\WindowsNoEditor

教程目录:
  D:\HST_WORK\py_project\carla_test\carla_from_zero_to_ar_tutorial
```

我检测到当前 CARLA 实际是 `0.9.15`：

```text
D:\HST_WORK\carla\WindowsNoEditor\PythonAPI\carla\dist\carla-0.9.15...
D:\HST_WORK\carla\WindowsNoEditor\CarlaUE4\Config\DefaultGame.ini -> ProjectVersion=0.9.15
```

先启动 CARLA server：

```powershell
D:\HST_WORK\carla\WindowsNoEditor\CarlaUE4.exe -carla-rpc-port=2000
```

再运行 lesson：

```powershell
cd D:\HST_WORK\py_project\carla_test\carla_from_zero_to_ar_tutorial
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 00_environment_check.py
```

## 1. 课程文件

### 基础公共文件

```text
common.py
```

这里放了每个 lesson 共用的函数：

```text
连接 CARLA
生成/清理车辆
RGB/Depth camera
Depth 解码
pygame 图像转换
车辆键盘控制
坐标转换
相机投影/反投影
AR 箭头几何
简单滤波
```

初学建议：

```text
先跑 lesson，不急着完全看懂 common.py。
当某个 lesson 调用了一个函数，再跳到 common.py 看那个函数的注释。
```

## 2. CARLA 层面

### 00_environment_check.py

目标：

```text
确认 Python 环境
确认 carla 包
确认能连接 server
打印 world / map / actor / blueprint 基本信息
```

运行：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 00_environment_check.py
```

### 01_world_map_actor.py

目标：

```text
理解 client / world / map / actor / blueprint
查看当前地图和出生点
生成一辆车
打印世界里的 actor
```

### 02_transform_location_rotation.py

目标：

```text
理解 Transform = Location + Rotation
理解 x/y/z 与 pitch/yaw/roll
观察修改车辆 yaw 后 forward vector 如何变化
```

### 03_vehicle_local_coordinate.py

目标：

```text
理解车辆局部坐标：
  +X 车头
  +Y 右侧
  +Z 上方

把车辆前方/左侧/右侧的局部点转换到 world 坐标
用 debug draw 在 CARLA 世界里显示这些点
```

### 04_rgb_camera_sensor.py

目标：

```text
创建 sensor.camera.rgb
理解 camera 是挂在 vehicle 上的 actor
理解 camera transform 是相对车辆的局部 Transform
把 CARLA BGRA 图像转成 RGB
用 pygame 显示相机第一视角
```

### 05_depth_camera_debug_draw.py

目标：

```text
创建 sensor.camera.depth
解码 depth image 到米
鼠标点击图像像素，读取该像素深度
用 pixel + depth 反算世界坐标
在 CARLA 世界里 debug draw 这个点
```

## 3. 几何层面

### 06_camera_intrinsic_k.py

目标：

```text
从 image width / height / FOV 计算相机内参 K
理解 fx/fy/cx/cy
用纯数学例子理解 camera coordinate -> pixel
```

### 07_world_to_pixel_projection.py

目标：

```text
CARLA world point -> camera UE coordinate
camera UE coordinate -> OpenCV camera coordinate
OpenCV camera coordinate -> pixel
把车辆前方多个地面点投影到 pygame 画面
```

### 08_pixel_depth_to_world.py

目标：

```text
鼠标点击图像像素
读取 depth camera 同一像素深度
pixel + depth -> camera coordinate
camera coordinate -> world coordinate
debug draw 世界点
```

### 09_pixel_ground_plane_to_world.py

目标：

```text
不用 depth camera
假设点击点在路面平面 z=ground_z
pixel ray 与地面平面求交
适合后续“检测到路面关键点”的场景
```

## 4. 图像层面

### 10_pygame_rgb_depth_viewer.py

目标：

```text
同屏显示 RGB 和 Depth
观察 RGB 与 Depth 的像素对应关系
鼠标移动时显示当前像素和 depth
```

### 11_mouse_and_opencv_detection.py

目标：

```text
鼠标点击获取像素点
OpenCV 读取当前 RGB 图像
做一个非常简单的颜色阈值检测示例
把检测点画回 pygame 画面
```

说明：

```text
如果你的环境没有 opencv-python，这个 lesson 仍能运行鼠标部分；
OpenCV 部分会提示缺少 cv2。
```

## 5. 融合层面

### 12_vehicle_imu_gnss_speed.py

目标：

```text
读取 vehicle transform
读取 vehicle velocity
计算 forward speed
挂载 IMU / GNSS
把数据实时显示到 pygame HUD
```

### 13_trajectory_estimation_basic.py

目标：

```text
用 forward speed + yaw 做最基础轨迹积分
同时记录 CARLA ground truth
保存 CSV
理解为什么轨迹估计会漂移
```

### 14_stable_ar_ground_arrow.py

目标：

```text
完整最小闭环：
  RGB camera
  鼠标/合成检测点
  pixel -> ground world
  目标点滤波
  ground arrow polygon
  world -> pixel
  pygame AR overlay
```

这是最接近你“转弯路口贴地箭头指向绘制”的 lesson。

## 6. 推荐运行顺序

第一次学习：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 00_environment_check.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 01_world_map_actor.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 02_transform_location_rotation.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 03_vehicle_local_coordinate.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 04_rgb_camera_sensor.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 05_depth_camera_debug_draw.py
```

开始理解投影/反投影：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 06_camera_intrinsic_k.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 07_world_to_pixel_projection.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 08_pixel_depth_to_world.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 09_pixel_ground_plane_to_world.py
```

开始做图像和 AR：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 10_pygame_rgb_depth_viewer.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 11_mouse_and_opencv_detection.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 14_stable_ar_ground_arrow.py
```

开始看融合：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 12_vehicle_imu_gnss_speed.py
C:\Users\cicii\miniconda3\envs\carla_test\python.exe 13_trajectory_estimation_basic.py
```

## 7. 从这套教程迁移到你的项目

你已有脚本：

```text
D:\HST_WORK\py_project\carla_test\多传感器融合测试\manual_drive_trajectory_compare.py
```

已经有：

```text
pygame 第一视角
手动控制
IMU / GNSS
轨迹记录
轨迹图和误差图
```

本教程补充：

```text
Depth 解码
相机 K / T
world <-> camera <-> pixel
鼠标/检测点反投影
贴地箭头 overlay
检测点滤波稳定
```

后面你可以把这些函数迁进去：

```text
build_camera_intrinsic_k
world_to_pixel
pixel_depth_to_world
pixel_to_world_on_ground
make_ground_arrow_polygon
project_polygon_to_pixels
ExponentialLocationFilter
```

## 8. 一句话主线

这套教程要帮你建立的直觉是：

```text
CARLA 给你真实世界坐标和传感器；
几何模型负责在 world / camera / pixel 之间来回转换；
图像算法给出像素检测点；
融合与滤波让检测点稳定；
AR overlay 把地面世界几何重新投影回相机画面。
```
