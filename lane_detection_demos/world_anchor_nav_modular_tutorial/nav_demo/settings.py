# -*- coding: utf-8 -*-
"""实时 demo 的命令行参数。

这里保留了原始 demo 的大部分参数。学习时可以把参数分成几组看：

    - 窗口/相机/YOLOP：width、height、yolop-onnx、threshold。
    - 检测节奏和稳定性：detect-interval、stability-confirmations。
    - 车道几何：scan_rows、turn_shift_ratio、min_confidence。
    - AR 箭头视觉：ground_arrow_*、arrow_flow_*。
    - 世界锚点：arrow_projection、world_anchor_expire_mode。
"""

import argparse

from .runtime_deps import lane
from .models import DEFAULT_HEIGHT, DEFAULT_WIDTH

def parse_args():
    parser = argparse.ArgumentParser(
        description="Realtime CARLA YOLOP navigation-intent world-anchored AR arrow demo.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
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
    parser.add_argument("--arrow-hold-seconds", type=float, default=6.0)
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
    parser.add_argument("--arrow-start-meters", type=float, default=10.0)
    parser.add_argument("--min-arrow-length-meters", type=float, default=2.0)
    parser.add_argument(
        "--turn-target-min-forward-meters",
        type=float,
        default=7.0,
        help="Minimum forward distance for turn target candidates. Kept separate from arrow start so moving the start does not change turn endpoints.",
    )
    parser.add_argument("--max-target-forward-meters", type=float, default=15.0)
    parser.add_argument("--straight-target-forward-meters", type=float, default=15.0)
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

    parser.add_argument("--arrow-projection", choices=["world", "ground", "screen"], default="world")
    parser.add_argument("--world-anchor-fallback-screen", action="store_true", default=False)
    parser.add_argument("--world-anchor-expire-mode", choices=["pass", "time"], default="pass")
    parser.add_argument("--world-anchor-pass-point", choices=["target", "center", "start"], default="target")
    parser.add_argument("--world-anchor-pass-margin-m", type=float, default=-0.50)
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
    parser.add_argument("--ground-arrow-body-width-m", type=float, default=0.62)
    parser.add_argument("--ground-arrow-head-width-m", type=float, default=1.35)
    parser.add_argument("--ground-arrow-head-length-m", type=float, default=1.35)
    parser.add_argument("--ground-arrow-glow-extra-width-m", type=float, default=0.34)
    parser.add_argument("--ground-arrow-alpha", type=float, default=0.48)
    parser.add_argument("--ground-arrow-glow-alpha", type=float, default=0.18)
    parser.add_argument("--ground-arrow-inner-alpha", type=float, default=0.12)
    parser.add_argument("--ground-arrow-edge-alpha", type=float, default=0.32)
    parser.add_argument("--ground-arrow-flow-length-m", type=float, default=0.70)
    parser.add_argument("--ground-arrow-min-length-m", type=float, default=1.20)
    parser.add_argument("--render-arrow-length-scale", type=float, default=0.67)

    parser.add_argument("--show-debug-geometry", action="store_true", default=False)
    parser.add_argument("--show-debug-mask", action="store_true", default=False)
    args = parser.parse_args()
    args.vehicle_ground_z = 0.0
    return args
