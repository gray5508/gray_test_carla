# 13_trajectory_estimation_basic.py 逐行注释

说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。

| 行号 | 代码 | 解释 |
|---:|---|---|
| 1 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 2 | `13_trajectory_estimation_basic.py` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 3 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 4 | `本节目标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 5 | `  1. 用 CARLA ground truth 记录真实轨迹；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 6 | `  2. 用 forward speed + yaw 做最基础轨迹积分；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 7 | `  3. 保存 CSV；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 8 | `  4. 理解轨迹估计为什么会漂。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 9 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 10 | `这一节故意不用复杂 EKF，只用最基础公式：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 11 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 12 | `  x = x + speed * cos(yaw) * dt` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 13 | `  y = y + speed * sin(yaw) * dt` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 14 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 15 | `其中：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 16 | `  speed 来自车辆前向速度` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 17 | `  yaw 来自车辆当前 ground truth yaw` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 18 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 19 | `这不是完整定位算法，只是帮助你理解：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 20 | `  坐标、速度、角度、dt 是怎么共同决定轨迹的。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 21 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 22 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 23 | `import csv` | 导入 `csv` 模块，供后续代码使用其中的函数、类或常量。 |
| 24 | `import math` | 导入 `math` 模块，供后续代码使用其中的函数、类或常量。 |
| 25 | `import os` | 导入 `os` 模块，供后续代码使用其中的函数、类或常量。 |
| 26 | `import time` | 导入 `time` 模块，供后续代码使用其中的函数、类或常量。 |
| 27 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 28 | `import pygame` | 导入 `pygame` 模块，供后续代码使用其中的函数、类或常量。 |
| 29 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 30 | `from common import CameraSensor` | 从 `common` 导入 `CameraSensor`，避免后面反复写模块前缀。 |
| 31 | `from common import WINDOW_HEIGHT` | 从 `common` 导入 `WINDOW_HEIGHT`，避免后面反复写模块前缀。 |
| 32 | `from common import WINDOW_WIDTH` | 从 `common` 导入 `WINDOW_WIDTH`，避免后面反复写模块前缀。 |
| 33 | `from common import connect_to_carla` | 从 `common` 导入 `connect_to_carla`，避免后面反复写模块前缀。 |
| 34 | `from common import destroy_actors` | 从 `common` 导入 `destroy_actors`，避免后面反复写模块前缀。 |
| 35 | `from common import draw_text_lines` | 从 `common` 导入 `draw_text_lines`，避免后面反复写模块前缀。 |
| 36 | `from common import get_forward_speed` | 从 `common` 导入 `get_forward_speed`，避免后面反复写模块前缀。 |
| 37 | `from common import get_keyboard_vehicle_control` | 从 `common` 导入 `get_keyboard_vehicle_control`，避免后面反复写模块前缀。 |
| 38 | `from common import make_pygame_surface` | 从 `common` 导入 `make_pygame_surface`，避免后面反复写模块前缀。 |
| 39 | `from common import spawn_ego_vehicle` | 从 `common` 导入 `spawn_ego_vehicle`，避免后面反复写模块前缀。 |
| 40 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 41 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 42 | `class BasicTrajectoryEstimator(object):` | 定义 `BasicTrajectoryEstimator` 类，把相关数据和行为组织到一个对象里。 |
| 43 | `    """` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 44 | `    一个最小轨迹积分器。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 45 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 46 | `    初始化时把估计位置设为车辆真实位置。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 47 | `    每帧根据速度、yaw、dt 往前积分。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 48 | `    """` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 49 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 50 | `    def __init__(self):` | 定义 `__init__` 函数，把一段可复用逻辑封装起来。 |
| 51 | `        self.initialized = False` | 给 `self.initialized` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 52 | `        self.last_time = None` | 给 `self.last_time` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 53 | `        self.est_x = 0.0` | 给 `self.est_x` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 54 | `        self.est_y = 0.0` | 给 `self.est_y` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 55 | `        self.records = []` | 给 `self.records` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 56 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 57 | `    def update(self, vehicle):` | 定义 `update` 函数，把一段可复用逻辑封装起来。 |
| 58 | `        now = time.time()` | 给 `now` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 59 | `        transform = vehicle.get_transform()` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 60 | `        loc = transform.location` | 给 `loc` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 61 | `        yaw_rad = math.radians(transform.rotation.yaw)` | 使用数学函数计算角度、三角函数、距离或归一化结果。 |
| 62 | `        speed = get_forward_speed(vehicle)` | 给 `speed` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 63 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 64 | `        if not self.initialized:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 65 | `            self.initialized = True` | 给 `self.initialized` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 66 | `            self.last_time = now` | 给 `self.last_time` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 67 | `            self.est_x = loc.x` | 给 `self.est_x` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 68 | `            self.est_y = loc.y` | 给 `self.est_y` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 69 | `            return` | 提前结束当前函数，不返回具体值。 |
| 70 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 71 | `        dt = now - self.last_time` | 给 `dt` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 72 | `        self.last_time = now` | 给 `self.last_time` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 73 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 74 | `        # 防止窗口卡顿时 dt 过大，导致一次积分跳很远。` | 普通注释，解释下面代码块的目的、背景或注意事项。 |
| 75 | `        if dt > 0.2:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 76 | `            dt = 0.2` | 给 `dt` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 77 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 78 | `        self.est_x += speed * math.cos(yaw_rad) * dt` | 使用数学函数计算角度、三角函数、距离或归一化结果。 |
| 79 | `        self.est_y += speed * math.sin(yaw_rad) * dt` | 使用数学函数计算角度、三角函数、距离或归一化结果。 |
| 80 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 81 | `        error = math.sqrt((self.est_x - loc.x) ** 2 + (self.est_y - loc.y) ** 2)` | 使用数学函数计算角度、三角函数、距离或归一化结果。 |
| 82 | `        self.records.append({` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 83 | `            "time": now,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 84 | `            "dt": dt,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 85 | `            "gt_x": loc.x,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 86 | `            "gt_y": loc.y,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 87 | `            "yaw_deg": transform.rotation.yaw,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 88 | `            "forward_speed_mps": speed,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 89 | `            "est_x": self.est_x,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 90 | `            "est_y": self.est_y,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 91 | `            "error_m": error,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 92 | `        })` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 93 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 94 | `    def save_csv(self):` | 定义 `save_csv` 函数，把一段可复用逻辑封装起来。 |
| 95 | `        output_dir = os.path.join(os.path.dirname(__file__), "outputs")` | 给 `output_dir` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 96 | `        if not os.path.isdir(output_dir):` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 97 | `            os.makedirs(output_dir)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 98 | `        output_path = os.path.join(output_dir, "basic_trajectory_estimation.csv")` | 给 `output_path` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 99 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 100 | `        if not self.records:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 101 | `            print("No trajectory records to save.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 102 | `            return output_path` | 返回当前函数的计算结果，调用者会拿到这个值继续使用。 |
| 103 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 104 | `        fieldnames = [` | 给 `fieldnames` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 105 | `            "time", "dt", "gt_x", "gt_y", "yaw_deg",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 106 | `            "forward_speed_mps", "est_x", "est_y", "error_m",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 107 | `        ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 108 | `        with open(output_path, "w", newline="") as f:` | 上下文管理语句：自动管理资源打开和关闭，例如文件写入。 |
| 109 | `            writer = csv.DictWriter(f, fieldnames=fieldnames)` | 给 `writer` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 110 | `            writer.writeheader()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 111 | `            writer.writerows(self.records)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 112 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 113 | `        print("Saved:", output_path)` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 114 | `        return output_path` | 返回当前函数的计算结果，调用者会拿到这个值继续使用。 |
| 115 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 116 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 117 | `def main():` | 定义 `main` 函数，把一段可复用逻辑封装起来。 |
| 118 | `    pygame.init()` | 初始化 pygame 主模块，后续才能创建窗口、读取事件和绘制图像。 |
| 119 | `    pygame.font.init()` | 初始化 pygame 字体模块，后续才能在窗口里渲染 HUD 文本。 |
| 120 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 121 | `    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))` | 创建 pygame 窗口，作为显示 CARLA 相机图像和 AR overlay 的画布。 |
| 122 | `    pygame.display.set_caption("13 basic trajectory estimation")` | 设置 pygame 窗口标题，方便区分当前运行的是哪个 lesson。 |
| 123 | `    font = pygame.font.SysFont("Arial", 18)` | 给 `font` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 124 | `    clock = pygame.time.Clock()` | 给 `clock` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 125 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 126 | `    client, world = connect_to_carla()` | 连接 CARLA server，并拿到 client 和 world。 |
| 127 | `    actors = []` | 给 `actors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 128 | `    current_steer = 0.0` | 给 `current_steer` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 129 | `    estimator = BasicTrajectoryEstimator()` | 给 `estimator` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 130 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 131 | `    try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 132 | `        vehicle = spawn_ego_vehicle(world)` | 生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。 |
| 133 | `        actors.append(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 134 | `        camera = CameraSensor(world, vehicle, "sensor.camera.rgb")` | 创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。 |
| 135 | `        actors.append(camera.actor)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 136 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 137 | `        running = True` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 138 | `        while running:` | 循环语句：只要条件成立，就持续执行这个缩进块。 |
| 139 | `            clock.tick(30)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 140 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 141 | `            for event in pygame.event.get():` | 循环语句：依次处理一个序列里的每个元素。 |
| 142 | `                if event.type == pygame.QUIT:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 143 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 144 | `                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 145 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 146 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 147 | `            keys = pygame.key.get_pressed()` | 读取当前键盘按键状态，用于手动驾驶控制。 |
| 148 | `            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)` | 把 pygame 键盘状态转换为 CARLA 车辆控制命令。 |
| 149 | `            vehicle.apply_control(control)` | 把油门、刹车、方向盘等控制量发送给 CARLA 车辆。 |
| 150 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 151 | `            estimator.update(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 152 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 153 | `            if camera.latest_rgb is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 154 | `                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 155 | `            else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 156 | `                display.fill((10, 10, 10))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 157 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 158 | `            transform = vehicle.get_transform()` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 159 | `            loc = transform.location` | 给 `loc` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 160 | `            last_error = estimator.records[-1]["error_m"] if estimator.records else 0.0` | 给 `last_error` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 161 | `            lines = [` | 给 `lines` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 162 | `                "Lesson 13 \| basic trajectory estimation \| ESC save and quit",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 163 | `                "GT x={:.2f} y={:.2f} yaw={:.2f}".format(loc.x, loc.y, transform.rotation.yaw),` | 给 `"GT x` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 164 | `                "EST x={:.2f} y={:.2f} \| error {:.2f}m".format(` | 给 `"EST x` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 165 | `                    estimator.est_x, estimator.est_y, last_error` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 166 | `                ),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 167 | `                "Records: {}".format(len(estimator.records)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 168 | `                "This uses ground-truth yaw. Later you can replace yaw with IMU gyro integration.",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 169 | `            ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 170 | `            draw_text_lines(pygame, display, font, lines)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 171 | `            pygame.display.flip()` | 刷新 pygame 窗口，把本帧绘制结果真正显示到屏幕上。 |
| 172 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 173 | `    finally:` | 最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。 |
| 174 | `        estimator.save_csv()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 175 | `        destroy_actors(actors)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 176 | `        pygame.quit()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 177 | `        print("Cleaned up.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 178 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 179 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 180 | `if __name__ == "__main__":` | Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。 |
| 181 | `    main()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
