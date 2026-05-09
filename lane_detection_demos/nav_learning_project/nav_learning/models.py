from dataclasses import dataclass


NAV_NONE = "none"
NAV_STRAIGHT = "straight"
NAV_LEFT = "left"
NAV_RIGHT = "right"


@dataclass
class NavCandidate:
    nav_mode: str
    start: tuple
    target: tuple
    confidence: float
    center_points: int
    direction: str
    created_at: float


@dataclass
class LockedNavArrow:
    nav_mode: str
    start: tuple
    target: tuple
    confidence: float
    locked_at: float
    expires_at: float


@dataclass
class DetectionPacket:
    result: object
    candidate: object
    inference_ms: float
    frame_id: object
    nav_mode: str
    error: str = ""


class EmptyResult(object):
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

