# 03 坐标转换：像素、车辆坐标、世界坐标

这是本项目最重要的数学主题。AR 箭头能不能“贴在地面上”，关键就看坐标转换是否正确。

## 三套坐标

### 1. 图像像素坐标

图像像素用 `(u, v)` 表示：

- `u`：横向，向右增大。
- `v`：纵向，向下增大。
- 左上角是 `(0, 0)`。

YOLOP 输出的 lane mask、车道中心线点，最初都在这套坐标里。

### 2. 车辆局部地面坐标

本项目把地面点写成 `(forward_m, right_m)`：

- `forward_m`：车辆前方多少米。
- `right_m`：车辆右侧多少米，负数表示左侧。

这套坐标最适合描述“箭头应该在车前方 10 米到 15 米之间”。

### 3. CARLA 世界坐标

世界坐标是地图里的固定坐标。车辆会动，相机会动，但世界坐标中的地面点不动。

世界锚点箭头的核心是：箭头一旦稳定，就从车辆局部坐标转换到世界坐标。之后车辆继续移动，箭头仍然留在原来的道路位置。

## 主流程

```text
YOLOP lane pixel
  -> pixel_to_vehicle_ground()
  -> vehicle-local ground point
  -> vehicle_ground_to_world_point()
  -> world point
  -> project_world_point_to_pixel()
  -> current camera pixel
```

## 关键函数

- `pixel_to_vehicle_ground(point, args)`：把像素反投影成一条相机射线，再求这条射线和地面平面的交点。
- `vehicle_ground_to_pixel(forward_m, right_m, args, width, height)`：把车辆局部地面点投影回图像。
- `vehicle_ground_to_world_point(forward_m, right_m, vehicle_to_world, args)`：把车辆局部点变成世界坐标。
- `world_point_to_vehicle_local(point_world, vehicle_transform)`：把世界点转换回当前车辆局部坐标，用来判断车是否已经开过箭头。
- `project_world_point_to_pixel(point_world, camera_transform, args)`：每一帧用当前相机姿态把世界点投影到图像上。

## OpenCV 相机坐标和 CARLA 相机坐标

这部分很容易出错：

```text
OpenCV camera: x 向右, y 向下, z 向前
CARLA/UE camera: x 向前, y 向右, z 向上
```

所以代码里会出现这样的转换：

```python
point_cv = [point_ue[1], -point_ue[2], point_ue[0]]
```

它的意思是把 CARLA/Unreal 的相机坐标换成 OpenCV 投影公式习惯的坐标。

## 学习任务

1. 在 `geometry.py` 中阅读 `pixel_to_vehicle_ground()`，重点看相机射线如何和地面求交。
2. 阅读 `project_world_point_to_pixel()`，重点看世界点如何先转到当前相机坐标。
3. 修改 `--arrow-start-meters 8` 或 `--straight-target-forward-meters 20`，观察箭头起点和终点变化。
4. 如果箭头看起来漂浮或位置不对，优先检查 `camera_k`、相机安装姿态、`vehicle_ground_z`。
