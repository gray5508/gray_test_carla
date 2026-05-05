# 04_rgb_camera_sensor.py 逐行注释

说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。

| 行号 | 代码 | 解释 |
|---:|---|---|
| 1 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 2 | `04_rgb_camera_sensor.py` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 3 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 4 | `本节目标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 5 | `  1. 创建 sensor.camera.rgb；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 6 | `  2. 把 camera attach 到车辆；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 7 | `  3. 理解 camera transform 是车辆局部坐标；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 8 | `  4. 把 CARLA BGRA 图像转换成 RGB；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 9 | `  5. 用 pygame 显示第一视角，并用 pygame 控车。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 10 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 11 | `这就是你后续实景融合的“画布”。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 12 | `AR 箭头、检测点、HUD 都会叠加在这个 camera 图像上。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 13 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 14 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 15 | `import pygame` | 导入 `pygame` 模块，供后续代码使用其中的函数、类或常量。 |
| 16 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 17 | `from common import CameraSensor` | 从 `common` 导入 `CameraSensor`，避免后面反复写模块前缀。 |
| 18 | `from common import WINDOW_HEIGHT` | 从 `common` 导入 `WINDOW_HEIGHT`，避免后面反复写模块前缀。 |
| 19 | `from common import WINDOW_WIDTH` | 从 `common` 导入 `WINDOW_WIDTH`，避免后面反复写模块前缀。 |
| 20 | `from common import connect_to_carla` | 从 `common` 导入 `connect_to_carla`，避免后面反复写模块前缀。 |
| 21 | `from common import destroy_actors` | 从 `common` 导入 `destroy_actors`，避免后面反复写模块前缀。 |
| 22 | `from common import draw_text_lines` | 从 `common` 导入 `draw_text_lines`，避免后面反复写模块前缀。 |
| 23 | `from common import get_forward_speed` | 从 `common` 导入 `get_forward_speed`，避免后面反复写模块前缀。 |
| 24 | `from common import get_keyboard_vehicle_control` | 从 `common` 导入 `get_keyboard_vehicle_control`，避免后面反复写模块前缀。 |
| 25 | `from common import make_pygame_surface` | 从 `common` 导入 `make_pygame_surface`，避免后面反复写模块前缀。 |
| 26 | `from common import print_transform_details` | 从 `common` 导入 `print_transform_details`，避免后面反复写模块前缀。 |
| 27 | `from common import spawn_ego_vehicle` | 从 `common` 导入 `spawn_ego_vehicle`，避免后面反复写模块前缀。 |
| 28 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 29 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 30 | `def main():` | 定义 `main` 函数，把一段可复用逻辑封装起来。 |
| 31 | `    pygame.init()` | 初始化 pygame 主模块，后续才能创建窗口、读取事件和绘制图像。 |
| 32 | `    pygame.font.init()` | 初始化 pygame 字体模块，后续才能在窗口里渲染 HUD 文本。 |
| 33 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 34 | `    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))` | 创建 pygame 窗口，作为显示 CARLA 相机图像和 AR overlay 的画布。 |
| 35 | `    pygame.display.set_caption("04 RGB camera sensor")` | 设置 pygame 窗口标题，方便区分当前运行的是哪个 lesson。 |
| 36 | `    font = pygame.font.SysFont("Arial", 18)` | 给 `font` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 37 | `    clock = pygame.time.Clock()` | 给 `clock` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 38 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 39 | `    client, world = connect_to_carla()` | 连接 CARLA server，并拿到 client 和 world。 |
| 40 | `    actors = []` | 给 `actors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 41 | `    current_steer = 0.0` | 给 `current_steer` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 42 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 43 | `    try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 44 | `        vehicle = spawn_ego_vehicle(world)` | 生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。 |
| 45 | `        actors.append(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 46 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 47 | `        camera = CameraSensor(world, vehicle, camera_type="sensor.camera.rgb")` | 创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。 |
| 48 | `        actors.append(camera.actor)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 49 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 50 | `        print_transform_details("Camera local mount", camera.transform)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 51 | `        print("Camera actor world transform will change as vehicle moves.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 52 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 53 | `        running = True` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 54 | `        while running:` | 循环语句：只要条件成立，就持续执行这个缩进块。 |
| 55 | `            clock.tick(30)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 56 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 57 | `            for event in pygame.event.get():` | 循环语句：依次处理一个序列里的每个元素。 |
| 58 | `                if event.type == pygame.QUIT:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 59 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 60 | `                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 61 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 62 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 63 | `            keys = pygame.key.get_pressed()` | 读取当前键盘按键状态，用于手动驾驶控制。 |
| 64 | `            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)` | 把 pygame 键盘状态转换为 CARLA 车辆控制命令。 |
| 65 | `            vehicle.apply_control(control)` | 把油门、刹车、方向盘等控制量发送给 CARLA 车辆。 |
| 66 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 67 | `            if camera.latest_rgb is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 68 | `                surface = make_pygame_surface(pygame, camera.latest_rgb)` | 把 numpy 图像转换成 pygame 可以绘制的 surface。 |
| 69 | `                display.blit(surface, (0, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 70 | `            else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 71 | `                display.fill((10, 10, 10))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 72 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 73 | `            vehicle_tf = vehicle.get_transform()` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 74 | `            camera_tf = camera.get_transform()` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 75 | `            lines = [` | 给 `lines` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 76 | `                "Lesson 04 \| RGB camera sensor \| ESC quit",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 77 | `                "W/A/S/D or arrow keys drive in pygame window",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 78 | `                "Vehicle: x={:.2f} y={:.2f} yaw={:.2f}".format(` | 给 `"Vehicle: x` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 79 | `                    vehicle_tf.location.x, vehicle_tf.location.y, vehicle_tf.rotation.yaw` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 80 | `                ),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 81 | `                "Camera world: x={:.2f} y={:.2f} z={:.2f}".format(` | 给 `"Camera world: x` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 82 | `                    camera_tf.location.x, camera_tf.location.y, camera_tf.location.z` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 83 | `                ),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 84 | `                "Forward speed: {:.2f} m/s".format(get_forward_speed(vehicle)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 85 | `                "Image frame: {}".format(` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 86 | `                    camera.latest_image.frame if camera.latest_image is not None else "-"` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 87 | `                ),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 88 | `            ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 89 | `            draw_text_lines(pygame, display, font, lines)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 90 | `            pygame.display.flip()` | 刷新 pygame 窗口，把本帧绘制结果真正显示到屏幕上。 |
| 91 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 92 | `    finally:` | 最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。 |
| 93 | `        destroy_actors(actors)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 94 | `        pygame.quit()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 95 | `        print("Cleaned up.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 96 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 97 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 98 | `if __name__ == "__main__":` | Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。 |
| 99 | `    main()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
