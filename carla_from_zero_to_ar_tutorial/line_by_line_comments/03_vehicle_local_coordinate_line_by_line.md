# 03_vehicle_local_coordinate.py 逐行注释

说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。

| 行号 | 代码 | 解释 |
|---:|---|---|
| 1 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 2 | `03_vehicle_local_coordinate.py` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 3 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 4 | `本节目标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 5 | `  1. 理解车辆局部坐标；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 6 | `  2. 把“车辆前方/左侧/右侧”的点转换到 CARLA world；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 7 | `  3. 用 world.debug.draw_point/draw_arrow 在 CARLA 世界里可视化。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 8 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 9 | `车辆局部坐标非常重要，因为你后面会频繁表达：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 10 | `  车前方 10 米` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 11 | `  车左侧 2 米` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 12 | `  相机挂在车头前方 1.25 米、左侧 0.35 米、高 1.35 米` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 13 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 14 | `CARLA 车辆局部坐标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 15 | `  +X：车头方向` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 16 | `  +Y：车辆右侧` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 17 | `  +Z：车辆上方` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 18 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 19 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 20 | `import time` | 导入 `time` 模块，供后续代码使用其中的函数、类或常量。 |
| 21 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 22 | `from common import carla` | 从 `common` 导入 `carla`，避免后面反复写模块前缀。 |
| 23 | `from common import connect_to_carla` | 从 `common` 导入 `connect_to_carla`，避免后面反复写模块前缀。 |
| 24 | `from common import debug_draw_point` | 从 `common` 导入 `debug_draw_point`，避免后面反复写模块前缀。 |
| 25 | `from common import destroy_actors` | 从 `common` 导入 `destroy_actors`，避免后面反复写模块前缀。 |
| 26 | `from common import ground_point_in_vehicle_frame` | 从 `common` 导入 `ground_point_in_vehicle_frame`，避免后面反复写模块前缀。 |
| 27 | `from common import print_vehicle_local_axes` | 从 `common` 导入 `print_vehicle_local_axes`，避免后面反复写模块前缀。 |
| 28 | `from common import spawn_ego_vehicle` | 从 `common` 导入 `spawn_ego_vehicle`，避免后面反复写模块前缀。 |
| 29 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 30 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 31 | `def draw_vehicle_axes(world, vehicle, life_time=0.12):` | 定义 `draw_vehicle_axes` 函数，把一段可复用逻辑封装起来。 |
| 32 | `    """在 CARLA 世界里画出车辆局部 +X/+Y/+Z 轴。"""` | 单行文档字符串，用一句话说明当前函数或代码对象的用途。 |
| 33 | `    transform = vehicle.get_transform()` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 34 | `    origin = transform.location` | 给 `origin` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 35 | `    forward = transform.get_forward_vector()` | 读取 actor 局部 +X 轴在世界坐标中的方向，车辆上通常就是车头方向。 |
| 36 | `    right = transform.get_right_vector()` | 给 `right` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 37 | `    up = transform.get_up_vector()` | 给 `up` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 38 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 39 | `    def add_vector(vector, scale):` | 定义 `add_vector` 函数，把一段可复用逻辑封装起来。 |
| 40 | `        return carla.Location(` | 返回当前函数的计算结果，调用者会拿到这个值继续使用。 |
| 41 | `            origin.x + vector.x * scale,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 42 | `            origin.y + vector.y * scale,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 43 | `            origin.z + vector.z * scale,` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 44 | `        )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 45 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 46 | `    world.debug.draw_arrow(` | 使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。 |
| 47 | `        origin, add_vector(forward, 5.0),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 48 | `        thickness=0.08, arrow_size=0.6,` | 给 `thickness` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 49 | `        color=carla.Color(255, 0, 0), life_time=life_time,` | 给 `color` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 50 | `    )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 51 | `    world.debug.draw_arrow(` | 使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。 |
| 52 | `        origin, add_vector(right, 3.0),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 53 | `        thickness=0.08, arrow_size=0.6,` | 给 `thickness` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 54 | `        color=carla.Color(0, 255, 0), life_time=life_time,` | 给 `color` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 55 | `    )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 56 | `    world.debug.draw_arrow(` | 使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。 |
| 57 | `        origin, add_vector(up, 2.5),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 58 | `        thickness=0.08, arrow_size=0.6,` | 给 `thickness` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 59 | `        color=carla.Color(0, 80, 255), life_time=life_time,` | 给 `color` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 60 | `    )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 61 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 62 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 63 | `def main():` | 定义 `main` 函数，把一段可复用逻辑封装起来。 |
| 64 | `    client, world = connect_to_carla()` | 连接 CARLA server，并拿到 client 和 world。 |
| 65 | `    actors = []` | 给 `actors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 66 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 67 | `    try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 68 | `        vehicle = spawn_ego_vehicle(world)` | 生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。 |
| 69 | `        actors.append(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 70 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 71 | `        print_vehicle_local_axes(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 72 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 73 | `        samples = [` | 给 `samples` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 74 | `            ("front 8m", 8.0, 0.0, carla.Color(255, 255, 0)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 75 | `            ("front 12m", 12.0, 0.0, carla.Color(255, 160, 0)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 76 | `            ("left", 10.0, -2.5, carla.Color(0, 220, 255)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 77 | `            ("right", 10.0, 2.5, carla.Color(255, 0, 255)),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 78 | `        ]` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 79 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 80 | `        print("\\nLocal point -> world point:")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 81 | `        for name, forward_m, right_m, color in samples:` | 循环语句：依次处理一个序列里的每个元素。 |
| 82 | `            point = ground_point_in_vehicle_frame(world, vehicle, forward_m, right_m)` | 用车辆局部坐标定义一个路面点，并转换成世界坐标。 |
| 83 | `            print("  {:10s} local(x={:.1f}, y={:.1f}) -> world({:.3f}, {:.3f}, {:.3f})".format(` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 84 | `                name, forward_m, right_m, point.x, point.y, point.z` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 85 | `            ))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 86 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 87 | `        print("\\nCARLA 窗口里观察 15 秒。红色轴是车头 +X，绿色轴是右侧 +Y。")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 88 | `        end_time = time.time() + 15.0` | 给 `end_time` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 89 | `        while time.time() < end_time:` | 循环语句：只要条件成立，就持续执行这个缩进块。 |
| 90 | `            draw_vehicle_axes(world, vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 91 | `            for name, forward_m, right_m, color in samples:` | 循环语句：依次处理一个序列里的每个元素。 |
| 92 | `                point = ground_point_in_vehicle_frame(world, vehicle, forward_m, right_m)` | 用车辆局部坐标定义一个路面点，并转换成世界坐标。 |
| 93 | `                debug_draw_point(world, point, color, name)` | 使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。 |
| 94 | `            time.sleep(0.05)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 95 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 96 | `    finally:` | 最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。 |
| 97 | `        destroy_actors(actors)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 98 | `        print("Cleaned up.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 99 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 100 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 101 | `if __name__ == "__main__":` | Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。 |
| 102 | `    main()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
