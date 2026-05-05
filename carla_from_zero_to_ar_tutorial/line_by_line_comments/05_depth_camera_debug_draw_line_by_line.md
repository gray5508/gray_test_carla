# 05_depth_camera_debug_draw.py 逐行注释

说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。

| 行号 | 代码 | 解释 |
|---:|---|---|
| 1 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 2 | `05_depth_camera_debug_draw.py` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 3 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 4 | `本节目标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 5 | `  1. 创建 RGB camera 和 Depth camera；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 6 | `  2. 解码 depth image 到米；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 7 | `  3. 鼠标点击 RGB 图像中的一个像素；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 8 | `  4. 读取同一像素的 depth；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 9 | `  5. 用 pixel + depth 反算世界坐标；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 10 | `  6. 在 CARLA 世界里 debug draw 这个点。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 11 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 12 | `这是“像素坐标 + 深度 -> 世界坐标”的第一次完整实践。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 13 | `后面如果你的模型能得到某个像素点，同时你有深度图，就可以用这个链路定位它。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 14 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 15 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 16 | `import pygame` | 导入 `pygame` 模块，供后续代码使用其中的函数、类或常量。 |
| 17 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 18 | `from common import CAMERA_FOV` | 从 `common` 导入 `CAMERA_FOV`，避免后面反复写模块前缀。 |
| 19 | `from common import CameraSensor` | 从 `common` 导入 `CameraSensor`，避免后面反复写模块前缀。 |
| 20 | `from common import WINDOW_HEIGHT` | 从 `common` 导入 `WINDOW_HEIGHT`，避免后面反复写模块前缀。 |
| 21 | `from common import WINDOW_WIDTH` | 从 `common` 导入 `WINDOW_WIDTH`，避免后面反复写模块前缀。 |
| 22 | `from common import build_camera_intrinsic_k` | 从 `common` 导入 `build_camera_intrinsic_k`，避免后面反复写模块前缀。 |
| 23 | `from common import connect_to_carla` | 从 `common` 导入 `connect_to_carla`，避免后面反复写模块前缀。 |
| 24 | `from common import debug_draw_point` | 从 `common` 导入 `debug_draw_point`，避免后面反复写模块前缀。 |
| 25 | `from common import destroy_actors` | 从 `common` 导入 `destroy_actors`，避免后面反复写模块前缀。 |
| 26 | `from common import draw_text_lines` | 从 `common` 导入 `draw_text_lines`，避免后面反复写模块前缀。 |
| 27 | `from common import get_keyboard_vehicle_control` | 从 `common` 导入 `get_keyboard_vehicle_control`，避免后面反复写模块前缀。 |
| 28 | `from common import make_pygame_surface` | 从 `common` 导入 `make_pygame_surface`，避免后面反复写模块前缀。 |
| 29 | `from common import pixel_depth_to_world` | 从 `common` 导入 `pixel_depth_to_world`，避免后面反复写模块前缀。 |
| 30 | `from common import spawn_ego_vehicle` | 从 `common` 导入 `spawn_ego_vehicle`，避免后面反复写模块前缀。 |
| 31 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 32 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 33 | `def main():` | 定义 `main` 函数，把一段可复用逻辑封装起来。 |
| 34 | `    pygame.init()` | 初始化 pygame 主模块，后续才能创建窗口、读取事件和绘制图像。 |
| 35 | `    pygame.font.init()` | 初始化 pygame 字体模块，后续才能在窗口里渲染 HUD 文本。 |
| 36 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 37 | `    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))` | 创建 pygame 窗口，作为显示 CARLA 相机图像和 AR overlay 的画布。 |
| 38 | `    pygame.display.set_caption("05 Depth camera debug draw")` | 设置 pygame 窗口标题，方便区分当前运行的是哪个 lesson。 |
| 39 | `    font = pygame.font.SysFont("Arial", 18)` | 给 `font` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 40 | `    clock = pygame.time.Clock()` | 给 `clock` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 41 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 42 | `    k = build_camera_intrinsic_k(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)` | 构造相机内参矩阵 K，用于 camera 坐标和像素坐标之间的转换。 |
| 43 | `    client, world = connect_to_carla()` | 连接 CARLA server，并拿到 client 和 world。 |
| 44 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 45 | `    actors = []` | 给 `actors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 46 | `    current_steer = 0.0` | 给 `current_steer` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 47 | `    clicked_pixel = None` | 给 `clicked_pixel` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 48 | `    clicked_world = None` | 给 `clicked_world` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 49 | `    clicked_depth = None` | 给 `clicked_depth` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 50 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 51 | `    try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 52 | `        vehicle = spawn_ego_vehicle(world)` | 生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。 |
| 53 | `        actors.append(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 54 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 55 | `        rgb_camera = CameraSensor(world, vehicle, "sensor.camera.rgb")` | 创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。 |
| 56 | `        depth_camera = CameraSensor(world, vehicle, "sensor.camera.depth")` | 创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。 |
| 57 | `        actors.extend([rgb_camera.actor, depth_camera.actor])` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 58 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 59 | `        running = True` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 60 | `        while running:` | 循环语句：只要条件成立，就持续执行这个缩进块。 |
| 61 | `            clock.tick(30)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 62 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 63 | `            for event in pygame.event.get():` | 循环语句：依次处理一个序列里的每个元素。 |
| 64 | `                if event.type == pygame.QUIT:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 65 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 66 | `                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 67 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 68 | `                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 69 | `                    clicked_pixel = event.pos` | 读取鼠标事件中的像素坐标，作为手工标注或模拟检测点。 |
| 70 | `                    if depth_camera.latest_depth_m is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 71 | `                        u, v = clicked_pixel` | 给 `u, v` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 72 | `                        if 0 <= u < WINDOW_WIDTH and 0 <= v < WINDOW_HEIGHT:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 73 | `                            clicked_depth = float(depth_camera.latest_depth_m[v, u])` | 给 `clicked_depth` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 74 | `                            clicked_world = pixel_depth_to_world(` | 根据像素坐标和 depth 值反算该点的 CARLA 世界坐标。 |
| 75 | `                                u, v, clicked_depth, rgb_camera.get_transform(), k` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 76 | `                            )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 77 | `                            print("Click pixel ({}, {}) depth {:.3f}m -> world x={:.3f}, y={:.3f}, z={:.3f}".format(` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 78 | `                                u, v, clicked_depth,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 79 | `                                clicked_world.x, clicked_world.y, clicked_world.z` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 80 | `                            ))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 81 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 82 | `            keys = pygame.key.get_pressed()` | 读取当前键盘按键状态，用于手动驾驶控制。 |
| 83 | `            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)` | 把 pygame 键盘状态转换为 CARLA 车辆控制命令。 |
| 84 | `            vehicle.apply_control(control)` | 把油门、刹车、方向盘等控制量发送给 CARLA 车辆。 |
| 85 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 86 | `            if rgb_camera.latest_rgb is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 87 | `                display.blit(make_pygame_surface(pygame, rgb_camera.latest_rgb), (0, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 88 | `            else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 89 | `                display.fill((10, 10, 10))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 90 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 91 | `            if clicked_pixel is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 92 | `                pygame.draw.circle(display, (255, 60, 60), clicked_pixel, 8, 2)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 93 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 94 | `            if clicked_world is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 95 | `                debug_draw_point(world, clicked_world, text="depth hit")` | 使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。 |
| 96 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 97 | `            lines = [` | 给 `lines` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 98 | `                "Lesson 05 \| RGB + Depth \| left click pixel -> world point \| ESC quit",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 99 | `                "Depth camera is decoded from CARLA BGRA to meters.",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 100 | `                "Clicked pixel: {} depth: {}".format(` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 101 | `                    clicked_pixel,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 102 | `                    "{:.3f}m".format(clicked_depth) if clicked_depth is not None else "-",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 103 | `                ),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 104 | `            ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 105 | `            draw_text_lines(pygame, display, font, lines)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 106 | `            pygame.display.flip()` | 刷新 pygame 窗口，把本帧绘制结果真正显示到屏幕上。 |
| 107 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 108 | `    finally:` | 最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。 |
| 109 | `        destroy_actors(actors)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 110 | `        pygame.quit()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 111 | `        print("Cleaned up.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 112 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 113 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 114 | `if __name__ == "__main__":` | Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。 |
| 115 | `    main()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
