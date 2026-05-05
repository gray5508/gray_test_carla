"""
generate_line_by_line_comments.py

把本教程目录下每个 .py 文件生成一份逐行注释版 Markdown。

说明：
  这个脚本是辅助生成讲义用的，不是 CARLA lesson。
  它不会改动原始 lesson 代码，只会写入 line_by_line_comments/*.md。
"""

import os
import re


ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT, "line_by_line_comments")

SKIP_FILES = set()


def escape_markdown_cell(text):
    """让代码可以安全放进 Markdown 表格。"""
    if text == "":
        return "` `"
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("`", "\\`")
    return "`{}`".format(text)


def split_assignment(line):
    """粗略拆分赋值语句，避开 ==、>=、<=、!=。"""
    if "=" not in line:
        return None
    if any(op in line for op in ["==", ">=", "<=", "!="]):
        return None
    left, right = line.split("=", 1)
    return left.strip(), right.strip()


def comment_for_line(raw_line, context):
    """
    根据一行代码生成中文解释。

    这不是替代人工理解的“魔法注释器”，而是教学讲义生成器：
    它会尽量解释语法动作、CARLA/pygame/几何含义和变量用途。
    """
    line = raw_line.rstrip("\n")
    stripped = line.strip()
    indent = len(line) - len(line.lstrip(" "))

    if stripped == "":
        return "空行，用来把代码分成更容易阅读的逻辑段落。"

    triple = None
    if stripped.startswith('"""'):
        triple = '"""'
    elif stripped.startswith("'''"):
        triple = "'''"

    if triple is not None:
        # 单行 docstring，例如："""简单等待。"""
        # 这种行既开始又结束，不能改变 in_docstring 状态。
        if stripped.count(triple) >= 2 and len(stripped) > len(triple):
            return "单行文档字符串，用一句话说明当前函数或代码对象的用途。"
        context["in_docstring"] = not context.get("in_docstring", False)
        return "文档字符串边界，开始或结束本文件/函数/类的说明文字。"

    if context.get("in_docstring"):
        return "文档字符串内容，用自然语言解释当前文件、函数或类的目标和使用方式。"

    if stripped.startswith("#"):
        return "普通注释，解释下面代码块的目的、背景或注意事项。"

    if stripped.startswith("import "):
        module = stripped.replace("import ", "", 1).strip()
        return "导入 `{}` 模块，供后续代码使用其中的函数、类或常量。".format(module)

    if stripped.startswith("from "):
        match = re.match(r"from\s+([\w\.]+)\s+import\s+(.+)", stripped)
        if match:
            module, names = match.groups()
            return "从 `{}` 导入 `{}`，避免后面反复写模块前缀。".format(module, names)
        return "从某个模块导入需要使用的名称。"

    if stripped.startswith("class "):
        name = stripped.split("class ", 1)[1].split("(", 1)[0].split(":", 1)[0]
        return "定义 `{}` 类，把相关数据和行为组织到一个对象里。".format(name)

    if stripped.startswith("def "):
        name = stripped.split("def ", 1)[1].split("(", 1)[0]
        return "定义 `{}` 函数，把一段可复用逻辑封装起来。".format(name)

    if stripped.startswith("return "):
        return "返回当前函数的计算结果，调用者会拿到这个值继续使用。"

    if stripped == "return":
        return "提前结束当前函数，不返回具体值。"

    if stripped.startswith("if __name__"):
        return "Python 脚本入口判断：只有直接运行本文件时，下面的 `main()` 才会执行。"

    if stripped.startswith("if "):
        return "条件判断：只有条件成立时，才执行这个缩进块里的代码。"

    if stripped.startswith("elif "):
        return "上一条 `if` 不成立时，继续检查这个备选条件。"

    if stripped.startswith("else:"):
        return "当前面条件都不成立时，执行这个兜底分支。"

    if stripped.startswith("for "):
        return "循环语句：依次处理一个序列里的每个元素。"

    if stripped.startswith("while "):
        return "循环语句：只要条件成立，就持续执行这个缩进块。"

    if stripped.startswith("try:"):
        return "异常处理开始：尝试执行可能失败的代码，方便后面统一清理或报错。"

    if stripped.startswith("except "):
        return "异常捕获分支：当前面 `try` 中出现指定错误时执行。"

    if stripped.startswith("finally:"):
        return "最终清理分支：无论是否出错都会执行，常用于销毁 CARLA actor 和退出 pygame。"

    if stripped.startswith("with "):
        return "上下文管理语句：自动管理资源打开和关闭，例如文件写入。"

    if stripped.startswith("print("):
        return "向终端打印信息，帮助你观察程序当前状态或调试变量。"

    if stripped.startswith("pygame.init"):
        return "初始化 pygame 主模块，后续才能创建窗口、读取事件和绘制图像。"

    if stripped.startswith("pygame.font.init"):
        return "初始化 pygame 字体模块，后续才能在窗口里渲染 HUD 文本。"

    if "pygame.display.set_mode" in stripped:
        return "创建 pygame 窗口，作为显示 CARLA 相机图像和 AR overlay 的画布。"

    if "pygame.display.set_caption" in stripped:
        return "设置 pygame 窗口标题，方便区分当前运行的是哪个 lesson。"

    if "pygame.event.get" in stripped:
        return "读取 pygame 事件队列，包括关闭窗口、按键、鼠标点击等交互。"

    if "pygame.key.get_pressed" in stripped:
        return "读取当前键盘按键状态，用于手动驾驶控制。"

    if "pygame.display.flip" in stripped:
        return "刷新 pygame 窗口，把本帧绘制结果真正显示到屏幕上。"

    if "vehicle.apply_control" in stripped:
        return "把油门、刹车、方向盘等控制量发送给 CARLA 车辆。"

    if ".listen(" in stripped:
        return "注册 CARLA 传感器回调函数；每次传感器产生新数据时会自动调用。"

    if ".spawn_actor" in stripped or ".try_spawn_actor" in stripped:
        return "在 CARLA 世界中根据 blueprint 和 transform 生成一个真实 actor。"

    if ".destroy()" in stripped:
        return "销毁 CARLA actor，避免脚本退出后车辆或传感器残留在世界里。"

    if ".get_transform()" in stripped:
        return "读取 actor 当前 Transform，也就是世界坐标位置和姿态。"

    if ".get_velocity()" in stripped:
        return "读取车辆当前世界坐标系下的速度向量。"

    if ".get_forward_vector()" in stripped:
        return "读取 actor 局部 +X 轴在世界坐标中的方向，车辆上通常就是车头方向。"

    if "build_camera_intrinsic_k" in stripped:
        return "构造相机内参矩阵 K，用于 camera 坐标和像素坐标之间的转换。"

    if "world_to_pixel" in stripped:
        return "把 CARLA 世界坐标点投影到相机图像像素位置。"

    if "pixel_depth_to_world" in stripped:
        return "根据像素坐标和 depth 值反算该点的 CARLA 世界坐标。"

    if "pixel_to_world_on_ground" in stripped:
        return "把图像像素射线与地面平面求交，估计路面点的世界坐标。"

    if "make_ground_arrow_polygon" in stripped:
        return "根据箭头起点和目标点生成贴地箭头多边形的世界坐标顶点。"

    if "project_polygon_to_pixels" in stripped:
        return "把箭头多边形的世界坐标顶点批量投影成屏幕像素点。"

    if "debug_draw" in stripped or "world.debug" in stripped:
        return "使用 CARLA debug draw 在 UE 世界里画调试点、线或箭头，便于核对坐标。"

    if stripped.startswith(("break", "continue", "pass")):
        return "控制流程语句，用于跳出循环、进入下一轮循环，或占位不执行操作。"

    assignment = split_assignment(stripped)
    if assignment:
        left, right = assignment
        if "carla.Client" in right:
            return "创建 CARLA client 对象，后续通过它连接和控制仿真 server。"
        if "client.get_world" in right:
            return "从 CARLA server 获取当前仿真 world。"
        if "world.get_map" in right:
            return "读取当前 world 使用的地图对象。"
        if "world.get_blueprint_library" in right:
            return "读取 blueprint 库，后续用它选择车辆和传感器模板。"
        if "world.get_actors" in right:
            return "读取当前世界中所有 actor，便于统计或筛选车辆/传感器。"
        if "np.array" in right or "np.dot" in right:
            return "进行 numpy 数组或矩阵计算，这是坐标变换和投影的数学基础。"
        if "math." in right:
            return "使用数学函数计算角度、三角函数、距离或归一化结果。"
        if "CameraSensor" in right:
            return "创建一个相机传感器包装对象，内部会生成 CARLA camera actor 并接收图像。"
        if "spawn_ego_vehicle" in right:
            return "生成本 lesson 的主车 ego vehicle，后续控制和传感器都围绕它展开。"
        if "connect_to_carla" in right:
            return "连接 CARLA server，并拿到 client 和 world。"
        if "get_keyboard_vehicle_control" in right:
            return "把 pygame 键盘状态转换为 CARLA 车辆控制命令。"
        if "make_pygame_surface" in right:
            return "把 numpy 图像转换成 pygame 可以绘制的 surface。"
        if "ground_point_in_vehicle_frame" in right:
            return "用车辆局部坐标定义一个路面点，并转换成世界坐标。"
        if "event.pos" in right:
            return "读取鼠标事件中的像素坐标，作为手工标注或模拟检测点。"
        return "给 `{}` 赋值；右侧表达式计算或创建结果，左侧变量保存下来供后续使用。".format(left)

    if stripped.endswith(")") or stripped.endswith("),") or stripped.endswith("]") or stripped.endswith("},"):
        return "函数调用、对象构造或容器内容的一部分；结合上下文完成当前代码块的参数配置。"

    if stripped in ["]", ")", "}", "],", "),", "},"]:
        return "结束前面开始的列表、元组、字典或函数调用结构。"

    return "当前代码行参与本 lesson 的主逻辑；请结合上一行和下一行一起理解其作用。"


def generate_for_file(path):
    rel_name = os.path.basename(path)
    output_name = rel_name.replace(".py", "_line_by_line.md")
    output_path = os.path.join(OUTPUT_DIR, output_name)

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    context = {"in_docstring": False}
    rows = []
    for index, line in enumerate(lines, start=1):
        comment = comment_for_line(line, context)
        code = line.rstrip("\n")
        rows.append((index, code, comment))

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# {} 逐行注释\n\n".format(rel_name))
        f.write("说明：本文件不替代源码运行；它是给初学者阅读的逐行讲义。\n\n")
        f.write("| 行号 | 代码 | 解释 |\n")
        f.write("|---:|---|---|\n")
        for index, code, comment in rows:
            f.write("| {} | {} | {} |\n".format(
                index,
                escape_markdown_cell(code),
                comment.replace("|", "\\|"),
            ))

    return output_path, len(rows)


def main():
    if not os.path.isdir(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    py_files = [
        os.path.join(ROOT, name)
        for name in sorted(os.listdir(ROOT))
        if name.endswith(".py") and name not in SKIP_FILES
    ]

    index_path = os.path.join(OUTPUT_DIR, "README.md")
    generated = []
    for path in py_files:
        generated.append((os.path.basename(path),) + generate_for_file(path))

    with open(index_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 逐行注释讲义索引\n\n")
        f.write("这个目录由 `generate_line_by_line_comments.py` 生成。\n\n")
        f.write("原始 lesson 代码仍在上一级目录，可以直接运行；本目录用于阅读每一行代码的解释。\n\n")
        f.write("| 源文件 | 逐行注释 | 行数 |\n")
        f.write("|---|---|---:|\n")
        for source_name, output_path, line_count in generated:
            output_name = os.path.basename(output_path)
            f.write("| `{}` | [{}]({}) | {} |\n".format(
                source_name,
                output_name,
                output_name,
                line_count,
            ))

    print("Generated line-by-line comments:")
    print("  {}".format(OUTPUT_DIR))
    print("Files:", len(generated))


if __name__ == "__main__":
    main()
