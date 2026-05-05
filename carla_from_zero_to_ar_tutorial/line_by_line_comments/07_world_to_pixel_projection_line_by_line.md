# 07_world_to_pixel_projection.py 逐行注释

说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。

| 行号 | 代码 | 解释 |
|---:|---|---|
| 1 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 2 | `07_world_to_pixel_projection.py` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 3 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 4 | `本节目标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 5 | `  1. 把 CARLA 世界坐标点投影到 RGB camera 图像；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 6 | `  2. 理解 world -> camera UE -> camera CV -> pixel；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 7 | `  3. 在 pygame 画面上标记车辆前方的地面点。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 8 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 9 | `这就是 AR overlay 的半条链：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 10 | `  world ground point -> image pixel` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 11 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 12 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 13 | `import pygame` | 导入 `pygame` 模块，供后续代码使用其中的函数、类或常量。 |
| 14 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 15 | `from common import CAMERA_FOV` | 从 `common` 导入 `CAMERA_FOV`，避免后面反复写模块前缀。 |
| 16 | `from common import CameraSensor` | 从 `common` 导入 `CameraSensor`，避免后面反复写模块前缀。 |
| 17 | `from common import WINDOW_HEIGHT` | 从 `common` 导入 `WINDOW_HEIGHT`，避免后面反复写模块前缀。 |
| 18 | `from common import WINDOW_WIDTH` | 从 `common` 导入 `WINDOW_WIDTH`，避免后面反复写模块前缀。 |
| 19 | `from common import build_camera_intrinsic_k` | 从 `common` 导入 `build_camera_intrinsic_k`，避免后面反复写模块前缀。 |
| 20 | `from common import carla` | 从 `common` 导入 `carla`，避免后面反复写模块前缀。 |
| 21 | `from common import connect_to_carla` | 从 `common` 导入 `connect_to_carla`，避免后面反复写模块前缀。 |
| 22 | `from common import debug_draw_point` | 从 `common` 导入 `debug_draw_point`，避免后面反复写模块前缀。 |
| 23 | `from common import destroy_actors` | 从 `common` 导入 `destroy_actors`，避免后面反复写模块前缀。 |
| 24 | `from common import draw_text_lines` | 从 `common` 导入 `draw_text_lines`，避免后面反复写模块前缀。 |
| 25 | `from common import get_keyboard_vehicle_control` | 从 `common` 导入 `get_keyboard_vehicle_control`，避免后面反复写模块前缀。 |
| 26 | `from common import ground_point_in_vehicle_frame` | 从 `common` 导入 `ground_point_in_vehicle_frame`，避免后面反复写模块前缀。 |
| 27 | `from common import make_pygame_surface` | 从 `common` 导入 `make_pygame_surface`，避免后面反复写模块前缀。 |
| 28 | `from common import spawn_ego_vehicle` | 从 `common` 导入 `spawn_ego_vehicle`，避免后面反复写模块前缀。 |
| 29 | `from common import world_to_pixel` | 从 `common` 导入 `world_to_pixel`，避免后面反复写模块前缀。 |
| 30 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 31 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 32 | `def draw_pixel_marker(pygame, display, font, pixel, color, label):` | 定义 `draw_pixel_marker` 函数，把一段可复用逻辑封装起来。 |
| 33 | `    if pixel is None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 34 | `        return` | 提前结束当前函数，不返回具体值。 |
| 35 | `    u, v, depth = pixel` | 给 `u, v, depth` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 36 | `    center = (int(u), int(v))` | 给 `center` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 37 | `    pygame.draw.circle(display, color, center, 7, 0)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 38 | `    pygame.draw.circle(display, (0, 0, 0), center, 9, 2)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 39 | `    text = font.render("{} {:.1f}m".format(label, depth), True, color)` | 给 `text` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 40 | `    display.blit(text, (center[0] + 10, center[1] - 10))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 41 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 42 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 43 | `def main():` | 定义 `main` 函数，把一段可复用逻辑封装起来。 |
| 44 | `    pygame.init()` | 初始化 pygame 主模块，后续才能创建窗口、读取事件和绘制图像。 |
| 45 | `    pygame.font.init()` | 初始化 pygame 字体模块，后续才能在窗口里渲染 HUD 文本。 |
| 46 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 47 | `    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))` | 创建 pygame 窗口，作为显示 CARLA 相机图像和 AR overlay 的画布。 |
| 48 | `    pygame.display.set_caption("07 world point to pixel")` | 设置 pygame 窗口标题，方便区分当前运行的是哪个 lesson。 |
| 49 | `    font = pygame.font.SysFont("Arial", 18)` | 给 `font` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 50 | `    clock = pygame.time.Clock()` | 给 `clock` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 51 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 52 | `    k = build_camera_intrinsic_k(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)` | 构造相机内参矩阵 K，用于 camera 坐标和像素坐标之间的转换。 |
| 53 | `    client, world = connect_to_carla()` | 连接 CARLA server，并拿到 client 和 world。 |
| 54 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 55 | `    actors = []` | 给 `actors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 56 | `    current_steer = 0.0` | 给 `current_steer` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 57 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 58 | `    try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 59 | `        vehicle = spawn_ego_vehicle(world)` | 生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。 |
| 60 | `        actors.append(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 61 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 62 | `        camera = CameraSensor(world, vehicle, "sensor.camera.rgb")` | 创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。 |
| 63 | `        actors.append(camera.actor)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 64 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 65 | `        running = True` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 66 | `        while running:` | 循环语句：只要条件成立，就持续执行这个缩进块。 |
| 67 | `            clock.tick(30)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 68 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 69 | `            for event in pygame.event.get():` | 循环语句：依次处理一个序列里的每个元素。 |
| 70 | `                if event.type == pygame.QUIT:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 71 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 72 | `                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 73 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 74 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 75 | `            keys = pygame.key.get_pressed()` | 读取当前键盘按键状态，用于手动驾驶控制。 |
| 76 | `            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)` | 把 pygame 键盘状态转换为 CARLA 车辆控制命令。 |
| 77 | `            vehicle.apply_control(control)` | 把油门、刹车、方向盘等控制量发送给 CARLA 车辆。 |
| 78 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 79 | `            if camera.latest_rgb is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 80 | `                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 81 | `            else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 82 | `                display.fill((10, 10, 10))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 83 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 84 | `            samples = [` | 给 `samples` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 85 | `                ("5m", 5.0, 0.0, (255, 255, 0), carla.Color(255, 255, 0)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 86 | `                ("10m", 10.0, 0.0, (255, 150, 0), carla.Color(255, 150, 0)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 87 | `                ("15m", 15.0, 0.0, (255, 80, 0), carla.Color(255, 80, 0)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 88 | `                ("left", 10.0, -2.5, (0, 220, 255), carla.Color(0, 220, 255)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 89 | `                ("right", 10.0, 2.5, (255, 0, 255), carla.Color(255, 0, 255)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 90 | `            ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 91 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 92 | `            camera_tf = camera.get_transform()` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 93 | `            for label, forward_m, right_m, pg_color, dbg_color in samples:` | 循环语句：依次处理一个序列里的每个元素。 |
| 94 | `                world_point = ground_point_in_vehicle_frame(world, vehicle, forward_m, right_m)` | 用车辆局部坐标定义一个路面点，并转换成世界坐标。 |
| 95 | `                debug_draw_point(world, world_point, dbg_color, label)` | 使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。 |
| 96 | `                pixel = world_to_pixel(world_point, camera_tf, k, WINDOW_WIDTH, WINDOW_HEIGHT, margin=30.0)` | 把 CARLA 世界坐标点投影到相机图像像素位置。 |
| 97 | `                draw_pixel_marker(pygame, display, font, pixel, pg_color, label)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 98 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 99 | `            lines = [` | 给 `lines` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 100 | `                "Lesson 07 \| world point -> pixel \| ESC quit",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 101 | `                "CARLA debug points and pygame markers should match visually.",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 102 | `                "Chain: world -> camera UE -> camera CV -> pixel.",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 103 | `            ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 104 | `            draw_text_lines(pygame, display, font, lines)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 105 | `            pygame.display.flip()` | 刷新 pygame 窗口，把本帧绘制结果真正显示到屏幕上。 |
| 106 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 107 | `    finally:` | 最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。 |
| 108 | `        destroy_actors(actors)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 109 | `        pygame.quit()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 110 | `        print("Cleaned up.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 111 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 112 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 113 | `if __name__ == "__main__":` | Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。 |
| 114 | `    main()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
