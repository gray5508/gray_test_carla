from pathlib import Path
import argparse
import sys


SUBPROJECT_DIR = Path(__file__).resolve().parents[1]
if str(SUBPROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(SUBPROJECT_DIR))

from nav_learning.arrow_renderer import ArrowRenderer  # noqa: E402
from nav_learning.paths import ensure_runtime, latest_capture_image, lane  # noqa: E402
from nav_learning.settings import build_parser, config_from_args  # noqa: E402
from nav_learning.yolop_detector import YolopLaneDetector  # noqa: E402


def output_path(output_dir, input_path, suffix):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / "{}{}".format(Path(input_path).stem, suffix)


def describe_result(result, inference_ms):
    print(
        "YOLOP {:.0f} ms | direction={} | conf={:.2f} | center={} left={} right={}".format(
            inference_ms,
            getattr(result, "turn_direction", "unknown"),
            getattr(result, "confidence", 0.0),
            len(getattr(result, "center_points", []) or []),
            len(getattr(result, "left_points", []) or []),
            len(getattr(result, "right_points", []) or []),
        )
    )


def process_image(path, detector, renderer, output_dir, show_geometry, show_mask):
    bgr = lane.cv2.imread(str(path))
    if bgr is None:
        raise RuntimeError("Cannot read image: {}".format(path))
    result, debug_lines, inference_ms = detector.analyze_bgr(bgr)
    renderer.draw_lane_debug(bgr, result, show_geometry=show_geometry, show_mask=show_mask)
    out = output_path(output_dir, path, "__yolo_learning.png")
    lane.cv2.imwrite(str(out), bgr)
    describe_result(result, inference_ms)
    print("Saved:", out)


def process_video(path, detector, renderer, output_dir, show_geometry, show_mask, every, limit):
    cap = lane.cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError("Cannot open video: {}".format(path))

    fps = cap.get(lane.cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(lane.cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(lane.cv2.CAP_PROP_FRAME_HEIGHT))
    out = output_path(output_dir, path, "__yolo_learning.mp4")
    writer = lane.cv2.VideoWriter(str(out), lane.cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    frame_idx = 0
    last_result = None
    every = max(1, int(every))
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if limit and frame_idx >= limit:
                break
            if frame_idx % every == 0 or last_result is None:
                last_result, debug_lines, inference_ms = detector.analyze_bgr(frame)
                if frame_idx % max(1, every * 10) == 0:
                    print("frame", frame_idx)
                    describe_result(last_result, inference_ms)
            renderer.draw_lane_debug(frame, last_result, show_geometry=show_geometry, show_mask=show_mask)
            writer.write(frame)
            frame_idx += 1
    finally:
        cap.release()
        writer.release()

    print("Saved:", out)


def main():
    parser = build_parser("Run only YOLOP lane segmentation and lane geometry analysis.")
    parser.add_argument("--input", default=None, help="Image/video path. Empty means latest capture screenshot.")
    parser.add_argument("--output-dir", default=str(SUBPROJECT_DIR / "outputs" / "yolo_test"))
    parser.add_argument("--hide-geometry", action="store_true", help="Do not draw detected lane boundaries/centerline.")
    parser.add_argument("--every", type=int, default=1, help="Video only: run YOLOP every N frames.")
    parser.add_argument("--limit", type=int, default=0, help="Video only: stop after N frames, 0 means full video.")
    args = parser.parse_args()
    config = config_from_args(args)

    ensure_runtime()
    input_path = Path(args.input) if args.input else latest_capture_image()
    if input_path is None:
        raise RuntimeError("No input was given and no capture screenshot was found.")

    detector = YolopLaneDetector(config)
    renderer = ArrowRenderer(config)
    show_geometry = not args.hide_geometry
    show_mask = bool(args.show_debug_mask)

    suffix = input_path.suffix.lower()
    if suffix in lane.VIDEO_EXTS:
        process_video(input_path, detector, renderer, args.output_dir, show_geometry, show_mask, args.every, args.limit)
    else:
        process_image(input_path, detector, renderer, args.output_dir, show_geometry, show_mask)


if __name__ == "__main__":
    main()

