# -*- coding: utf-8 -*-
"""模块之间传递的小型数据对象。

教学重点：
    这些 dataclass 就是各模块之间的“接口合同”。YOLOP 模块不直接画图，
    它只返回 DetectionPacket；导航模块不关心 OpenCV 怎么画，它只锁定
    LockedNavArrow；世界锚点模块再把 LockedNavArrow 转成 WorldArrowAnchor。

阅读顺序建议：
    1. 先理解 NavCandidate：单帧检测出来的候选箭头。
    2. 再理解 LockedNavArrow：连续几帧稳定后，允许显示的箭头。
    3. 最后理解 WorldArrowAnchor：已经固定到 CARLA 世界坐标的箭头。
"""

from dataclasses import dataclass

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
NAV_NONE = "none"
NAV_STRAIGHT = "straight"
NAV_LEFT = "left"
NAV_RIGHT = "right"

@dataclass
class NavCandidate:
    """YOLOP + 车道几何在“某一帧”给出的候选导航箭头。"""

    nav_mode: str
    start: tuple
    target: tuple
    confidence: float
    center_points: int
    direction: str
    created_at: float

@dataclass
class LockedNavArrow:
    """经过稳定性确认后，短时间内可以显示给用户的箭头。"""

    nav_mode: str
    start: tuple
    target: tuple
    confidence: float
    locked_at: float
    expires_at: float

@dataclass
class WorldArrowAnchor:
    """把锁定箭头固定到 CARLA 世界坐标后得到的 AR 锚点。"""

    nav_mode: str
    start_ground: object
    target_ground: object
    vehicle_to_world: object
    start_world: object
    target_world: object
    confidence: float
    created_at: float
    expires_at: float

@dataclass
class DetectionPacket:
    """后台 YOLOP 推理线程返回给主循环的数据包。"""

    result: object
    candidate: object
    inference_ms: float
    frame_id: object
    nav_mode: str
    error: str = ""

class EmptyResult(object):
    """当 YOLOP 没有返回 lane mask 时，用一个空结果保持流程不断。"""

    def __init__(self, debug_lines):
        self.raw_mask = None
        self.clean_mask = None
        self.left_points = []
        self.right_points = []
        self.center_points = []
        self.smooth_center = []
        self.start_point = None
        self.target_point = None
        self.confidence = 0.0
        self.turn_direction = "unknown"
        self.debug_lines = debug_lines

