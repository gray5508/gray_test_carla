# 09_pixel_ground_plane_to_world.py 逐行注释

说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。

| 行号 | 代码 | 解释 |
|---:|---|---|
| 1 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 2 | `09_pixel_ground_plane_to_world.py` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 3 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 4 | `本节目标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 5 | `  不使用 depth camera，只假设鼠标点击的是“路面上的点”，然后把 pixel 反投影` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 6 | `  到地面平面 z=ground_z。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 7 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 8 | `为什么重要：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 9 | `  你后续的路口/车道线模型很可能只从 RGB 图像输出一个像素点。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 10 | `  如果这个点代表路面关键点，比如转弯入口点、车道中心点、停止线点，` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 11 | `  就可以用“像素射线与地面平面求交”估计它的世界坐标。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 12 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 13 | `限制：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 14 | `  如果道路有坡度、点不在地面、相机 pitch 不准，误差会明显。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 15 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 16 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 17 | `import pygame` | 导入 `pygame` 模块，供后续代码使用其中的函数、类或常量。 |
| 18 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 19 | `from common import CAMERA_FOV` | 从 `common` 导入 `CAMERA_FOV`，避免后面反复写模块前缀。 |
| 20 | `from common import CameraSensor` | 从 `common` 导入 `CameraSensor`，避免后面反复写模块前缀。 |
| 21 | `from common import WINDOW_HEIGHT` | 从 `common` 导入 `WINDOW_HEIGHT`，避免后面反复写模块前缀。 |
| 22 | `from common import WINDOW_WIDTH` | 从 `common` 导入 `WINDOW_WIDTH`，避免后面反复写模块前缀。 |
| 23 | `from common import build_camera_intrinsic_k` | 从 `common` 导入 `build_camera_intrinsic_k`，避免后面反复写模块前缀。 |
| 24 | `from common import connect_to_carla` | 从 `common` 导入 `connect_to_carla`，避免后面反复写模块前缀。 |
| 25 | `from common import debug_draw_point` | 从 `common` 导入 `debug_draw_point`，避免后面反复写模块前缀。 |
| 26 | `from common import destroy_actors` | 从 `common` 导入 `destroy_actors`，避免后面反复写模块前缀。 |
| 27 | `from common import draw_text_lines` | 从 `common` 导入 `draw_text_lines`，避免后面反复写模块前缀。 |
| 28 | `from common import get_ground_z` | 从 `common` 导入 `get_ground_z`，避免后面反复写模块前缀。 |
| 29 | `from common import get_keyboard_vehicle_control` | 从 `common` 导入 `get_keyboard_vehicle_control`，避免后面反复写模块前缀。 |
| 30 | `from common import ground_point_in_vehicle_frame` | 从 `common` 导入 `ground_point_in_vehicle_frame`，避免后面反复写模块前缀。 |
| 31 | `from common import make_pygame_surface` | 从 `common` 导入 `make_pygame_surface`，避免后面反复写模块前缀。 |
| 32 | `from common import pixel_to_world_on_ground` | 从 `common` 导入 `pixel_to_world_on_ground`，避免后面反复写模块前缀。 |
| 33 | `from common import spawn_ego_vehicle` | 从 `common` 导入 `spawn_ego_vehicle`，避免后面反复写模块前缀。 |
| 34 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 35 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 36 | `def main():` | 定义 `main` 函数，把一段可复用逻辑封装起来。 |
| 37 | `    pygame.init()` | 初始化 pygame 主模块，后续才能创建窗口、读取事件和绘制图像。 |
| 38 | `    pygame.font.init()` | 初始化 pygame 字体模块，后续才能在窗口里渲染 HUD 文本。 |
| 39 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 40 | `    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))` | 创建 pygame 窗口，作为显示 CARLA 相机图像和 AR overlay 的画布。 |
| 41 | `    pygame.display.set_caption("09 pixel to ground plane")` | 设置 pygame 窗口标题，方便区分当前运行的是哪个 lesson。 |
| 42 | `    font = pygame.font.SysFont("Arial", 18)` | 给 `font` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 43 | `    clock = pygame.time.Clock()` | 给 `clock` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 44 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 45 | `    k = build_camera_intrinsic_k(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)` | 构造相机内参矩阵 K，用于 camera 坐标和像素坐标之间的转换。 |
| 46 | `    client, world = connect_to_carla()` | 连接 CARLA server，并拿到 client 和 world。 |
| 47 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 48 | `    actors = []` | 给 `actors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 49 | `    current_steer = 0.0` | 给 `current_steer` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 50 | `    clicked_pixel = None` | 给 `clicked_pixel` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 51 | `    clicked_world = None` | 给 `clicked_world` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 52 | `    last_info = "Click a road pixel."` | 给 `last_info` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 53 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 54 | `    try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 55 | `        vehicle = spawn_ego_vehicle(world)` | 生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。 |
| 56 | `        actors.append(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 57 | `        camera = CameraSensor(world, vehicle, "sensor.camera.rgb")` | 创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。 |
| 58 | `        actors.append(camera.actor)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 59 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 60 | `        running = True` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 61 | `        while running:` | 循环语句：只要条件成立，就持续执行这个缩进块。 |
| 62 | `            clock.tick(30)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 63 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 64 | `            for event in pygame.event.get():` | 循环语句：依次处理一个序列里的每个元素。 |
| 65 | `                if event.type == pygame.QUIT:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 66 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 67 | `                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 68 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 69 | `                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 70 | `                    clicked_pixel = event.pos` | 读取鼠标事件中的像素坐标，作为手工标注或模拟检测点。 |
| 71 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 72 | `                    # 用车辆前方 10 米处的道路高度作为地面平面高度。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 73 | `                    # 这是假设局部路面近似水平。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 74 | `                    ahead = ground_point_in_vehicle_frame(world, vehicle, 10.0, 0.0)` | 用车辆局部坐标定义一个路面点，并转换成世界坐标。 |
| 75 | `                    ground_z = get_ground_z(world, ahead) + 0.04` | 给 `ground_z` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 76 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 77 | `                    clicked_world = pixel_to_world_on_ground(` | 把图像像素射线与地面平面求交，估计路面点的世界坐标。 |
| 78 | `                        clicked_pixel[0],` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 79 | `                        clicked_pixel[1],` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 80 | `                        camera.get_transform(),` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 81 | `                        k,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 82 | `                        ground_z,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 83 | `                    )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 84 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 85 | `                    if clicked_world is None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 86 | `                        last_info = "Ray does not hit ground plane in front of camera."` | 给 `last_info` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 87 | `                    else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 88 | `                        last_info = "pixel={} -> ground world=({:.2f},{:.2f},{:.2f})".format(` | 给 `last_info` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 89 | `                            clicked_pixel,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 90 | `                            clicked_world.x,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 91 | `                            clicked_world.y,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 92 | `                            clicked_world.z,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 93 | `                        )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 94 | `                    print(last_info)` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 95 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 96 | `            keys = pygame.key.get_pressed()` | 读取当前键盘按键状态，用于手动驾驶控制。 |
| 97 | `            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)` | 把 pygame 键盘状态转换为 CARLA 车辆控制命令。 |
| 98 | `            vehicle.apply_control(control)` | 把油门、刹车、方向盘等控制量发送给 CARLA 车辆。 |
| 99 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 100 | `            if camera.latest_rgb is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 101 | `                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 102 | `            else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 103 | `                display.fill((10, 10, 10))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 104 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 105 | `            if clicked_pixel is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 106 | `                pygame.draw.circle(display, (255, 60, 60), clicked_pixel, 8, 2)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 107 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 108 | `            if clicked_world is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 109 | `                debug_draw_point(world, clicked_world, text="ground hit")` | 使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。 |
| 110 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 111 | `            lines = [` | 给 `lines` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 112 | `                "Lesson 09 \| pixel ray intersects ground plane \| ESC quit",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 113 | `                "This is useful for RGB-only road keypoint detection.",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 114 | `                last_info,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 115 | `            ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 116 | `            draw_text_lines(pygame, display, font, lines)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 117 | `            pygame.display.flip()` | 刷新 pygame 窗口，把本帧绘制结果真正显示到屏幕上。 |
| 118 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 119 | `    finally:` | 最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。 |
| 120 | `        destroy_actors(actors)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 121 | `        pygame.quit()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 122 | `        print("Cleaned up.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 123 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 124 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 125 | `if __name__ == "__main__":` | Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。 |
| 126 | `    main()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
