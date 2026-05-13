# 07 调试清单与进阶练习

这份清单用于你自己改代码时定位问题。

## 现象：窗口打不开

检查：

- 是否使用了 `C:\Users\cicii\miniconda3\envs\carla_test\python.exe`。
- 当前环境是否安装 `pygame`。
- 是否在 `world_anchor_nav_modular_tutorial` 目录中运行。

命令：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe main.py --help
```

如果 `--help` 能显示，说明入口和参数解析正常。

## 现象：连接不上 CARLA

检查：

- CARLA server 是否已经启动。
- 端口是否是 `2000`。
- `common.py` 中的 CARLA 路径是否符合当前机器。

运行 CARLA：

```powershell
D:\HST_WORK\carla\WindowsNoEditor\CarlaUE4.exe -carla-rpc-port=2000
```

## 现象：YOLOP 报错或没有检测

检查：

- `lane_detection_demos/model/yolop/yolop-640-640.onnx` 是否存在。
- `onnxruntime` 是否在 `carla_test` 环境中可用。
- `--yolop-threshold` 是否过高。
- 是否按了 `1/2/3`。没有导航意图时不会提交检测。

## 现象：箭头不出现

可能原因：

- 当前没有导航意图。
- YOLOP 置信度低于 `--min-confidence`。
- 中心线点数量低于 `--min-center-points`。
- 候选目标不稳定，未达到 `--stability-confirmations`。
- 转弯偏移不足，未达到 `--turn-min-shift-ratio`。

建议：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe main.py --show-debug-geometry
```

看左上角 HUD 和车道中心线，先确认感知结果是否合理。

## 现象：箭头位置不对

优先检查：

- `camera_k` 是否按当前 width/height/FOV 生成。
- `camera_mount_transform` 是否正确。
- `vehicle_ground_z` 是否符合地面高度假设。
- 是否把 OpenCV 坐标和 CARLA/UE 坐标混了。

重点读：

- `geometry.py::pixel_to_vehicle_ground`
- `geometry.py::project_world_point_to_pixel`
- `world_anchor.py::create_world_arrow_anchor`

## 进阶练习

1. 加一个新的导航意图 `u_turn`，先只在状态机里支持，不必真的识别。
2. 给 `DetectionPacket` 增加 `debug_reason`，记录为什么这一帧没有生成候选。
3. 做一个离线图片调试脚本：读取一张截图，跑 YOLOP，保存 mask 和中心线图。
4. 把 `draw_world_flow_chevrons()` 的 chevron 数量改成和箭头长度自动相关。
5. 在 HUD 上显示当前车速和车辆世界坐标。
6. 把世界锚点过期逻辑改成：车辆开过 target 或者距离 target 太远都清除。
7. 尝试把 YOLOPAdapter 替换成另一个车道检测模型，但保持 `DetectionPacket` 接口不变。
