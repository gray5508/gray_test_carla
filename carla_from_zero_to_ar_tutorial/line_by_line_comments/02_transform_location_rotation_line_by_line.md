# 02_transform_location_rotation.py 逐行注释

说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。

| 行号 | 代码 | 解释 |
|---:|---|---|
| 1 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 2 | `02_transform_location_rotation.py` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 3 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 4 | `本节目标：` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 5 | `  1. 理解 Transform = Location + Rotation；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 6 | `  2. 理解 Location 的 x/y/z；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 7 | `  3. 理解 Rotation 的 pitch/yaw/roll；` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 8 | `  4. 改变车辆 yaw，观察 forward vector 怎么变化。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 9 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 10 | `Location:` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 11 | `  x/y/z 是 CARLA 世界坐标，单位通常是米。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 12 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 13 | `Rotation:` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 14 | `  yaw   ：绕 z 轴转，决定车头朝向。平面行驶最常用。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 15 | `  pitch ：绕 y 轴转，车头抬起/低下。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 16 | `  roll  ：绕 x 轴转，车辆左右倾斜。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 17 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 18 | `Transform:` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 19 | `  同时包含位置和姿态。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 20 | `"""` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 21 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 22 | `import math` | 导入 `math` 模块，供后续代码使用其中的函数、类或常量。 |
| 23 | `import time` | 导入 `time` 模块，供后续代码使用其中的函数、类或常量。 |
| 24 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 25 | `from common import carla` | 从 `common` 导入 `carla`，避免后面反复写模块前缀。 |
| 26 | `from common import connect_to_carla` | 从 `common` 导入 `connect_to_carla`，避免后面反复写模块前缀。 |
| 27 | `from common import destroy_actors` | 从 `common` 导入 `destroy_actors`，避免后面反复写模块前缀。 |
| 28 | `from common import print_transform_details` | 从 `common` 导入 `print_transform_details`，避免后面反复写模块前缀。 |
| 29 | `from common import spawn_ego_vehicle` | 从 `common` 导入 `spawn_ego_vehicle`，避免后面反复写模块前缀。 |
| 30 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 31 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 32 | `def print_forward_from_yaw(transform):` | 定义 `print_forward_from_yaw` 函数，把一段可复用逻辑封装起来。 |
| 33 | `    """` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 34 | `    CARLA 里 transform.get_forward_vector() 应该和 yaw 的 cos/sin 对齐。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 35 | `    这对后续轨迹积分和“车辆前方点”计算都很重要。` | 文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。 |
| 36 | `    """` | 文档字符串边界，开始或结束本文件/函数/类的说明文字。 |
| 37 | `    forward = transform.get_forward_vector()` | 读取 actor 局部 +X 轴在世界坐标中的方向，车辆上通常就是车头方向。 |
| 38 | `    yaw_rad = math.radians(transform.rotation.yaw)` | 使用数学函数计算角度、三角函数、距离或归一化结果。 |
| 39 | `    print("  forward vector      = ({:.4f}, {:.4f}, {:.4f})".format(` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 40 | `        forward.x, forward.y, forward.z` | 当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。 |
| 41 | `    ))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 42 | `    print("  cos(yaw), sin(yaw)  = ({:.4f}, {:.4f})".format(` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 43 | `        math.cos(yaw_rad), math.sin(yaw_rad)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 44 | `    ))` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 45 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 46 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 47 | `def main():` | 定义 `main` 函数，把一段可复用逻辑封装起来。 |
| 48 | `    client, world = connect_to_carla()` | 连接 CARLA server，并拿到 client 和 world。 |
| 49 | `    actors = []` | 给 `actors` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 50 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 51 | `    try:` | 异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。 |
| 52 | `        vehicle = spawn_ego_vehicle(world)` | 生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。 |
| 53 | `        actors.append(vehicle)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 54 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 55 | `        original_transform = vehicle.get_transform()` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 56 | `        print_transform_details("Original vehicle", original_transform)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 57 | `        print_forward_from_yaw(original_transform)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 58 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 59 | `        print("\\n现在每 2 秒改变一次 yaw，观察 forward vector。")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 60 | `        base_location = original_transform.location` | 给 `base_location` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 61 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 62 | `        for yaw in [180.0, 135.0, 90.0, 45.0, 0.0, -45.0]:` | 循环语句：依次处理一个序列里的每个元素。 |
| 63 | `            new_transform = carla.Transform(` | 给 `new_transform` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 64 | `                carla.Location(base_location.x, base_location.y, base_location.z),` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 65 | `                carla.Rotation(pitch=0.0, yaw=yaw, roll=0.0),` | 给 `carla.Rotation(pitch` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。 |
| 66 | `            )` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 67 | `            vehicle.set_transform(new_transform)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 68 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 69 | `            print("\\nSet yaw = {:.1f} deg".format(yaw))` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 70 | `            print_transform_details("Vehicle", vehicle.get_transform())` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 71 | `            print_forward_from_yaw(vehicle.get_transform())` | 读取 actor 当前 Transform，也就是世界坐标位置和姿态。 |
| 72 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 73 | `            time.sleep(2.0)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 74 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 75 | `    finally:` | 最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。 |
| 76 | `        destroy_actors(actors)` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
| 77 | `        print("Cleaned up.")` | 向终端打印信息，帮助你观察程序当前状态或调试变量。 |
| 78 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 79 | ` ` | 空行，用来把代码分成更容易阅读的逻辑段落。 |
| 80 | `if __name__ == "__main__":` | Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。 |
| 81 | `    main()` | 函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。 |
