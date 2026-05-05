# 12_vehicle_imu_gnss_speed.py 逐行注释

说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。

| 行号 | 代码 | 解释 |
|---:|---|---|
| 1 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 2 | `12_vehicle_imu_gnss_speed.py` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 3 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 4 | `本节目标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 5 | `  1. 读取 vehicle.get_transform()；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 6 | `  2. 读取 vehicle.get_velocity()；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 7 | `  3. 计算 forward speed；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 8 | `  4. 挂载 IMU / GNSS；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 9 | `  5. 在 pygame HUD 里实时显示数据。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 10 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 11 | `为什么这属于“融合层”？` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 12 | `  因为后续 AR overlay 不只依赖图像，还依赖车辆当前位姿、速度、IMU/GNSS。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 13 | `  真正稳定的贴地箭头需要知道：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 14 | `    车在哪里` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 15 | `    车朝哪` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 16 | `    车速多少` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 17 | `    传感器数据是否对齐` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 18 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 19 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 20 | `import math` | 导入 `math` 模块，供后续代码使用其中的函数、类或常量。 |
| 21 | `import weakref` | 导入 `weakref` 模块，供后续代码使用其中的函数、类或常量。 |
| 22 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 23 | `import pygame` | 导入 `pygame` 模块，供后续代码使用其中的函数、类或常量。 |
| 24 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 25 | `from common import CameraSensor` | 从 `common` 导入 `CameraSensor`，避免后面反复写模块前缀。 |
| 26 | `from common import WINDOW_HEIGHT` | 从 `common` 导入 `WINDOW_HEIGHT`，避免后面反复写模块前缀。 |
| 27 | `from common import WINDOW_WIDTH` | 从 `common` 导入 `WINDOW_WIDTH`，避免后面反复写模块前缀。 |
| 28 | `from common import carla` | 从 `common` 导入 `carla`，避免后面反复写模块前缀。 |
| 29 | `from common import connect_to_carla` | 从 `common` 导入 `connect_to_carla`，避免后面反复写模块前缀。 |
| 30 | `from common import destroy_actors` | 从 `common` 导入 `destroy_actors`，避免后面反复写模块前缀。 |
| 31 | `from common import draw_text_lines` | 从 `common` 导入 `draw_text_lines`，避免后面反复写模块前缀。 |
| 32 | `from common import get_forward_speed` | 从 `common` 导入 `get_forward_speed`，避免后面反复写模块前缀。 |
| 33 | `from common import get_keyboard_vehicle_control` | 从 `common` 导入 `get_keyboard_vehicle_control`，避免后面反复写模块前缀。 |
| 34 | `from common import get_planar_speed` | 从 `common` 导入 `get_planar_speed`，避免后面反复写模块前缀。 |
| 35 | `from common import make_pygame_surface` | 从 `common` 导入 `make_pygame_surface`，避免后面反复写模块前缀。 |
| 36 | `from common import spawn_ego_vehicle` | 从 `common` 导入 `spawn_ego_vehicle`，避免后面反复写模块前缀。 |
| 37 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 38 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 39 | `class ImuGnssBundle(object):` | 定义 `ImuGnssBundle` 类，把相关数据和行为组织到一个对象里。 |
| 40 | `    """` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 41 | `    管理 IMU 和 GNSS。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 42 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 43 | `    这里仍然使用 sensor.listen 的异步回调。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 44 | `    对入门显示和手动驾驶足够。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 45 | `    后续严谨实验可以转到 synchronous mode。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 46 | `    """` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 47 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 48 | `    def __init__(self, world, vehicle):` | 定义 `__init__` 函数，把一段可复用逻辑封装起来。 |
| 49 | `        self.latest_imu = None` | 给 `self.latest_imu` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 50 | `        self.latest_gnss = None` | 给 `self.latest_gnss` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 51 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 52 | `        bp_lib = world.get_blueprint_library()` | 读取 blueprint 库，后续用它选择车辆和传感器模板。 |
| 53 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 54 | `        imu_bp = bp_lib.find("sensor.other.imu")` | 给 `imu_bp` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 55 | `        imu_bp.set_attribute("sensor_tick", "0.05")` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 56 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 57 | `        gnss_bp = bp_lib.find("sensor.other.gnss")` | 给 `gnss_bp` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 58 | `        gnss_bp.set_attribute("sensor_tick", "0.10")` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 59 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 60 | `        self.imu = world.spawn_actor(` | 在 CARLA 世界中根据 blueprint 和 transform 生成一个真实 actor。 |
| 61 | `            imu_bp,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 62 | `            carla.Transform(carla.Location(x=0.0, y=0.0, z=0.0)),` | 给 `carla.Transform(carla.Location(x` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 63 | `            attach_to=vehicle,` | 给 `attach_to` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 64 | `        )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 65 | `        self.gnss = world.spawn_actor(` | 在 CARLA 世界中根据 blueprint 和 transform 生成一个真实 actor。 |
| 66 | `            gnss_bp,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 67 | `            carla.Transform(carla.Location(x=0.0, y=0.0, z=0.0)),` | 给 `carla.Transform(carla.Location(x` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 68 | `            attach_to=vehicle,` | 给 `attach_to` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 69 | `        )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 70 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 71 | `        weak_self = weakref.ref(self)` | 给 `weak_self` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 72 | `        self.imu.listen(lambda data: ImuGnssBundle._on_imu(weak_self, data))` | 注册 CARLA 传感器回调函数；每次传感器产生新数据时会自动调用。 |
| 73 | `        self.gnss.listen(lambda data: ImuGnssBundle._on_gnss(weak_self, data))` | 注册 CARLA 传感器回调函数；每次传感器产生新数据时会自动调用。 |
| 74 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 75 | `    @staticmethod` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 76 | `    def _on_imu(weak_self, data):` | 定义 `_on_imu` 函数，把一段可复用逻辑封装起来。 |
| 77 | `        self = weak_self()` | 给 `self` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 78 | `        if self is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 79 | `            self.latest_imu = data` | 给 `self.latest_imu` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 80 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 81 | `    @staticmethod` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 82 | `    def _on_gnss(weak_self, data):` | 定义 `_on_gnss` 函数，把一段可复用逻辑封装起来。 |
| 83 | `        self = weak_self()` | 给 `self` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 84 | `        if self is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 85 | `            self.latest_gnss = data` | 给 `self.latest_gnss` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 86 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 87 | `    def actors(self):` | 定义 `actors` 函数，把一段可复用逻辑封装起来。 |
| 88 | `        return [self.imu, self.gnss]` | 返回当前函数的计算结果，调用者会拿到这个值继续使用。 |
| 89 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 90 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 91 | `def main():` | 定义 `main` 函数，把一段可复用逻辑封装起来。 |
| 92 | `    pygame.init()` | 初始化 pygame 主模块，后续才能创建窗口、读取事件和绘制图像。 |
| 93 | `    pygame.font.init()` | 初始化 pygame 字体模块，后续才能在窗口里渲染 HUD 文本。 |
| 94 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 95 | `    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))` | 创建 pygame 窗口，作为显示 CARLA 相机图像和 AR overlay 的画布。 |
| 96 | `    pygame.display.set_caption("12 vehicle IMU GNSS speed")` | 设置 pygame 窗口标题，方便区分当前运行的是哪个 lesson。 |
| 97 | `    font = pygame.font.SysFont("Arial", 18)` | 给 `font` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 98 | `    clock = pygame.time.Clock()` | 给 `clock` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 99 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 100 | `    client, world = connect_to_carla()` | 连接 CARLA server，并拿到 client 和 world。 |
| 101 | `    actors = []` | 给 `actors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 102 | `    current_steer = 0.0` | 给 `current_steer` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 103 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 104 | `    try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 105 | `        vehicle = spawn_ego_vehicle(world)` | 生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。 |
| 106 | `        actors.append(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 107 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 108 | `        camera = CameraSensor(world, vehicle, "sensor.camera.rgb")` | 创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。 |
| 109 | `        actors.append(camera.actor)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 110 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 111 | `        sensors = ImuGnssBundle(world, vehicle)` | 给 `sensors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 112 | `        actors.extend(sensors.actors())` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 113 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 114 | `        running = True` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 115 | `        while running:` | 循环语句：只要条件成立，就持续执行这个缩进块。 |
| 116 | `            clock.tick(30)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 117 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 118 | `            for event in pygame.event.get():` | 循环语句：依次处理一个序列里的每个元素。 |
| 119 | `                if event.type == pygame.QUIT:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 120 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 121 | `                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:` | 上一条 `if` 不成立时，继续检查这个备选条件。 |
| 122 | `                    running = False` | 给 `running` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 123 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 124 | `            keys = pygame.key.get_pressed()` | 读取当前键盘按键状态，用于手动驾驶控制。 |
| 125 | `            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)` | 把 pygame 键盘状态转换为 CARLA 车辆控制命令。 |
| 126 | `            vehicle.apply_control(control)` | 把油门、刹车、方向盘等控制量发送给 CARLA 车辆。 |
| 127 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 128 | `            if camera.latest_rgb is not None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 129 | `                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 130 | `            else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 131 | `                display.fill((10, 10, 10))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 132 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 133 | `            transform = vehicle.get_transform()` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 134 | `            location = transform.location` | 给 `location` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 135 | `            rotation = transform.rotation` | 给 `rotation` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 136 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 137 | `            lines = [` | 给 `lines` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 138 | `                "Lesson 12 \| vehicle transform + speed + IMU/GNSS \| ESC quit",` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 139 | `                "Control throttle={:.2f} brake={:.2f} steer={:.2f} reverse={}".format(` | 给 `"Control throttle` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 140 | `                    control.throttle, control.brake, control.steer, control.reverse` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 141 | `                ),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 142 | `                "Vehicle loc x={:.2f} y={:.2f} z={:.2f}".format(location.x, location.y, location.z),` | 给 `"Vehicle loc x` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 143 | `                "Vehicle rot pitch={:.2f} yaw={:.2f} roll={:.2f}".format(` | 给 `"Vehicle rot pitch` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 144 | `                    rotation.pitch, rotation.yaw, rotation.roll` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 145 | `                ),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 146 | `                "Speed forward={:.2f} m/s planar={:.2f} m/s".format(` | 给 `"Speed forward` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 147 | `                    get_forward_speed(vehicle), get_planar_speed(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 148 | `                ),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 149 | `            ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 150 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 151 | `            imu = sensors.latest_imu` | 给 `imu` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 152 | `            if imu is None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 153 | `                lines.append("IMU: waiting...")` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 154 | `            else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 155 | `                lines.append("IMU accel x={:.3f} y={:.3f} z={:.3f}".format(` | 给 `lines.append("IMU accel x` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 156 | `                    imu.accelerometer.x, imu.accelerometer.y, imu.accelerometer.z` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 157 | `                ))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 158 | `                lines.append("IMU gyro  x={:.3f} y={:.3f} z={:.3f} \| compass {:.2f}deg".format(` | 给 `lines.append("IMU gyro  x` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 159 | `                    imu.gyroscope.x, imu.gyroscope.y, imu.gyroscope.z,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 160 | `                    math.degrees(imu.compass),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 161 | `                ))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 162 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 163 | `            gnss = sensors.latest_gnss` | 给 `gnss` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 164 | `            if gnss is None:` | 条件判断：只有条件成立时，才执行这个缩进块里的代码。 |
| 165 | `                lines.append("GNSS: waiting...")` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 166 | `            else:` | 当前面条件都不成立时，执行这个兜底分支。 |
| 167 | `                lines.append("GNSS lat={:.8f} lon={:.8f} alt={:.2f}".format(` | 给 `lines.append("GNSS lat` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 168 | `                    gnss.latitude, gnss.longitude, gnss.altitude` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 169 | `                ))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 170 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 171 | `            draw_text_lines(pygame, display, font, lines)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 172 | `            pygame.display.flip()` | 刷新 pygame 窗口，把本帧绘制结果真正显示到屏幕上。 |
| 173 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 174 | `    finally:` | 最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。 |
| 175 | `        destroy_actors(actors)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 176 | `        pygame.quit()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 177 | `        print("Cleaned up.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 178 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 179 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 180 | `if __name__ == "__main__":` | Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。 |
| 181 | `    main()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
