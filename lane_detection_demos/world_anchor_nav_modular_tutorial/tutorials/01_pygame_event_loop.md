# 01 pygame：实时程序的心跳

在这个项目里，pygame 不是重点算法，但它决定了实时 demo 是否“顺手”。你可以把 pygame 理解成三个职责：

- 创建一个窗口，显示 CARLA 相机画面。
- 读取键盘事件，用来控制车和切换导航意图。
- 维持一个稳定的帧循环，让画面持续刷新。

对应代码在 `nav_demo/app.py`。

## 每一帧发生什么

主循环大致是这样的：

```text
while running:
    控制显示帧率
    读取 pygame 事件
    读取持续按键状态
    把键盘转换成 CARLA vehicle control
    收取 YOLOP 后台线程结果
    必要时提交下一次 YOLOP 推理
    获取最新相机图像
    绘制车道 debug / AR 箭头 / HUD
    pygame.display.flip()
```

两个概念很容易混：

- `pygame.event.get()`：读取“发生过的事件”，例如刚刚按下 `1`、刚刚按下 `ESC`。
- `pygame.key.get_pressed()`：读取“当前是否按住”，例如一直按着 `W` 加速。

所以本项目把它们分开用：

- `1/2/3/C/M/ESC` 属于事件，因为只需要响应按下的那一下。
- `W/A/S/D` 属于持续状态，因为按住多久，车就应该持续控制多久。

## 为什么 YOLOP 要放后台线程

YOLOP 推理可能需要几十毫秒甚至更久。如果直接在 pygame 主循环里推理，画面会卡住，键盘也会变得不灵敏。

所以 `app.py` 使用：

```python
executor = ThreadPoolExecutor(max_workers=1)
pending_future = executor.submit(run_detection, ...)
```

这样主线程继续负责窗口和驾驶，后台线程负责模型推理。主循环每一帧检查 `pending_future.done()`，一旦推理完成，就把结果交给导航状态机。

## 学习任务

1. 在 `app.py` 里找到 `pygame.event.get()`，看哪些按键是“一次性事件”。
2. 找到 `pygame.key.get_pressed()`，看它如何控制车辆。
3. 把 `--detect-interval` 调大，比如 `2.0`，观察 YOLOP 刷新变慢但窗口仍然流畅。
4. 把 `--display-fps` 调低，比如 `20`，观察画面刷新与模型推理是两件不同的事。
