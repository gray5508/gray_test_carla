# -*- coding: utf-8 -*-
"""实时 CARLA demo 才需要的依赖。

geometry/navigation/yolop 这些模块不直接导入 CARLA helper，是为了让小测试
更轻量。只有真正运行 `app.py` 时，才需要连接 CARLA、生成车辆、创建相机。
"""

from .runtime_deps import lane  # noqa: F401

from common import CAMERA_FOV  # noqa: E402
from common import CameraSensor  # noqa: E402
from common import build_camera_intrinsic_k  # noqa: E402
from common import connect_to_carla  # noqa: E402
from common import destroy_actors  # noqa: E402
from common import draw_text_lines  # noqa: E402
from common import get_keyboard_vehicle_control  # noqa: E402
from common import make_pygame_surface  # noqa: E402
from common import spawn_ego_vehicle  # noqa: E402
