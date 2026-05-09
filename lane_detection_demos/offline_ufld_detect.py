"""
Run UFLD-v2 only on captured CARLA screenshots/videos.

The default model is the Tusimple 320x800 model:
  model/ufld-v2/resources/ufldv2_tusimple_res34_320x800.onnx

Examples:
  python offline_ufld_detect.py
  python offline_ufld_detect.py --input captures/session_xxx/videos/demo.mp4
  python offline_ufld_detect.py --every 3 --limit 300
"""

import argparse

from offline_lane_detect import (
    DEFAULT_CAPTURE_ROOT,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_UFLD_CROP_RATIO,
    DEFAULT_UFLD_HEIGHT,
    DEFAULT_UFLD_ONNX,
    DEFAULT_UFLD_WIDTH,
    run_offline,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Offline UFLD-v2 lane detection on captured images/videos.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", default="", help="Image/video file or folder. Empty means latest captures session.")
    parser.add_argument("--capture-root", default=str(DEFAULT_CAPTURE_ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--show-guide", action="store_true", help="Draw selected nearest guide line.")
    parser.add_argument("--every", type=int, default=1, help="Run inference every N video frames; reuse last result.")
    parser.add_argument("--limit", type=int, default=0, help="Limit video frames for quick tests; 0 means no limit.")
    parser.add_argument("--normalize", choices=["imagenet", "zero-one"], default="imagenet")
    parser.add_argument("--ufld-onnx", default=str(DEFAULT_UFLD_ONNX))
    parser.add_argument("--ufld-width", type=int, default=DEFAULT_UFLD_WIDTH)
    parser.add_argument("--ufld-height", type=int, default=DEFAULT_UFLD_HEIGHT)
    parser.add_argument("--ufld-confidence", type=float, default=0.45)
    parser.add_argument("--ufld-dataset", choices=["auto", "tusimple", "culane", "curvelanes"], default="auto")
    parser.add_argument("--ufld-crop-ratio", type=float, default=DEFAULT_UFLD_CROP_RATIO)
    args = parser.parse_args()
    args.model = "ufld"
    return args


def main():
    run_offline(parse_args())


if __name__ == "__main__":
    main()
