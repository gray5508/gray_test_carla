# 04 YOLOP：从模型输出到导航候选

YOLOP 在这个 demo 里不是“导航模型”。它只负责从图像里识别车道相关信息。导航意图来自你按下的 `1/2/3`。

这个设计很重要：模型负责感知，人或上层规划模块负责意图。

## 输入和输出

输入：

```text
CARLA RGB camera frame
```

YOLOP 实际推理时使用 BGR 图像，因为 OpenCV 和项目里的 `YOLOPAdapter` 按 BGR 工作。

输出：

```text
lane_mask
debug_lines
```

本项目主要使用 `lane_mask`。随后 `estimate_current_lane()` 会从 mask 中扫描出当前车道的左右边界和中心线。

## 推理流程

对应代码在 `nav_demo/yolop_pipeline.py`：

```text
run_detection()
  -> RGB 转 BGR
  -> predict_yolop_mask()
  -> YOLOPAdapter.predict()
  -> estimate_current_lane()
  -> make_nav_candidate()
  -> DetectionPacket
```

`DetectionPacket` 是 YOLOP 线程返回给主循环的数据包，里面包含：

- `result`：车道几何结果。
- `candidate`：如果几何支持当前导航意图，就生成候选箭头。
- `inference_ms`：本次推理耗时。
- `frame_id`：来自 CARLA 相机帧号。
- `error`：异常信息。

## 为什么要先生成候选，再锁定箭头

模型每一帧可能有轻微抖动。如果每次检测都立即画箭头，画面会跳来跳去。

所以流程分两步：

1. `make_nav_candidate()`：当前帧是否能给出一个合理候选。
2. `NavigationArrowTracker.push()`：最近几次候选是否足够稳定，稳定后才锁定。

这就是“感知结果”和“用户可见 UI”之间加了一层状态机。

## 直行和转弯的判断差异

直行时，代码优先使用固定的车辆前方线段：比如从 10 米到 15 米。然后检查这条线是否落在当前车道内部。

左转/右转时，代码会从 YOLOP 中心线里找目标点，要求目标点相对起点有足够横向偏移：

- 目标在左侧，且偏移足够大：左转候选。
- 目标在右侧，且偏移足够大：右转候选。
- 偏移太小：更像直行，不生成转弯箭头。

## 学习任务

1. 在 `yolop_pipeline.py` 中阅读 `run_detection()`。
2. 在 `navigation.py` 中阅读 `make_nav_candidate()`。
3. 打开 `--show-debug-geometry`，观察车道中心线和箭头目标点之间的关系。
4. 调整 `--min-confidence`，观察候选箭头生成变严格或变宽松。
