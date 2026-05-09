# 模块化导航箭头学习版

这个子项目是从 `carla_yolop_navigation_hint_demo.py` 拆出来的学习版。老脚本继续保留，这里专门用来逐个模块学习、单独调试，最后再联调 CARLA 实时效果。

## 目录结构

```text
nav_learning_project/
  nav_learning/
    settings.py          所有参数默认值和 argparse
    models.py            NavCandidate / LockedNavArrow / DetectionPacket
    geometry.py          像素点、相机投影、车前 5m/10m、转向目标点选择
    lane_interpreter.py  把 YOLOP 车道几何转换成导航候选箭头
    yolop_detector.py    YOLOP 模型封装：图像 -> lane mask -> 当前车道几何
    tracker.py           稳定目标锁定：多次候选点稳定后锁定 3 秒
    arrow_renderer.py    普通箭头和霓虹箭头绘制
    pygame_view.py       pygame 窗口、按键和 BGR 图像显示
    carla_session.py     CARLA 世界、车辆、相机生命周期管理
  main/
    test_yolo.py         只测试 YOLOP，不需要 CARLA
    test_arrow_renderer.py 只测试箭头绘制，不需要 CARLA/YOLOP
    test_pygame_view.py  只测试 pygame 窗口和箭头动画，不需要 CARLA/YOLOP
    test_tracker.py      只测试稳定锁定逻辑
  run/
    run_live.py          完整联调：CARLA + pygame + YOLOP + tracker + arrow
```

## 推荐学习顺序

1. 先跑 tracker，理解“为什么箭头不会每帧抖”。
2. 再跑 arrow renderer，理解箭头是怎么画出来的。
3. 再跑 pygame view，理解窗口、按键和显示循环。
4. 重点跑 YOLOP，理解模型输出的 lane mask 和当前车道几何。
5. 最后跑 `run_live.py`，把所有模块串起来。

## 1. 稳定锁定逻辑

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\nav_learning_project\main\test_tracker.py
```

你会看到候选点一条一条推入 tracker，连续稳定后才生成 `locked arrow`。

## 2. 箭头绘制

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\nav_learning_project\main\test_arrow_renderer.py
```

输出默认在：

```text
lane_detection_demos\nav_learning_project\outputs\arrow_preview.jpg
```

常用调参：

```powershell
--arrow-style neon
--arrow-chevrons 2
--arrow-flow-alpha 0.34
--arrow-glow-width 34
```

## 3. pygame 窗口

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\nav_learning_project\main\test_pygame_view.py
```

按键：

```text
1：直行箭头
2：左转箭头
3：右转箭头
C 或 0：清空
ESC：退出
```

这个测试只验证 pygame 显示和箭头动画，不连接 CARLA，也不跑 YOLOP。

## 4. YOLOP 单独测试

默认读取最新截图：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\nav_learning_project\main\test_yolo.py
```

指定一张图：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\nav_learning_project\main\test_yolo.py --input .\lane_detection_demos\captures\session_20260506_170216\screenshots\shot_0001_frame_1234943.png
```

指定一个视频：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\nav_learning_project\main\test_yolo.py --input .\lane_detection_demos\captures\session_20260506_170216\videos\recording_20260506_170231.mp4 --every 3
```

输出默认在：

```text
lane_detection_demos\nav_learning_project\outputs\yolo_test\
```

如果想看 lane mask 叠加：

```powershell
--show-debug-mask
```

## 5. 完整联调

先启动 CARLA server，然后运行：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\nav_learning_project\run\run_live.py
```

按键和旧脚本一致：

```text
W/A/S/D 或方向键：开车
1：导航意图 = 直行
2：导航意图 = 左转
3：导航意图 = 右转
C 或 0：清空导航意图和箭头
M：开关调试几何显示
ESC：退出
```

## 读代码时抓住这条主线

```text
camera frame
-> YolopLaneDetector.analyze_bgr()
-> lane mask
-> estimate_current_lane()
-> LaneInterpreter.make_candidate()
-> NavigationArrowTracker.push()
-> ArrowRenderer.draw_locked_arrow()
-> PygameWindow.blit_bgr()
```

最值得细读的是 `yolop_detector.py` 和 `lane_interpreter.py`：前者回答“模型怎么变成 mask”，后者回答“mask 怎么变成导航箭头目标点”。

