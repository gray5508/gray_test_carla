# 00 教学设计：如何系统学习这个项目

这份教程建议分成四个阶段学习。每个阶段都对应一个“能跑、能看、能改”的目标。

## 阶段一：先跑起来，建立整体感觉

目标：知道这个系统在做什么，不急着理解每个公式。

学习内容：

- 启动 CARLA server。
- 运行 `main.py`。
- 用 `W/A/S/D` 开车。
- 按 `1/2/3` 选择导航意图。
- 打开 `M` 观察车道 debug。

验收标准：

- 你能解释“按 2 之后为什么不是立刻一定出现左转箭头”。
- 你能说出 YOLOP、导航意图、世界锚点分别负责什么。

## 阶段二：读主循环，理解实时系统结构

目标：读懂 `nav_demo/app.py`。

重点问题：

- 哪些事情每一帧都做？
- 哪些事情只有按键时做？
- YOLOP 为什么放在后台线程？
- 为什么相机帧、显示帧率、YOLOP 推理频率可以不同？

建议阅读文件：

- `nav_demo/app.py`
- `nav_demo/ui.py`
- `tutorials/01_pygame_event_loop.md`
- `tutorials/02_carla_runtime.md`

练习：

- 把 `--detect-interval` 改成 `2.0`。
- 把 `--display-fps` 改成 `20`。
- 观察窗口刷新和 YOLOP 推理提示的差异。

## 阶段三：攻克坐标转换和世界锚点

目标：理解“为什么箭头能像贴在路面上一样”。

重点问题：

- 图像像素如何反投影到车辆前方地面？
- 车辆局部地面坐标如何变成世界坐标？
- 为什么车辆往前开，世界箭头会从画面中向后退？
- `pass` 过期模式如何判断车辆已经开过箭头？

建议阅读文件：

- `nav_demo/geometry.py`
- `nav_demo/world_anchor.py`
- `tutorials/03_coordinate_transform.md`
- `tutorials/06_multisensor_fusion_motion_illusion.md`

练习：

- 试 `--arrow-projection screen`、`ground`、`world`。
- 试 `--world-anchor-expire-mode time` 和 `pass`。
- 试 `--world-anchor-pass-point start/center/target`。

## 阶段四：理解 YOLOP 和 AR 绘制

目标：知道模型结果如何变成视觉提示。

重点问题：

- YOLOP 输出的是导航指令吗？
- lane mask 如何变成中心线？
- 为什么候选箭头要经过稳定性确认？
- AR 箭头为什么分成 glow、主体、高光、边线几层？

建议阅读文件：

- `nav_demo/yolop_pipeline.py`
- `nav_demo/navigation.py`
- `nav_demo/ar_renderer.py`
- `tutorials/04_yolop_lane_pipeline.md`
- `tutorials/05_ar_arrow_rendering.md`

练习：

- 调整 `--min-confidence`。
- 调整 `--stability-confirmations`。
- 调整 `--ground-arrow-body-width-m` 和 `--arrow-flow-speed`。

## 最后的能力目标

学完后，你应该能独立回答：

- 如何把一个图像点转成车辆前方地面点？
- 为什么实时 UI 需要状态机，而不是直接画模型输出？
- 世界锚点和屏幕箭头的差别是什么？
- 如果以后加入 IMU/GNSS，应该在哪个模块替换或增强位姿来源？
- 如果要换一个车道检测模型，应该优先改哪个模块？
