"""
Run YOLOP only on captured CARLA screenshots/videos.

Examples:
  python offline_yolop_detect.py
  python offline_yolop_detect.py --input captures/session_xxx/videos/demo.mp4
  python offline_yolop_detect.py --every 3 --limit 300
"""

import argparse

from offline_lane_detect import (
    DEFAULT_CAPTURE_ROOT,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_YOLOP_HEIGHT,
    DEFAULT_YOLOP_ONNX,
    DEFAULT_YOLOP_WIDTH,
    run_offline,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Offline YOLOP lane detection on captured images/videos.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", default="", help="Image/video file or folder. Empty means latest captures session.")
    parser.add_argument("--capture-root", default=str(DEFAULT_CAPTURE_ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--show-guide", action="store_true", help="Draw selected nearest guide line.")
    parser.add_argument("--every", type=int, default=1, help="Run inference every N video frames; reuse last result.")
    parser.add_argument("--limit", type=int, default=0, help="Limit video frames for quick tests; 0 means no limit.")
    parser.add_argument("--normalize", choices=["imagenet", "zero-one"], default="imagenet")
    parser.add_argument("--yolop-onnx", default=str(DEFAULT_YOLOP_ONNX))
    parser.add_argument("--yolop-width", type=int, default=DEFAULT_YOLOP_WIDTH)
    parser.add_argument("--yolop-height", type=int, default=DEFAULT_YOLOP_HEIGHT)
    parser.add_argument("--yolop-threshold", type=float, default=0.45)
    args = parser.parse_args()
    args.model = "yolop"
    return args


def main():
    run_offline(parse_args())


if __name__ == "__main__":
    main()
