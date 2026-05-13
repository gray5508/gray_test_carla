# -*- coding: utf-8 -*-
"""运行时依赖桥接层。

这个模块只做“路径准备”和“轻量导入”，不启动 CARLA，不创建 pygame 窗口，
也不加载 YOLOP ONNX session。这样做的好处是：

    - `main.py --help` 可以很快返回，不需要 CARLA server。
    - 几何和状态机测试可以复用 numpy/cv2 工具，但不进入实时仿真。
    - 所有 sys.path 处理集中在一个地方，其他模块不用重复写路径逻辑。
"""

import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
TUTORIAL_ROOT = THIS_DIR.parent
LANE_DEMOS_DIR = TUTORIAL_ROOT.parent
PROJECT_ROOT = LANE_DEMOS_DIR.parent
CARLA_TUTORIAL_DIR = PROJECT_ROOT / "carla_from_zero_to_ar_tutorial"

for path in (LANE_DEMOS_DIR, CARLA_TUTORIAL_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import offline_lane_detect as lane  # noqa: E402

# Windows + conda 环境里，cv2/numpy/onnxruntime 可能依赖 env/Library/bin 下的 DLL。
# 在导入 common.py 或 OpenCV 相关模块前先补 DLL 搜索路径，可以减少“找不到 DLL”
# 这类环境问题。
lane.prepare_windows_dll_search_path()

from offline_yolop_turn_experiment import estimate_current_lane  # noqa: E402
