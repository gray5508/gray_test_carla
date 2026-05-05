# 11_mouse_and_opencv_detection.py 逐行注释

说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。

| 行号 | 代码 | 解释 |
|---:|---|---|
| 1 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 2 | `11_mouse_and_opencv_detection.py` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 3 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 4 | `本节目标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 5 | `  1. 鼠标点击获取像素点；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 6 | `  2. 演示 OpenCV 如何处理当前 RGB 图像；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 7 | `  3. 做一个很简单的颜色阈值检测，把检测点画回 pygame。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 8 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 9 | `这不是车道线算法，只是告诉你：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 10 | `  camera.latest_rgb 是普通 numpy 图像，可以直接交给 OpenCV / 深度学习模型。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 11 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 12 | `如果环境没有 opencv-python：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 13 | `  鼠标点击功能仍然可用；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 14 | `  OpenCV 检测部分会在 HUD 上提示 cv2 不可用。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 15 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 16 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 17 | `import pygame` | 导入 `pygame` 模块，供后续代码使用其中的函数、类或常量。 |
| 18 | `import numpy as np` | 导入 `numpy as np` 模块，供后续代码使用其中的函数、类或常量。 |
| 19 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 20 | `try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 21 | `    import cv2` | 导入 `cv2` 模块，供后续代码使用其中的函数、类或常量。 |
| 22 | `except ImportError:` | 异常捕获分支：当前面 `try` 中出现指定错误时执行。 |
| 23 | `    cv2 = None` | 给 `cv2` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 24 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 25 | `from common import CameraSensor` | 从 `common` 导入 `CameraSensor`，避免后面反复写模块前缀。 |
| 26 | `from common import WINDOW_HEIGHT` | 从 `common` 导入 `WINDOW_HEIGHT`，避免后面反复写模块前缀。 |
| 27 | `from common import WINDOW_WIDTH` | 从 `common` 导入 `WINDOW_WIDTH`，避免后面反复写模块前缀。 |
| 28 | `from common import connect_to_carla` | 从 `common` 导入 `connect_to_carla`，避免后面反复写模块前缀。 |
| 29 | `from common import destroy_actors` | 从 `common` 导入 `destroy_actors`，避免后面反复写模块前缀。 |
| 30 | `from common import draw_text_lines` | 从 `common` 导入 `draw_text_lines`，避免后面反复写模块前缀。 |
| 31 | `from common import get_keyboard_vehicle_control` | 从 `common` 导入 `get_keyboard_vehicle_control`，避免后面反复写模块前缀。 |
| 32 | `from common import make_pygame_surface` | 从 `common` 导入 `make_pygame_surface`，避免后面反复写模块前缀。 |
| 33 | `from common import spawn_ego_vehicle` | 从 `common` 导入 `spawn_ego_vehicle`，避免后面反复写模块前缀。 |
| 34 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 35 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 36 | `def detect_bright_yellow_points(rgb_image):` | 定义 `detect_bright_yellow_points` 函数，把一段可复用逻辑封装起来。 |
| 37 | `    """` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 38 | `    一个玩具检测器：找画面中偏黄色且较亮的区域中心。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 39 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 40 | `    真实项目里，你会把这里替换成：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 41 | `      lane detection model` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 42 | `      intersection detection model` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 43 | `      segmentation model` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 44 | `      keypoint model` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 45 | `    """` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 46 | `    if cv2 is None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 47 | `        return []` | 返回当前函数的计算结果，调用者会拿到这个值继续使用。 |
| 48 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 49 | `    # OpenCV 很多函数默认使用 BGR/HSV。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 50 | `    hsv = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2HSV)` | 给 `hsv` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 51 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 52 | `    # 黄色的一个粗略 HSV 范围。这个范围只是演示，不保证适合所有天气/地图。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 53 | `    lower = np.array([15, 80, 120], dtype=np.uint8)` | 进行 numpy 数组或矩阵计算，这是坐标变换和投影的数学基础。 |
| 54 | `    upper = np.array([40, 255, 255], dtype=np.uint8)` | 进行 numpy 数组或矩阵计算，这是坐标变换和投影的数学基础。 |
| 55 | `    mask = cv2.inRange(hsv, lower, upper)` | 给 `mask` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 56 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 57 | `    # 找轮廓，取面积比较大的区域中心。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 58 | `    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)` | 给 `contours, _` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 59 | `    points = []` | 给 `points` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 60 | `    for contour in contours:` | 循环语句：依次处理一个序列里的每个元素。 |
| 61 | `        area = cv2.contourArea(contour)` | 给 `area` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 62 | `        if area < 25:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 63 | `            continue` | 控制流程语句，用于跳出循环、进入下一轮循环，或占位不执行操作。 |
| 64 | `        m = cv2.moments(contour)` | 给 `m` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 65 | `        if m["m00"] <= 1e-6:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 66 | `            continue` | 控制流程语句，用于跳出循环、进入下一轮循环，或占位不执行操作。 |
| 67 | `        u = int(m["m10"] / m["m00"])` | 给 `u` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 68 | `        v = int(m["m01"] / m["m00"])` | 给 `v` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 69 | `        points.append((u, v, area))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 70 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 71 | `    # 面积大的排前面。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 72 | `    points.sort(key=lambda item: item[2], reverse=True)` | 给 `points.sort(key` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 73 | `    return points[:20]` | 返回当前函数的计算结果，调用者会拿到这个值继续使用。 |
| 74 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 75 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 76 | `def main():` | 定义 `main` 函数，把一段可复用逻辑封装起来。 |
| 77 | `    pygame.init()` | 初始化 pygame 主模块，后续才能创建窗口、读取事件和绘制图像。 |
| 78 | `    pygame.font.init()` | 初始化 pygame 字体模块，后续才能在窗口里渲染 HUD 文本。 |
| 79 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 80 | `    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))` | 创建 pygame 窗口，作为显示 CARLA 相机图像和 AR overlay 的画布。 |
| 81 | `    pygame.display.set_caption("11 mouse and OpenCV detection")` | 设置 pygame 窗口标题，方便区分当前运行的是哪个 lesson。 |
| 82 | `    font = pygame.font.SysFont("Arial", 18)` | 给 `font` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 83 | `    clock = pygame.time.Clock()` | 给 `clock` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 84 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 85 | `    client, world = connect_to_carla()` | 连接 CARLA server，并拿到 client 和 world。 |
| 86 | `    actors = []` | 给 `actors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 87 | `    current_steer = 0.0` | 给 `current_steer` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 88 | `    clicked_points = []` | 给 `clicked_points` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 89 | `    detected_points = []` | 给 `detected_points` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 90 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 91 | `    try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 92 | `        vehicle = spawn_ego_vehicle(world)` | 生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。 |
| 93 | `        actors.append(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 94 | `        camera = CameraSensor(world, vehicle, "sensor.camera.rgb")` | 创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。 |
| 95 | `        actors.append(camera.actor)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 96 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 97 | `        running = True` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 98 | `        while running:` | 循环语句：只要条件成立，就持续执行这个缩进块。 |
| 99 | `            clock.tick(30)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 100 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 101 | `            for event in pygame.event.get():` | 循环语句：依次处理一个序列里的每个元素。 |
| 102 | `                if event.type == pygame.QUIT:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 103 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 104 | `                elif event.type == pygame.KEYUP:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 105 | `                    if event.key == pygame.K_ESCAPE:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 106 | `                        running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 107 | `                    elif event.key == pygame.K_c:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 108 | `                        clicked_points = []` | 给 `clicked_points` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 109 | `                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 110 | `                    clicked_points.append(event.pos)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 111 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 112 | `            keys = pygame.key.get_pressed()` | 读取当前键盘按键状态，用于手动驾驶控制。 |
| 113 | `            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)` | 把 pygame 键盘状态转换为 CARLA 车辆控制命令。 |
| 114 | `            vehicle.apply_control(control)` | 把油门、刹车、方向盘等控制量发送给 CARLA 车辆。 |
| 115 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 116 | `            if camera.latest_rgb is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 117 | `                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 118 | `                detected_points = detect_bright_yellow_points(camera.latest_rgb)` | 给 `detected_points` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 119 | `            else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 120 | `                display.fill((10, 10, 10))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 121 | `                detected_points = []` | 给 `detected_points` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 122 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 123 | `            for point in clicked_points:` | 循环语句：依次处理一个序列里的每个元素。 |
| 124 | `                pygame.draw.circle(display, (255, 60, 60), point, 7, 2)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 125 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 126 | `            for u, v, area in detected_points:` | 循环语句：依次处理一个序列里的每个元素。 |
| 127 | `                pygame.draw.circle(display, (0, 255, 255), (u, v), 5, 0)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 128 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 129 | `            lines = [` | 给 `lines` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 130 | `                "Lesson 11 \| mouse pixels + optional OpenCV toy detector \| ESC quit \| C clear clicks",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 131 | `                "Clicked points: {}".format(clicked_points[-5:]),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 132 | `                "cv2: {} \| yellow detections: {}".format("available" if cv2 else "not installed", len(detected_points)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 133 | `                "Replace toy detector with your lane/intersection model later.",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 134 | `            ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 135 | `            draw_text_lines(pygame, display, font, lines)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 136 | `            pygame.display.flip()` | 刷新 pygame 窗口，把本帧绘制结果真正显示到屏幕上。 |
| 137 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 138 | `    finally:` | 最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。 |
| 139 | `        destroy_actors(actors)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 140 | `        pygame.quit()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 141 | `        print("Cleaned up.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 142 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 143 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 144 | `if __name__ == "__main__":` | Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。 |
| 145 | `    main()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
