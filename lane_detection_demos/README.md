# CARLA 车道线离线测试工具

这个文件夹现在先做一件事：

```text
先采集 CARLA 截图/视频
再离线分别跑 YOLOP / UFLD-v2
确认模型能不能识别当前路面车道线
调通后再接回实时 CARLA 视频流
```

## 文件结构

```text
lane_detection_demos/
  carla_capture_recorder.py   CARLA 截图/录视频素材采集
  carla_yolop_stable_arrow_demo.py  实时 YOLOP 稳定箭头 demo
  carla_yolop_navigation_hint_demo.py  带导航意图按键的实时箭头 demo
  offline_yolop_detect.py     只跑 YOLOP 的离线入口
  offline_yolop_turn_experiment.py  YOLOP lane mask 转弯/箭头离线实验
  offline_ufld_detect.py      只跑 UFLD-v2 的离线入口，默认 320x800
  offline_lane_detect.py      公共离线识别内核，也可以 --model both 对比
  model/
    yolop/
    ufld-v2/
  captures/                   采集到的原始素材
  offline_outputs/            离线识别输出
```

之前的两个实时模型 demo 入口已经删除，避免现在调试时混淆。

## 1. 采集素材

先启动 CARLA server：

```powershell
D:\HST_WORK\carla\WindowsNoEditor\CarlaUE4.exe -carla-rpc-port=2000
```

运行采集脚本：

```powershell
cd D:\HST_WORK\py_project\carla_test
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\carla_capture_recorder.py
```

按键：

```text
W/A/S/D 或方向键：开车
C：保存当前帧 PNG
V：开始录制
再次按 V：停止录制并保存
ESC：退出
```

输出：

```text
lane_detection_demos\captures\session_YYYYmmdd_HHMMSS\
  screenshots\
  videos\
```

## 2. 离线跑 YOLOP

默认会读取最新的 `captures/session_*`：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\offline_yolop_detect.py
```

指定某张图：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\offline_yolop_detect.py --input .\lane_detection_demos\captures\session_20260506_170216\screenshots\shot_0001_frame_1234943.png
```

指定某个视频：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\offline_yolop_detect.py --input .\lane_detection_demos\captures\session_20260506_170216\videos\recording_20260506_170231.mp4
```

## 3. 离线跑 UFLD-v2 320x800

这个入口默认加载：

```text
lane_detection_demos\model\ufld-v2\resources\ufldv2_tusimple_res34_320x800.onnx
```

直接跑最新素材：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\offline_ufld_detect.py
```

指定某张图或某个视频：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\offline_ufld_detect.py --input .\lane_detection_demos\captures\session_20260506_170216\screenshots\shot_0001_frame_1234943.png
```

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\offline_ufld_detect.py --input .\lane_detection_demos\captures\session_20260506_170216\videos\recording_20260506_170231.mp4
```

注意：模型文件名写的是 `320x800`，脚本内部参数按 OpenCV 常用习惯写成 `width=800, height=320`。控制台会打印 `UFLD input (HxW): 320x800`，方便确认没有跑错模型。

UFLD-v2 的 Tusimple 模型不是把原图直接压成 `320x800`。脚本会先把图像缩放到 `400x800`，再裁掉顶部 80 行，保留底部 `320x800` 输入模型；画回原图时使用 Tusimple 的 row anchors 做坐标还原。这个步骤如果省掉，车道线会明显漂到路面纹理和裂纹上。

## 4. 同时对比两个模型

如果想同一批素材同时输出 YOLOP 和 UFLD 两份结果，用公共脚本：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\offline_lane_detect.py --model both
```

## 5. YOLOP 转弯箭头离线实验

这个脚本不使用 CARLA waypoint，只使用 YOLOP 的 lane segmentation mask：

```text
YOLOP lane mask
-> 过滤画面下半部分 ROI
-> 过滤过宽横向线段
-> 逐行扫描左右车道边界
-> 估计当前车道中心线
-> 找视觉上的转弯/前视目标点
-> 画普通红色箭头
```

跑最新采集素材：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\offline_yolop_turn_experiment.py
```

只跑某个转弯片段，方便快速调参：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\offline_yolop_turn_experiment.py --input .\lane_detection_demos\captures\session_20260506_170216\videos\recording_20260506_170231.mp4 --start-frame 280 --end-frame 430
```

会额外输出一份 CSV 调试数据：

```text
原文件名__yolop_turn_debug.csv
```

注意：这个脚本现在还是纯 2D 图像实验。“车前 5m”在没有相机标定、IPM、深度或尺度信息时无法从 YOLOP 单目 mask 直接得到，所以当前用图像下方近处锚点代替。后面迁移到实车时，需要把这个近处锚点接到相机标定/IPM，才能换成真实 5m。

## 6. 实时 YOLOP 稳定箭头 demo

这个脚本会连接 CARLA server，打开 pygame 窗口，手动开车，并实时画导航风格箭头：

```text
每帧显示摄像头画面
每 1 秒后台跑一次 YOLOP
连续稳定识别到目标点后锁定箭头
箭头保持 3 秒，期间不跟着每帧检测结果抖动
```

运行：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\carla_yolop_stable_arrow_demo.py
```

按键：

```text
W/A/S/D 或方向键：开车
R：清空当前锁定箭头
M：开关调试几何显示
ESC：退出
```

常用调参：

```powershell
--detect-interval 1.0
--arrow-hold-seconds 3.0
--stability-confirmations 2
--stable-target-radius 120
```

如果只想看干净箭头，不显示绿色中心线和扫描点：

```powershell
--no-debug-geometry
```

当前实时脚本仍然不使用 CARLA waypoint。箭头起点默认是图像下方的固定近处锚点，用来近似“车前 5m”。后续接实车时，可以把这个起点替换成相机标定/IPM/深度算出来的真实 5m 像素点。

## 7. 实时 YOLOP 导航意图箭头 demo

这个版本把“导航意图”和“视觉检测”拆开：

```text
你按键给导航意图：直行 / 左转 / 右转
YOLOP 只判断当前画面有没有符合这个意图的车道几何
符合并稳定后，锁定箭头并保持 3 秒
```

运行：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\carla_yolop_navigation_hint_demo.py
```

按键：

```text
W/A/S/D 或方向键：开车
1：导航意图 = 直行
2：导航意图 = 左转
3：导航意图 = 右转
C 或 0：清空导航意图和箭头
M：开关调试几何显示
ESC：退出
```

逻辑区别：

```text
直行：固定画驾驶相机正前方约 5m 到 10m 的贴地直线箭头；只有这条线落在当前直行车道内才显示。
左转：只有 15m 内检测到中心线向左偏移到一定幅度，才锁定左转箭头。
右转：只有 15m 内检测到中心线向右偏移到一定幅度，才锁定右转箭头。
```

常用调参：

```powershell
--detect-interval 1.0
--arrow-hold-seconds 3.0
--stability-confirmations 2
--arrow-start-meters 5.0
--straight-target-forward-meters 10.0
--straight-right-meters -0.35
--max-target-forward-meters 15.0
--straight-validation-ratio 0.66
--straight-center-tolerance-ratio 0.11
--turn-min-shift-ratio 0.070
--stable-target-radius 130
```

默认只看干净箭头，不显示绿色中心线和扫描点。如果想看调试几何：

```powershell
--show-debug-geometry
```

这个脚本仍然不使用 CARLA waypoint，也没有真正识别“地面箭头标志”的语义；左/右转主要依据 YOLOP lane mask 形成的车道中心线弯曲/横向偏移来判断。`15m` 是基于相机安装参数和近似地面平面的估计，后续迁移实车时可以替换成真实标定/IPM。

直行箭头默认使用驾驶相机的正前方地面线，因此在画面里更像笔直向前。若想改回车辆几何中心线，可以加：

```powershell
--straight-right-meters 0.0
```

默认箭头样式是程序生成的霓虹动画，不依赖外部图片素材：

```powershell
--arrow-style neon
```

如果想切回普通线箭头：

```powershell
--arrow-style simple
```

如果想试“地面 3D 箭头投影到屏幕”的版本，用同级新脚本：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\carla_yolop_ground_arrow_demo.py
```

这个版本默认不是固定屏幕线宽，而是先在车辆地面坐标系里生成一个真实宽度的扁平箭头，再用相机内参和相机相对车辆的外参投影到 pygame 画面上，因此会自然产生近大远小效果。想临时切回旧的屏幕 2D 箭头，可以加：

```powershell
--arrow-projection screen
```

地面箭头常用调参：

```powershell
--ground-arrow-body-width-m 0.62
--ground-arrow-head-width-m 1.35
--ground-arrow-alpha 0.48
--ground-arrow-glow-alpha 0.18
```

如果想试“首次出现后固定到世界坐标”的版本，用：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\carla_yolop_world_anchor_arrow_demo.py
```

这个版本默认：

```powershell
--arrow-projection world
```

它会在箭头首次稳定锁定时，把箭头从车辆局部地面坐标转换成 CARLA 世界坐标；后续每帧用当前相机位姿重新投影，所以车往前开时，箭头会像真实路面标志一样相对车辆往后移动。CARLA 里这里用的是 actor transform 真值，迁移实车时对应替换成 IMU/轮速/GNSS/视觉里程计融合出来的车辆位姿。

当前世界锚定版本默认会一直保持这个世界箭头，直到车辆越过箭头前端才清除；`--arrow-hold-seconds 6.0` 只是给首次稳定锁定和备用时间模式使用。最终渲染长度默认缩短到原来的约 2/3：

```powershell
--world-anchor-expire-mode pass
--world-anchor-pass-point target
--world-anchor-pass-margin-m -0.50
--arrow-hold-seconds 6.0
--render-arrow-length-scale 0.67
```

如果想恢复按时间消失：

```powershell
--world-anchor-expire-mode time
```

常用动画调参：

```powershell
--arrow-flow-speed 0.80
--arrow-pulse-speed 0.85
--arrow-chevrons 2
--arrow-glow-width 34
--arrow-flow-alpha 0.34
```

后续如果你提供透明 PNG 序列帧，可以按这种结构放：

```text
lane_detection_demos\assets\arrows\straight\frame_000.png
lane_detection_demos\assets\arrows\straight\frame_001.png
lane_detection_demos\assets\arrows\left\frame_000.png
lane_detection_demos\assets\arrows\right\frame_000.png
```

当前版本先用程序生成动画，优点是会自动适配箭头起点、终点、长度和角度，不会受固定序列帧尺寸限制。

## 8. 输出在哪里

离线识别结果输出到：

```text
lane_detection_demos\offline_outputs\run_YYYYmmdd_HHMMSS\
```

图片会保存成：

```text
原文件名__yolop_annotated.png
原文件名__ufld_annotated.png
```

视频会保存成：

```text
原文件名__yolop_annotated.mp4
原文件名__ufld_annotated.mp4
```

## 9. 颜色含义

```text
YOLOP 蓝色区域：模型原始 lane mask
UFLD 绿色线段 ：模型原始 lane points
白色线         ：脚本选择的最近 guide line，默认不显示
转弯实验红色箭头：基于 YOLOP lane mask 估计的视觉前视方向
转弯实验绿色曲线：估计的当前车道中心线
```

如果想显示白色 guide line：

```powershell
--show-guide
```

## 10. 加速调试视频

视频很长时可以先只处理前 300 帧：

```powershell
--limit 300
```

视频每 3 帧推理一次，其余帧复用上一帧结果：

```powershell
--every 3
```

完整示例：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe .\lane_detection_demos\offline_ufld_detect.py --every 3 --limit 300
```

## 11. 默认模型路径

YOLOP：

```text
lane_detection_demos\model\yolop\yolop-640-640.onnx
```

UFLD-v2：

```text
lane_detection_demos\model\ufld-v2\resources\ufldv2_tusimple_res34_320x800.onnx
```

如果换模型，用：

```powershell
--yolop-onnx D:\models\xxx.onnx
--ufld-onnx D:\models\xxx.onnx
```
