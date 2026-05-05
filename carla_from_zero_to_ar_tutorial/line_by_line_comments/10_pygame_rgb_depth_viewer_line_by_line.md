# 10_pygame_rgb_depth_viewer.py 逐行注释

说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。

| 行号 | 代码 | 解释 |
|---:|---|---|
| 1 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 2 | `10_pygame_rgb_depth_viewer.py` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 3 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 4 | `本节目标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 5 | `  1. 同时显示 RGB 和 Depth；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 6 | `  2. 鼠标移动时读取当前像素和 depth；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 7 | `  3. 建立“同一个像素在 RGB/Depth 中一一对应”的直觉。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 8 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 9 | `显示布局：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 10 | `  左半屏：RGB camera` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 11 | `  右半屏：Depth camera 灰度可视化` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 12 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 13 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 14 | `import pygame` | 导入 `pygame` 模块，供后续代码使用其中的函数、类或常量。 |
| 15 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 16 | `from common import CameraSensor` | 从 `common` 导入 `CameraSensor`，避免后面反复写模块前缀。 |
| 17 | `from common import WINDOW_HEIGHT` | 从 `common` 导入 `WINDOW_HEIGHT`，避免后面反复写模块前缀。 |
| 18 | `from common import WINDOW_WIDTH` | 从 `common` 导入 `WINDOW_WIDTH`，避免后面反复写模块前缀。 |
| 19 | `from common import connect_to_carla` | 从 `common` 导入 `connect_to_carla`，避免后面反复写模块前缀。 |
| 20 | `from common import destroy_actors` | 从 `common` 导入 `destroy_actors`，避免后面反复写模块前缀。 |
| 21 | `from common import draw_text_lines` | 从 `common` 导入 `draw_text_lines`，避免后面反复写模块前缀。 |
| 22 | `from common import get_keyboard_vehicle_control` | 从 `common` 导入 `get_keyboard_vehicle_control`，避免后面反复写模块前缀。 |
| 23 | `from common import make_pygame_surface` | 从 `common` 导入 `make_pygame_surface`，避免后面反复写模块前缀。 |
| 24 | `from common import spawn_ego_vehicle` | 从 `common` 导入 `spawn_ego_vehicle`，避免后面反复写模块前缀。 |
| 25 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 26 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 27 | `def scale_surface_half(pygame, surface):` | 定义 `scale_surface_half` 函数，把一段可复用逻辑封装起来。 |
| 28 | `    """把 1280x720 surface 缩放成半屏宽。"""` | 单行文档字符串，用一句话说明当前函数或代码对象的用途。 |
| 29 | `    return pygame.transform.smoothscale(surface, (WINDOW_WIDTH // 2, WINDOW_HEIGHT))` | 返回当前函数的计算结果，调用者会拿到这个值继续使用。 |
| 30 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 31 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 32 | `def main():` | 定义 `main` 函数，把一段可复用逻辑封装起来。 |
| 33 | `    pygame.init()` | 初始化 pygame 主模块，后续才能创建窗口、读取事件和绘制图像。 |
| 34 | `    pygame.font.init()` | 初始化 pygame 字体模块，后续才能在窗口里渲染 HUD 文本。 |
| 35 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 36 | `    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))` | 创建 pygame 窗口，作为显示 CARLA 相机图像和 AR overlay 的画布。 |
| 37 | `    pygame.display.set_caption("10 RGB + Depth viewer")` | 设置 pygame 窗口标题，方便区分当前运行的是哪个 lesson。 |
| 38 | `    font = pygame.font.SysFont("Arial", 18)` | 给 `font` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 39 | `    clock = pygame.time.Clock()` | 给 `clock` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 40 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 41 | `    client, world = connect_to_carla()` | 连接 CARLA server，并拿到 client 和 world。 |
| 42 | `    actors = []` | 给 `actors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 43 | `    current_steer = 0.0` | 给 `current_steer` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 44 | `    mouse_info = "Move mouse over right half to inspect depth."` | 给 `mouse_info` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 45 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 46 | `    try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 47 | `        vehicle = spawn_ego_vehicle(world)` | 生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。 |
| 48 | `        actors.append(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 49 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 50 | `        rgb_camera = CameraSensor(world, vehicle, "sensor.camera.rgb")` | 创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。 |
| 51 | `        depth_camera = CameraSensor(world, vehicle, "sensor.camera.depth")` | 创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。 |
| 52 | `        actors.extend([rgb_camera.actor, depth_camera.actor])` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 53 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 54 | `        running = True` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 55 | `        while running:` | 循环语句：只要条件成立，就持续执行这个缩进块。 |
| 56 | `            clock.tick(30)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 57 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 58 | `            for event in pygame.event.get():` | 循环语句：依次处理一个序列里的每个元素。 |
| 59 | `                if event.type == pygame.QUIT:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 60 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 61 | `                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 62 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 63 | `                elif event.type == pygame.MOUSEMOTION:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 64 | `                    mx, my = event.pos` | 读取鼠标事件中的像素坐标，作为手工标注或模拟检测点。 |
| 65 | `                    # 右半屏显示的是缩放后的 depth，x 要映射回原始图像坐标。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 66 | `                    if mx >= WINDOW_WIDTH // 2 and depth_camera.latest_depth_m is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 67 | `                        u = int((mx - WINDOW_WIDTH // 2) * 2)` | 给 `u` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 68 | `                        v = int(my)` | 给 `v` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 69 | `                        if 0 <= u < WINDOW_WIDTH and 0 <= v < WINDOW_HEIGHT:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 70 | `                            depth = depth_camera.latest_depth_m[v, u]` | 给 `depth` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 71 | `                            mouse_info = "Depth pixel original=({}, {}) depth={:.2f}m".format(u, v, depth)` | 给 `mouse_info` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 72 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 73 | `            keys = pygame.key.get_pressed()` | 读取当前键盘按键状态，用于手动驾驶控制。 |
| 74 | `            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)` | 把 pygame 键盘状态转换为 CARLA 车辆控制命令。 |
| 75 | `            vehicle.apply_control(control)` | 把油门、刹车、方向盘等控制量发送给 CARLA 车辆。 |
| 76 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 77 | `            display.fill((0, 0, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 78 | `            if rgb_camera.latest_rgb is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 79 | `                rgb_surface = scale_surface_half(pygame, make_pygame_surface(pygame, rgb_camera.latest_rgb))` | 把 numpy 图像转换成 pygame 可以绘制的 surface。 |
| 80 | `                display.blit(rgb_surface, (0, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 81 | `            if depth_camera.latest_rgb is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 82 | `                depth_surface = scale_surface_half(pygame, make_pygame_surface(pygame, depth_camera.latest_rgb))` | 把 numpy 图像转换成 pygame 可以绘制的 surface。 |
| 83 | `                display.blit(depth_surface, (WINDOW_WIDTH // 2, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 84 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 85 | `            pygame.draw.line(display, (255, 255, 255), (WINDOW_WIDTH // 2, 0), (WINDOW_WIDTH // 2, WINDOW_HEIGHT), 2)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 86 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 87 | `            lines = [` | 给 `lines` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 88 | `                "Lesson 10 \| left RGB \| right Depth visualization \| ESC quit",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 89 | `                mouse_info,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 90 | `            ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 91 | `            draw_text_lines(pygame, display, font, lines)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 92 | `            pygame.display.flip()` | 刷新 pygame 窗口，把本帧绘制结果真正显示到屏幕上。 |
| 93 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 94 | `    finally:` | 最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。 |
| 95 | `        destroy_actors(actors)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 96 | `        pygame.quit()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 97 | `        print("Cleaned up.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 98 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 99 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 100 | `if __name__ == "__main__":` | Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。 |
| 101 | `    main()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
