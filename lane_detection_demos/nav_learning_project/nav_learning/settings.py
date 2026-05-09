import argparse
from dataclasses import dataclass, fields
from typing import Optional

from .paths import lane


DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720


@dataclass
class AppConfig:
    # Window and camera stream.
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    display_fps: int = 60
    camera_fps: float = 0.0

    # YOLOP model.
    yolop_onnx: str = str(lane.DEFAULT_YOLOP_ONNX)
    yolop_width: int = lane.DEFAULT_YOLOP_WIDTH
    yolop_height: int = lane.DEFAULT_YOLOP_HEIGHT
    yolop_threshold: float = 0.45
    normalize: str = "imagenet"

    # Background detection cadence and stability lock.
    detect_interval: float = 1.0
    arrow_hold_seconds: float = 3.0
    stability_confirmations: int = 2
    stability_window_seconds: float = 3.2
    max_candidate_history: int = 5
    stable_target_radius: float = 130.0
    arrow_smoothing_alpha: float = 0.35

    # Lane-mask geometry scan. These are passed to offline_yolop_turn_experiment.
    roi_top_ratio: float = 0.38
    scan_top_ratio: float = 0.38
    scan_bottom_ratio: float = 0.92
    scan_rows: int = 42
    scan_band: int = 4
    min_segment_width: int = 2
    max_segment_width_ratio: float = 0.24
    vehicle_x_ratio: float = 0.50
    initial_half_lane_width_ratio: float = 0.17
    max_jump_ratio: float = 0.16
    smooth_samples: int = 36

    # Navigation geometry.
    arrow_start_y_ratio: float = 0.84
    arrow_start_meters: float = 5.0
    min_arrow_length_meters: float = 2.0
    max_target_forward_meters: float = 15.0
    straight_target_forward_meters: float = 10.0
    straight_right_meters: Optional[float] = None
    straight_validation_samples: int = 9
    straight_validation_ratio: float = 0.66
    min_straight_validation_checks: int = 4
    straight_center_tolerance_ratio: float = 0.11
    straight_boundary_margin_px: float = 6.0
    min_lane_width_px: float = 70.0
    turn_target_y_ratio: float = 0.48
    turn_shift_ratio: float = 0.055
    turn_min_shift_ratio: float = 0.070
    target_average_points: int = 5
    min_center_points: int = 8
    min_confidence: float = 0.18

    # Arrow drawing.
    arrow_style: str = "neon"
    arrow_width: float = 9.0
    arrow_glow_width: float = 34.0
    arrow_glow_alpha: float = 0.16
    arrow_mid_alpha: float = 0.28
    arrow_body_alpha: float = 0.82
    arrow_flow_alpha: float = 0.34
    arrow_flow_speed: float = 0.80
    arrow_pulse_speed: float = 0.85
    arrow_chevrons: int = 2
    arrow_chevron_len: float = 28.0
    arrow_show_particles: bool = False
    arrow_head_min_len: float = 42.0
    arrow_head_max_len: float = 78.0
    arrow_anchor_radius: float = 8.0

    # Debug drawing.
    show_debug_geometry: bool = False
    show_debug_mask: bool = False

    # Filled by the CARLA camera session at runtime.
    camera_k: object = None
    camera_mount_transform: object = None
    vehicle_ground_z: float = 0.0


def add_common_arguments(parser):
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--display-fps", type=int, default=60)
    parser.add_argument("--camera-fps", type=float, default=0.0, help="0 means every CARLA camera tick.")
    parser.add_argument("--yolop-onnx", default=str(lane.DEFAULT_YOLOP_ONNX))
    parser.add_argument("--yolop-width", type=int, default=lane.DEFAULT_YOLOP_WIDTH)
    parser.add_argument("--yolop-height", type=int, default=lane.DEFAULT_YOLOP_HEIGHT)
    parser.add_argument("--yolop-threshold", type=float, default=0.45)
    parser.add_argument("--normalize", choices=["imagenet", "zero-one"], default="imagenet")

    parser.add_argument("--detect-interval", type=float, default=1.0)
    parser.add_argument("--arrow-hold-seconds", type=float, default=3.0)
    parser.add_argument("--stability-confirmations", type=int, default=2)
    parser.add_argument("--stability-window-seconds", type=float, default=3.2)
    parser.add_argument("--max-candidate-history", type=int, default=5)
    parser.add_argument("--stable-target-radius", type=float, default=130.0)
    parser.add_argument("--arrow-smoothing-alpha", type=float, default=0.35)

    parser.add_argument("--roi-top-ratio", type=float, default=0.38)
    parser.add_argument("--scan-top-ratio", type=float, default=0.38)
    parser.add_argument("--scan-bottom-ratio", type=float, default=0.92)
    parser.add_argument("--scan-rows", type=int, default=42)
    parser.add_argument("--scan-band", type=int, default=4)
    parser.add_argument("--min-segment-width", type=int, default=2)
    parser.add_argument("--max-segment-width-ratio", type=float, default=0.24)
    parser.add_argument("--vehicle-x-ratio", type=float, default=0.50)
    parser.add_argument("--initial-half-lane-width-ratio", type=float, default=0.17)
    parser.add_argument("--max-jump-ratio", type=float, default=0.16)
    parser.add_argument("--smooth-samples", type=int, default=36)
    parser.add_argument("--arrow-start-y-ratio", type=float, default=0.84)
    parser.add_argument("--arrow-start-meters", type=float, default=5.0)
    parser.add_argument("--min-arrow-length-meters", type=float, default=2.0)
    parser.add_argument("--max-target-forward-meters", type=float, default=15.0)
    parser.add_argument("--straight-target-forward-meters", type=float, default=10.0)
    parser.add_argument(
        "--straight-right-meters",
        type=float,
        default=None,
        help="Vehicle-local right offset for straight arrows. Empty means camera/driver forward line.",
    )
    parser.add_argument("--straight-validation-samples", type=int, default=9)
    parser.add_argument("--straight-validation-ratio", type=float, default=0.66)
    parser.add_argument("--min-straight-validation-checks", type=int, default=4)
    parser.add_argument("--straight-center-tolerance-ratio", type=float, default=0.11)
    parser.add_argument("--straight-boundary-margin-px", type=float, default=6.0)
    parser.add_argument("--min-lane-width-px", type=float, default=70.0)
    parser.add_argument("--turn-target-y-ratio", type=float, default=0.48)
    parser.add_argument("--turn-shift-ratio", type=float, default=0.055)
    parser.add_argument("--turn-min-shift-ratio", type=float, default=0.070)
    parser.add_argument("--target-average-points", type=int, default=5)
    parser.add_argument("--min-center-points", type=int, default=8)
    parser.add_argument("--min-confidence", type=float, default=0.18)

    parser.add_argument("--arrow-style", choices=["neon", "simple"], default="neon")
    parser.add_argument("--arrow-width", type=float, default=9.0)
    parser.add_argument("--arrow-glow-width", type=float, default=34.0)
    parser.add_argument("--arrow-glow-alpha", type=float, default=0.16)
    parser.add_argument("--arrow-mid-alpha", type=float, default=0.28)
    parser.add_argument("--arrow-body-alpha", type=float, default=0.82)
    parser.add_argument("--arrow-flow-alpha", type=float, default=0.34)
    parser.add_argument("--arrow-flow-speed", type=float, default=0.80)
    parser.add_argument("--arrow-pulse-speed", type=float, default=0.85)
    parser.add_argument("--arrow-chevrons", type=int, default=2)
    parser.add_argument("--arrow-chevron-len", type=float, default=28.0)
    parser.add_argument("--arrow-show-particles", action="store_true", default=False)
    parser.add_argument("--arrow-head-min-len", type=float, default=42.0)
    parser.add_argument("--arrow-head-max-len", type=float, default=78.0)
    parser.add_argument("--arrow-anchor-radius", type=float, default=8.0)

    parser.add_argument("--show-debug-geometry", action="store_true", default=False)
    parser.add_argument("--show-debug-mask", action="store_true", default=False)


def config_from_args(args):
    config = AppConfig()
    for field in fields(config):
        if hasattr(args, field.name):
            setattr(config, field.name, getattr(args, field.name))
    config.width = int(config.width)
    config.height = int(config.height)
    return config


def build_parser(description):
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_arguments(parser)
    return parser

