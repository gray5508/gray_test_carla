# CARLA + YOLOP 世界锚点 AR 箭头模块化教程

这个目录是基于上一层的 `carla_yolop_world_anchor_arrow_demo.py` 重新拆出来的教学版。原始 demo 把 CARLA、pygame、YOLOP、车道几何、导航状态机、AR 箭头绘制都写在一个文件里，适合快速演示，但不太适合逐块学习。这个版本的目标是：

- 保留原 demo 的实时功能：开 CARLA、按 `1/2/3` 选择导航意图、YOLOP 识别车道、显示世界锚点 AR 箭头。
- 把每个知识点拆成单独模块，方便你按主题阅读。
- 在模块顶部和关键函数旁边加入教学注释，说明“这段代码在系统里承担什么角色”。
- 在 `tutorials/` 中补充难点专题：YOLOP、坐标转换、AR 箭头、多传感器融合中的世界锚点思路。

## 运行环境

你当前指定的 Python 环境是：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe
```

推荐用这个解释器运行教程：

```powershell
cd D:\HST_WORK\py_project\carla_test\lane_detection_demos\world_anchor_nav_modular_tutorial
C:\Users\cicii\miniconda3\envs\carla_test\python.exe main.py
```

运行实时 demo 前，请先启动 CARLA server。例如：

```powershell
D:\HST_WORK\carla\WindowsNoEditor\CarlaUE4.exe -carla-rpc-port=2000
```

## 操作方式

- `W/A/S/D` 或方向键：控制车辆
- `1`：导航意图设为直行
- `2`：导航意图设为左转
- `3`：导航意图设为右转
- `C` 或 `0`：清除导航意图和当前箭头
- `M`：切换 YOLOP/车道几何调试显示
- `ESC`：退出

## 推荐学习顺序

1. 先看 `nav_demo/models.py`：理解模块之间传递的数据对象。
2. 再看 `nav_demo/app.py`：从主循环了解整个系统每一帧做什么。
3. 看 `nav_demo/yolop_pipeline.py`：理解相机图像如何进入 YOLOP，并转成车道几何。
4. 看 `nav_demo/geometry.py`：重点学习像素坐标、车辆局部坐标、CARLA 世界坐标之间的转换。
5. 看 `nav_demo/navigation.py`：学习如何把“人的导航意图”与“YOLOP 检测到的车道形状”结合起来。
6. 看 `nav_demo/world_anchor.py`：理解箭头为什么能像贴在真实地面上一样，车开过去时它会从画面中向后退。
7. 看 `nav_demo/ar_renderer.py`：学习发光箭头、多边形填充、流动 chevron 的绘制。
8. 最后读 `tutorials/`：每份专题教程都对应一个核心难点。

## 目录结构

```text
world_anchor_nav_modular_tutorial/
  main.py                         # 最小入口，只调用 nav_demo.app.run()
  nav_demo/
    app.py                        # 实时主循环：pygame + CARLA + YOLOP + 绘制
    models.py                     # 数据结构：候选箭头、锁定箭头、世界锚点等
    settings.py                   # 命令行参数
    runtime_deps.py               # 路径和运行时依赖桥接
    carla_deps.py                 # CARLA/common.py 相关导入
    runtime.py                    # CARLA 世界模式设置
    geometry.py                   # 坐标转换与车道几何判断
    yolop_pipeline.py             # YOLOP 推理和 mask 到车道的转换
    navigation.py                 # 导航意图、候选箭头、稳定锁定
    world_anchor.py               # 世界锚点状态机
    ar_renderer.py                # AR 箭头和 debug 几何绘制
    ui.py                         # 键盘导航意图和 HUD 文本
  tutorials/
    00_learning_design.md
    01_pygame_event_loop.md
    02_carla_runtime.md
    03_coordinate_transform.md
    04_yolop_lane_pipeline.md
    05_ar_arrow_rendering.md
    06_multisensor_fusion_motion_illusion.md
    07_debugging_and_exercises.md
  tests/
    test_geometry_basics.py       # 不依赖 CARLA 的基础几何测试
    test_tracker_lock.py          # 导航箭头稳定锁定测试
  scripts/
    preview_arrow_polygon.py      # 离线查看箭头地面多边形顶点
```

## 教学测试

这些测试不启动 CARLA，只验证拆出来的小模块：

```powershell
cd D:\HST_WORK\py_project\carla_test\lane_detection_demos\world_anchor_nav_modular_tutorial
C:\Users\cicii\miniconda3\envs\carla_test\python.exe -m unittest discover -s tests
```

你也可以先看命令行参数，不会连接 CARLA：

```powershell
C:\Users\cicii\miniconda3\envs\carla_test\python.exe main.py --help
```

## 核心思想

这个 demo 可以理解成一条实时流水线：

```text
pygame 键盘输入
  -> 设置导航意图 straight/left/right
CARLA 相机
  -> RGB 图像
YOLOP
  -> lane mask
车道几何
  -> 当前车道中心线、候选目标点
导航状态机
  -> 稳定后锁定箭头
世界锚点
  -> 把箭头从车辆局部坐标固定到 CARLA 世界坐标
AR 绘制
  -> 每帧按当前相机位置重新投影到画面
```

其中最重要的一句是：YOLOP 只负责“看见车道”，导航意图由你按键给出，世界锚点负责把已经确认的箭头固定在道路空间里。
