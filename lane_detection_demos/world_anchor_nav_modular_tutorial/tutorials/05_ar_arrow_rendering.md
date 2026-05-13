# 05 AR 箭头：多边形、发光和流动效果

这个项目里的 AR 箭头不是图片素材，而是用 OpenCV 实时画出来的几何图形。这样做的好处是：

- 箭头大小可以用米来定义，而不是固定像素。
- 箭头可以从车辆局部坐标或世界坐标投影到画面。
- 发光、边线、内部高光、流动 chevron 都可以独立调节。

## 地面箭头多边形

核心函数是 `world_anchor.py` 中的：

```python
ground_arrow_polygon(start_ground, target_ground, body_width, head_width, head_length)
```

它返回 7 个地面点，组成一个箭头：

```text
左后角 -> 左身体 -> 左箭头肩部 -> 箭尖 -> 右箭头肩部 -> 右身体 -> 右后角
```

这些点一开始在车辆局部地面坐标中，单位是米。

## 绘制分层

`ar_renderer.py` 里的世界锚点箭头绘制大致分成四层：

1. 外层 glow：宽一些、透明一些，制造投影发光感。
2. 主体箭头：真实的箭头颜色。
3. 内层白色高光：让箭头更像 HUD/AR 投影。
4. 边线：增强轮廓，避免在亮色路面上看不清。

每一层都先画到临时图层，再用 `cv2.addWeighted()` 混合回原图。

## 流动 chevron

`draw_world_flow_chevrons()` 会沿箭头方向画几个移动的 V 形符号。移动感来自这个式子：

```python
t = (now * args.arrow_flow_speed + idx / chevrons) % 1.0
```

`now` 是当前时间。随着时间增加，`t` 在 0 到 1 之间循环，chevron 就沿箭头方向移动。

## ground、world、screen 三种投影

命令行参数 `--arrow-projection` 有三种：

- `screen`：直接在屏幕像素上画箭头，最简单，但没有真实贴地感。
- `ground`：每帧按当前车辆局部坐标画地面箭头，像“挂在车前方”。
- `world`：锁定后变成世界坐标，像真实地面标识，车辆开过去时箭头会向画面下方退去。

默认使用 `world`，这也是本教程的重点。

## 学习任务

1. 运行 `scripts/preview_arrow_polygon.py`，先离线理解箭头七边形的顶点。
2. 调整 `--ground-arrow-body-width-m`，观察箭身变宽或变窄。
3. 调整 `--ground-arrow-head-width-m`，观察箭头头部变化。
4. 调整 `--arrow-flow-speed`，观察 chevron 流动速度变化。
5. 尝试 `--arrow-projection screen`、`ground`、`world`，比较三种视觉差异。
