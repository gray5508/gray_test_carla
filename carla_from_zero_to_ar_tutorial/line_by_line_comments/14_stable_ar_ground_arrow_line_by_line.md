# 14_stable_ar_ground_arrow.py 逐行注释

说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。

| 行号 | 代码 | 解释 |
|---:|---|---|
| 1 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 2 | `14_stable_ar_ground_arrow.py` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 3 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 4 | `本节目标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 5 | `  完整跑通一个教学版“转弯路口贴地箭头”闭环。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 6 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 7 | `链路：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 8 | `  RGB camera 图像` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 9 | `    -> 鼠标点击或合成检测点，得到 pixel` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 10 | `    -> pixel ray 与地面平面相交，得到 target_world` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 11 | `    -> 对 target_world 做低通滤波，减少抖动` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 12 | `    -> 车辆前方参考点 ahead_world` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 13 | `    -> ahead_world + target_world 构造地面箭头多边形` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 14 | `    -> 多边形世界点投影回 image pixel` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 15 | `    -> pygame 半透明 AR overlay` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 16 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 17 | `操作：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 18 | `  W/A/S/D 或方向键   手动驾驶` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 19 | `  鼠标左键           模拟模型检测到一个路面点` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 20 | `  C                  清除鼠标目标，回到合成目标` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 21 | `  T                  切换合成目标：左转/右转/直行` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 22 | `  R                  重置滤波器` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 23 | `  ESC                退出` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 24 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 25 | `注意：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 26 | `  这是客户端 overlay，不是 UE 里真正贴了 decal。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 27 | `  但几何链路是真的：world/camera/pixel 都按相机模型计算。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 28 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 29 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 30 | `import random` | 导入 `random` 模块，供后续代码使用其中的函数、类或常量。 |
| 31 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 32 | `import pygame` | 导入 `pygame` 模块，供后续代码使用其中的函数、类或常量。 |
| 33 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 34 | `from common import CAMERA_FOV` | 从 `common` 导入 `CAMERA_FOV`，避免后面反复写模块前缀。 |
| 35 | `from common import CameraSensor` | 从 `common` 导入 `CameraSensor`，避免后面反复写模块前缀。 |
| 36 | `from common import ExponentialLocationFilter` | 从 `common` 导入 `ExponentialLocationFilter`，避免后面反复写模块前缀。 |
| 37 | `from common import WINDOW_HEIGHT` | 从 `common` 导入 `WINDOW_HEIGHT`，避免后面反复写模块前缀。 |
| 38 | `from common import WINDOW_WIDTH` | 从 `common` 导入 `WINDOW_WIDTH`，避免后面反复写模块前缀。 |
| 39 | `from common import build_camera_intrinsic_k` | 从 `common` 导入 `build_camera_intrinsic_k`，避免后面反复写模块前缀。 |
| 40 | `from common import carla` | 从 `common` 导入 `carla`，避免后面反复写模块前缀。 |
| 41 | `from common import connect_to_carla` | 从 `common` 导入 `connect_to_carla`，避免后面反复写模块前缀。 |
| 42 | `from common import debug_draw_arrow` | 从 `common` 导入 `debug_draw_arrow`，避免后面反复写模块前缀。 |
| 43 | `from common import debug_draw_point` | 从 `common` 导入 `debug_draw_point`，避免后面反复写模块前缀。 |
| 44 | `from common import destroy_actors` | 从 `common` 导入 `destroy_actors`，避免后面反复写模块前缀。 |
| 45 | `from common import draw_text_lines` | 从 `common` 导入 `draw_text_lines`，避免后面反复写模块前缀。 |
| 46 | `from common import get_ground_z` | 从 `common` 导入 `get_ground_z`，避免后面反复写模块前缀。 |
| 47 | `from common import get_keyboard_vehicle_control` | 从 `common` 导入 `get_keyboard_vehicle_control`，避免后面反复写模块前缀。 |
| 48 | `from common import ground_point_in_vehicle_frame` | 从 `common` 导入 `ground_point_in_vehicle_frame`，避免后面反复写模块前缀。 |
| 49 | `from common import make_ground_arrow_polygon` | 从 `common` 导入 `make_ground_arrow_polygon`，避免后面反复写模块前缀。 |
| 50 | `from common import make_pygame_surface` | 从 `common` 导入 `make_pygame_surface`，避免后面反复写模块前缀。 |
| 51 | `from common import pixel_to_world_on_ground` | 从 `common` 导入 `pixel_to_world_on_ground`，避免后面反复写模块前缀。 |
| 52 | `from common import project_polygon_to_pixels` | 从 `common` 导入 `project_polygon_to_pixels`，避免后面反复写模块前缀。 |
| 53 | `from common import spawn_ego_vehicle` | 从 `common` 导入 `spawn_ego_vehicle`，避免后面反复写模块前缀。 |
| 54 | `from common import world_to_pixel` | 从 `common` 导入 `world_to_pixel`，避免后面反复写模块前缀。 |
| 55 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 56 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 57 | `TARGET_MODES = [` | 给 `TARGET_MODES` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 58 | `    ("synthetic left turn", 18.0, -5.5),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 59 | `    ("synthetic right turn", 18.0, 5.5),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 60 | `    ("synthetic straight", 24.0, 0.0),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 61 | `]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 62 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 63 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 64 | `def draw_transparent_arrow(pygame, display, pixels):` | 定义 `draw_transparent_arrow` 函数，把一段可复用逻辑封装起来。 |
| 65 | `    """画半透明箭头。"""` | 单行文档字符串，用一句话说明当前函数或代码对象的用途。 |
| 66 | `    if not pixels:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 67 | `        return` | 提前结束当前函数，不返回具体值。 |
| 68 | `    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)` | 给 `overlay` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 69 | `    pygame.draw.polygon(overlay, (255, 170, 20, 115), pixels)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 70 | `    pygame.draw.lines(overlay, (255, 245, 180, 220), True, pixels, 2)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 71 | `    display.blit(overlay, (0, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 72 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 73 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 74 | `def draw_cross(pygame, display, pixel, color):` | 定义 `draw_cross` 函数，把一段可复用逻辑封装起来。 |
| 75 | `    """画检测点十字。"""` | 单行文档字符串，用一句话说明当前函数或代码对象的用途。 |
| 76 | `    x, y = int(pixel[0]), int(pixel[1])` | 给 `x, y` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 77 | `    pygame.draw.line(display, color, (x - 8, y), (x + 8, y), 2)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 78 | `    pygame.draw.line(display, color, (x, y - 8), (x, y + 8), 2)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 79 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 80 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 81 | `def main():` | 定义 `main` 函数，把一段可复用逻辑封装起来。 |
| 82 | `    pygame.init()` | 初始化 pygame 主模块，后续才能创建窗口、读取事件和绘制图像。 |
| 83 | `    pygame.font.init()` | 初始化 pygame 字体模块，后续才能在窗口里渲染 HUD 文本。 |
| 84 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 85 | `    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))` | 创建 pygame 窗口，作为显示 CARLA 相机图像和 AR overlay 的画布。 |
| 86 | `    pygame.display.set_caption("14 stable AR ground arrow")` | 设置 pygame 窗口标题，方便区分当前运行的是哪个 lesson。 |
| 87 | `    font = pygame.font.SysFont("Arial", 18)` | 给 `font` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 88 | `    clock = pygame.time.Clock()` | 给 `clock` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 89 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 90 | `    k = build_camera_intrinsic_k(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)` | 构造相机内参矩阵 K，用于 camera 坐标和像素坐标之间的转换。 |
| 91 | `    client, world = connect_to_carla()` | 连接 CARLA server，并拿到 client 和 world。 |
| 92 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 93 | `    actors = []` | 给 `actors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 94 | `    current_steer = 0.0` | 给 `current_steer` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 95 | `    target_mode_index = 0` | 给 `target_mode_index` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 96 | `    manual_pixel = None` | 给 `manual_pixel` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 97 | `    manual_target_world = None` | 给 `manual_target_world` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 98 | `    target_filter = ExponentialLocationFilter(alpha=0.25)` | 给 `target_filter` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 99 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 100 | `    try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 101 | `        vehicle = spawn_ego_vehicle(world)` | 生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。 |
| 102 | `        actors.append(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 103 | `        camera = CameraSensor(world, vehicle, "sensor.camera.rgb")` | 创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。 |
| 104 | `        actors.append(camera.actor)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 105 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 106 | `        running = True` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 107 | `        while running:` | 循环语句：只要条件成立，就持续执行这个缩进块。 |
| 108 | `            clock.tick(30)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 109 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 110 | `            for event in pygame.event.get():` | 循环语句：依次处理一个序列里的每个元素。 |
| 111 | `                if event.type == pygame.QUIT:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 112 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 113 | `                elif event.type == pygame.KEYUP:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 114 | `                    if event.key == pygame.K_ESCAPE:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 115 | `                        running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 116 | `                    elif event.key == pygame.K_c:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 117 | `                        manual_pixel = None` | 给 `manual_pixel` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 118 | `                        manual_target_world = None` | 给 `manual_target_world` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 119 | `                        target_filter.reset()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 120 | `                    elif event.key == pygame.K_t:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 121 | `                        target_mode_index = (target_mode_index + 1) % len(TARGET_MODES)` | 给 `target_mode_index` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 122 | `                        manual_pixel = None` | 给 `manual_pixel` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 123 | `                        manual_target_world = None` | 给 `manual_target_world` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 124 | `                        target_filter.reset()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 125 | `                    elif event.key == pygame.K_r:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 126 | `                        target_filter.reset()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 127 | `                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 128 | `                    manual_pixel = event.pos` | 读取鼠标事件中的像素坐标，作为手工标注或模拟检测点。 |
| 129 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 130 | `            keys = pygame.key.get_pressed()` | 读取当前键盘按键状态，用于手动驾驶控制。 |
| 131 | `            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)` | 把 pygame 键盘状态转换为 CARLA 车辆控制命令。 |
| 132 | `            vehicle.apply_control(control)` | 把油门、刹车、方向盘等控制量发送给 CARLA 车辆。 |
| 133 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 134 | `            if camera.latest_rgb is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 135 | `                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 136 | `            else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 137 | `                display.fill((10, 10, 10))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 138 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 139 | `            camera_tf = camera.get_transform()` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 140 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 141 | `            # 箭头起点：车辆前方 9 米的地面点。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 142 | `            ahead_world = ground_point_in_vehicle_frame(world, vehicle, 9.0, 0.0)` | 用车辆局部坐标定义一个路面点，并转换成世界坐标。 |
| 143 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 144 | `            # 目标点来源 A：鼠标点击像素，模拟模型检测到路面点。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 145 | `            if manual_pixel is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 146 | `                ground_z = get_ground_z(world, ahead_world) + 0.04` | 给 `ground_z` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 147 | `                manual_target_world = pixel_to_world_on_ground(` | 把图像像素射线与地面平面求交，估计路面点的世界坐标。 |
| 148 | `                    manual_pixel[0],` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 149 | `                    manual_pixel[1],` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 150 | `                    camera_tf,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 151 | `                    k,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 152 | `                    ground_z,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 153 | `                )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 154 | `                raw_target_world = manual_target_world` | 给 `raw_target_world` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 155 | `                target_source = "mouse pixel {}".format(manual_pixel)` | 给 `target_source` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 156 | `                draw_cross(pygame, display, manual_pixel, (255, 60, 60))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 157 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 158 | `            # 目标点来源 B：合成一个目标点，方便不用模型也能观察左转/右转/直行。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 159 | `            else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 160 | `                mode_name, forward_m, right_m = TARGET_MODES[target_mode_index]` | 给 `mode_name, forward_m, right_m` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 161 | `                synthetic_world = ground_point_in_vehicle_frame(world, vehicle, forward_m, right_m)` | 用车辆局部坐标定义一个路面点，并转换成世界坐标。 |
| 162 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 163 | `                # 故意走一遍 world->pixel->ground 的链路，并加一点像素噪声。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 164 | `                # 这样更像真实模型输出：模型通常给你的是像素点，不是世界点。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 165 | `                synthetic_pixel = world_to_pixel(synthetic_world, camera_tf, k, WINDOW_WIDTH, WINDOW_HEIGHT, margin=100.0)` | 把 CARLA 世界坐标点投影到相机图像像素位置。 |
| 166 | `                raw_target_world = None` | 给 `raw_target_world` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 167 | `                if synthetic_pixel is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 168 | `                    u = synthetic_pixel[0] + random.uniform(-3.0, 3.0)` | 给 `u` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 169 | `                    v = synthetic_pixel[1] + random.uniform(-2.0, 2.0)` | 给 `v` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 170 | `                    draw_cross(pygame, display, (u, v), (255, 60, 60))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 171 | `                    ground_z = get_ground_z(world, synthetic_world) + 0.04` | 给 `ground_z` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 172 | `                    raw_target_world = pixel_to_world_on_ground(u, v, camera_tf, k, ground_z)` | 把图像像素射线与地面平面求交，估计路面点的世界坐标。 |
| 173 | `                target_source = mode_name` | 给 `target_source` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 174 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 175 | `            filtered_target = target_filter.update(raw_target_world)` | 给 `filtered_target` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 176 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 177 | `            debug_draw_point(world, ahead_world, carla.Color(0, 255, 0), "ahead")` | 使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。 |
| 178 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 179 | `            if raw_target_world is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 180 | `                debug_draw_point(world, raw_target_world, carla.Color(255, 80, 80), "raw")` | 使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。 |
| 181 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 182 | `            if filtered_target is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 183 | `                debug_draw_point(world, filtered_target, carla.Color(30, 220, 255), "filtered")` | 使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。 |
| 184 | `                debug_draw_arrow(world, ahead_world, filtered_target)` | 使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。 |
| 185 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 186 | `                arrow_world = make_ground_arrow_polygon(ahead_world, filtered_target, width=1.25)` | 根据箭头起点和目标点生成贴地箭头多边形的世界坐标顶点。 |
| 187 | `                arrow_pixels = project_polygon_to_pixels(` | 把箭头多边形的世界坐标顶点批量投影成屏幕像素点。 |
| 188 | `                    arrow_world,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 189 | `                    camera_tf,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 190 | `                    k,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 191 | `                    WINDOW_WIDTH,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 192 | `                    WINDOW_HEIGHT,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 193 | `                    margin=180.0,` | 给 `margin` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 194 | `                )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 195 | `                if arrow_pixels is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 196 | `                    draw_transparent_arrow(pygame, display, arrow_pixels)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 197 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 198 | `                filtered_pixel = world_to_pixel(filtered_target, camera_tf, k, WINDOW_WIDTH, WINDOW_HEIGHT, margin=80.0)` | 把 CARLA 世界坐标点投影到相机图像像素位置。 |
| 199 | `                if filtered_pixel is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 200 | `                    pygame.draw.circle(display, (30, 220, 255), (int(filtered_pixel[0]), int(filtered_pixel[1])), 8, 0)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 201 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 202 | `            lines = [` | 给 `lines` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 203 | `                "Lesson 14 \| stable AR ground arrow \| ESC quit",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 204 | `                "Left click road pixel \| C clear \| T target mode \| R reset filter",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 205 | `                "Target source: {}".format(target_source),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 206 | `                "red = raw detection pixel/world \| cyan = filtered target \| orange = AR arrow",` | 给 `"red` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 207 | `            ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 208 | `            draw_text_lines(pygame, display, font, lines)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 209 | `            pygame.display.flip()` | 刷新 pygame 窗口，把本帧绘制结果真正显示到屏幕上。 |
| 210 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 211 | `    finally:` | 最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。 |
| 212 | `        destroy_actors(actors)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 213 | `        pygame.quit()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 214 | `        print("Cleaned up.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 215 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 216 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 217 | `if __name__ == "__main__":` | Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。 |
| 218 | `    main()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
