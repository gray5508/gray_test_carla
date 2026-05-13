# 02 CARLA：世界、车辆、相机、清理

CARLA 这部分的重点不是“会调用 API”，而是理解实时仿真里有哪些对象在协作。

## 四个核心对象

- `client`：Python 和 CARLA server 通信的入口。
- `world`：当前仿真世界，负责地图、actor、天气、仿真模式等。
- `vehicle`：ego 主车，也就是我们用键盘控制的车。
- `camera`：挂在车上的 RGB 传感器，每隔一段时间产生图像。

在代码里，它们主要出现在 `nav_demo/app.py` 和 `nav_demo/carla_deps.py`。

## 为什么要切到异步模式

原始 demo 和教学版都会调用 `set_world_async(world)`。这表示 CARLA server 按自己的节奏运行，而 Python 端用 pygame 主循环不断读取最新状态。

异步模式适合这个项目，因为：

- 人在手动驾驶，输入不是严格固定帧率的。
- 相机图像通过回调更新，不需要每一帧都严格同步。
- YOLOP 推理放在后台线程，耗时也不是固定的。

如果你做数据集采集或严格复现实验，同步模式更合适。但这个教程的目标是实时交互式理解 AR 导航，因此异步模式更自然。

## actor 生命周期

CARLA 里的车、相机、行人、传感器都可以叫 actor。创建 actor 后一定要清理，否则仿真世界会留下越来越多对象。

教学版主循环使用：

```python
actors = []
vehicle = spawn_ego_vehicle(world)
actors.append(vehicle)
camera = CameraSensor(...)
actors.append(camera.actor)
```

退出时：

```python
destroy_actors(actors)
world.apply_settings(original_settings)
pygame.quit()
```

这段清理逻辑放在 `finally` 中，即使运行中报错，也尽量恢复 CARLA 世界设置并销毁 actor。

## 学习任务

1. 在 `app.py` 中找到 `spawn_ego_vehicle(world)`，理解车辆是如何进入世界的。
2. 找到 `CameraSensor(...)`，观察相机宽高、FOV、sensor_tick 如何设置。
3. 看 `set_world_async(world)` 和退出时的 `world.apply_settings(original_settings)`，理解为什么要保存原设置。
4. 尝试改 `--camera-fps 10`，观察相机刷新频率和显示帧率之间的差异。
