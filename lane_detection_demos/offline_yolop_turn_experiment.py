"""
Offline YOLOP lane-segmentation turn experiment.

This script intentionally does not use CARLA waypoints. It only uses the
YOLOP lane-line segmentation mask, then estimates a visual current-lane
centerline and draws a plain arrow toward the detected bend/lookahead point.

Examples:
  python offline_yolop_turn_experiment.py
  python offline_yolop_turn_experiment.py --input captures/session_xxx/videos/demo.mp4
  python offline_yolop_turn_experiment.py --input captures/session_xxx/videos/demo.mp4 --start-frame 280 --end-frame 430
"""

import argparse
import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path

import offline_lane_detect as lane


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}


@dataclass
class TurnResult:
    raw_mask: object = None
    clean_mask: object = None
    left_points: object = None
    right_points: object = None
    center_points: object = None
    smooth_center: object = None
    start_point: object = None
    target_point: object = None
    confidence: float = 0.0
    turn_direction: str = "unknown"
    debug_lines: object = None


def timestamp():
    return time.strftime("%Y%m%d_%H%M%S")


def output_name(input_path, suffix):
    return "{}{}".format(Path(input_path).stem, suffix)


def make_output_dir(output_root):
    out_dir = Path(output_root) / "yolop_turn_{}".format(timestamp())
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def run_segments(row_bool):
    xs = lane.np.flatnonzero(row_bool)
    if len(xs) == 0:
        return []

    segments = []
    start = int(xs[0])
    prev = int(xs[0])
    for value in xs[1:]:
        value = int(value)
        if value == prev + 1:
            prev = value
            continue
        segments.append((start, prev))
        start = value
        prev = value
    segments.append((start, prev))
    return segments


def clusters_at_y(mask, y, band=4, max_width_ratio=0.26, min_width=2):
    h, w = mask.shape[:2]
    y0 = max(0, int(y) - band)
    y1 = min(h, int(y) + band + 1)
    row = mask[y0:y1].any(axis=0)
    clusters = []
    for x0, x1 in run_segments(row):
        width = x1 - x0 + 1
        if width < min_width:
            continue
        # Large horizontal spans are usually stop lines/crosswalks/intersection
        # markings, not a current-lane boundary.
        if width > w * max_width_ratio:
            continue
        clusters.append(
            {
                "x": 0.5 * (x0 + x1),
                "x0": x0,
                "x1": x1,
                "width": width,
            }
        )
    return clusters


def choose_nearest(candidates, target_x, max_distance):
    if not candidates:
        return None
    best = min(candidates, key=lambda item: abs(item["x"] - target_x))
    if abs(best["x"] - target_x) > max_distance:
        return None
    return best


def smooth_centerline(points, samples=36):
    if len(points) < 3:
        return points[:]

    arr = lane.np.asarray(points, dtype=lane.np.float32)
    xs = arr[:, 0]
    ys = arr[:, 1]
    degree = 2 if len(points) >= 6 else 1
    coeff = lane.np.polyfit(ys, xs, degree)
    y_new = lane.np.linspace(float(ys.max()), float(ys.min()), samples)
    x_new = lane.np.polyval(coeff, y_new)
    return [(int(x), int(y)) for x, y in zip(x_new, y_new)]


def estimate_current_lane(mask, args):
    h, w = mask.shape[:2]
    cleaned = mask.astype(lane.np.uint8)

    roi = lane.np.zeros_like(cleaned)
    roi[int(h * args.roi_top_ratio) :, :] = 1
    cleaned = cleaned * roi

    kernel = lane.cv2.getStructuringElement(lane.cv2.MORPH_RECT, (3, 3))
    cleaned = lane.cv2.morphologyEx(cleaned, lane.cv2.MORPH_OPEN, kernel)
    cleaned = lane.cv2.dilate(cleaned, kernel, iterations=1).astype(bool)

    y_samples = lane.np.linspace(
        int(h * args.scan_bottom_ratio),
        int(h * args.scan_top_ratio),
        args.scan_rows,
    ).astype(int)

    vehicle_x = w * args.vehicle_x_ratio
    half_width = w * args.initial_half_lane_width_ratio
    max_jump = w * args.max_jump_ratio

    left_points = []
    right_points = []
    center_points = []
    prev_left = None
    prev_right = None
    prev_center = vehicle_x

    for y in y_samples:
        clusters = clusters_at_y(
            cleaned,
            y,
            band=args.scan_band,
            max_width_ratio=args.max_segment_width_ratio,
            min_width=args.min_segment_width,
        )
        if not clusters:
            continue

        ref_center = prev_center
        left_candidates = [c for c in clusters if c["x"] < ref_center - 4]
        right_candidates = [c for c in clusters if c["x"] > ref_center + 4]

        left_target = prev_left if prev_left is not None else ref_center - half_width
        right_target = prev_right if prev_right is not None else ref_center + half_width
        left = choose_nearest(left_candidates, left_target, max_jump)
        right = choose_nearest(right_candidates, right_target, max_jump)

        if left is None and right is None and not center_points:
            # Cold start fallback: take the nearest two lane fragments around
            # the vehicle center.
            ordered = sorted(clusters, key=lambda c: abs(c["x"] - vehicle_x))
            if len(ordered) >= 2:
                pair = sorted(ordered[:2], key=lambda c: c["x"])
                left, right = pair[0], pair[1]

        point_center = None
        if left is not None and right is not None:
            lx = float(left["x"])
            rx = float(right["x"])
            if rx > lx:
                measured_half = 0.5 * (rx - lx)
                half_width = 0.85 * half_width + 0.15 * measured_half
                point_center = 0.5 * (lx + rx)
                prev_left = lx
                prev_right = rx
                left_points.append((int(lx), int(y)))
                right_points.append((int(rx), int(y)))
        elif left is not None:
            lx = float(left["x"])
            point_center = lx + half_width
            prev_left = lx
            prev_right = point_center + half_width
            left_points.append((int(lx), int(y)))
        elif right is not None:
            rx = float(right["x"])
            point_center = rx - half_width
            prev_right = rx
            prev_left = point_center - half_width
            right_points.append((int(rx), int(y)))

        if point_center is None:
            continue
        if point_center < 0 or point_center >= w:
            continue

        if center_points:
            last_x = center_points[-1][0]
            if abs(point_center - last_x) > max_jump:
                continue

        prev_center = point_center
        center_points.append((int(point_center), int(y)))

    smooth = smooth_centerline(center_points, samples=args.smooth_samples)
    confidence = min(1.0, len(center_points) / float(max(1, args.scan_rows)))
    start, target, direction = choose_arrow_points(smooth, w, h, args)

    debug = [
        "YOLOP turn experiment",
        "center pts: {} | confidence: {:.2f}".format(len(center_points), confidence),
        "direction: {}".format(direction),
    ]
    if start and target:
        debug.append("arrow: {} -> {}".format(start, target))
    else:
        debug.append("arrow: not enough stable centerline")

    return TurnResult(
        raw_mask=mask,
        clean_mask=cleaned,
        left_points=left_points,
        right_points=right_points,
        center_points=center_points,
        smooth_center=smooth,
        start_point=start,
        target_point=target,
        confidence=confidence,
        turn_direction=direction,
        debug_lines=debug,
    )


def closest_point_by_y(points, target_y):
    if not points:
        return None
    return min(points, key=lambda point: abs(point[1] - target_y))


def choose_arrow_points(center_points, width, height, args):
    if len(center_points) < args.min_center_points:
        return None, None, "unknown"

    start_y = height * args.arrow_start_y_ratio
    start = closest_point_by_y(center_points, start_y)
    if start is None:
        return None, None, "unknown"

    shift_threshold = width * args.turn_shift_ratio
    top_candidates = [
        point
        for point in center_points
        if point[1] <= start[1] and abs(point[0] - start[0]) >= shift_threshold
    ]
    if top_candidates:
        target_pool = top_candidates[: min(len(top_candidates), args.target_average_points)]
    else:
        target_pool = center_points[-min(len(center_points), args.target_average_points) :]

    tx = int(sum(point[0] for point in target_pool) / float(len(target_pool)))
    ty = int(sum(point[1] for point in target_pool) / float(len(target_pool)))
    target = (tx, ty)
    dx = target[0] - start[0]
    if abs(dx) < shift_threshold:
        direction = "straight/weak"
    elif dx > 0:
        direction = "right"
    else:
        direction = "left"
    return start, target, direction


def predict_yolop_mask(adapter, bgr):
    obs = adapter.predict(bgr)
    if obs.lane_mask is None:
        return None, obs.debug_lines or []
    return obs.lane_mask.astype(bool), obs.debug_lines or []


def draw_polyline(image, points, color, thickness=3):
    if points and len(points) >= 2:
        pts = lane.np.asarray(points, dtype=lane.np.int32)
        lane.cv2.polylines(image, [pts], False, color, thickness, lane.cv2.LINE_AA)


def draw_points(image, points, color, radius=3, stride=4):
    if not points:
        return
    for point in points[:: max(1, stride)]:
        lane.cv2.circle(image, tuple(point), radius, color, -1, lane.cv2.LINE_AA)


def draw_turn_overlay(bgr, result, args):
    out = bgr.copy()
    if result.raw_mask is not None and args.draw_raw_mask:
        color = lane.np.zeros_like(out)
        color[result.raw_mask.astype(bool)] = (255, 190, 0)
        out = lane.cv2.addWeighted(out, 1.0, color, 0.35, 0.0)

    if result.clean_mask is not None:
        color = lane.np.zeros_like(out)
        color[result.clean_mask.astype(bool)] = (255, 255, 0)
        out = lane.cv2.addWeighted(out, 1.0, color, 0.35, 0.0)

    draw_points(out, result.left_points, (80, 180, 255), radius=3, stride=3)
    draw_points(out, result.right_points, (255, 160, 80), radius=3, stride=3)
    draw_polyline(out, result.smooth_center, (60, 230, 60), thickness=4)
    draw_points(out, result.center_points, (0, 150, 0), radius=3, stride=3)

    if result.start_point and result.target_point and result.confidence >= args.min_confidence:
        lane.cv2.arrowedLine(
            out,
            tuple(result.start_point),
            tuple(result.target_point),
            (0, 0, 255),
            5,
            lane.cv2.LINE_AA,
            tipLength=0.18,
        )
        lane.cv2.circle(out, tuple(result.start_point), 7, (0, 0, 180), -1, lane.cv2.LINE_AA)
        lane.cv2.circle(out, tuple(result.target_point), 8, (0, 0, 255), -1, lane.cv2.LINE_AA)

    y = 30
    for text in (result.debug_lines or [])[:6]:
        lane.cv2.putText(out, text, (18, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.72, (20, 20, 20), 3, lane.cv2.LINE_AA)
        lane.cv2.putText(out, text, (18, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 1, lane.cv2.LINE_AA)
        y += 28
    return out


def analyze_frame(adapter, frame, args):
    mask, model_debug = predict_yolop_mask(adapter, frame)
    if mask is None:
        result = TurnResult(debug_lines=["YOLOP lane mask missing"] + model_debug[:2])
    else:
        result = estimate_current_lane(mask, args)
    return result, draw_turn_overlay(frame, result, args)


def collect_inputs(input_path, capture_root):
    return lane.collect_inputs(input_path, capture_root)


def process_image(path, adapter, output_dir, args):
    bgr = lane.cv2.imread(str(path), lane.cv2.IMREAD_COLOR)
    if bgr is None:
        print("Skip unreadable image:", path)
        return []
    result, annotated = analyze_frame(adapter, bgr, args)
    out_path = output_dir / output_name(path, "__yolop_turn_experiment.png")
    lane.cv2.imwrite(str(out_path), annotated)
    print("Image {} -> {}".format(Path(path).name, out_path))
    print("  confidence={:.2f}, direction={}".format(result.confidence, result.turn_direction))
    return [out_path]


def process_video(path, adapter, output_dir, args):
    cap = lane.cv2.VideoCapture(str(path))
    if not cap.isOpened():
        print("Skip unreadable video:", path)
        return []

    fps = cap.get(lane.cv2.CAP_PROP_FPS)
    if fps <= 1e-3:
        fps = 30.0
    width = int(cap.get(lane.cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(lane.cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(lane.cv2.CAP_PROP_FRAME_COUNT))

    start_frame = max(0, args.start_frame)
    end_frame = args.end_frame if args.end_frame > 0 else frame_count
    if args.limit > 0:
        end_frame = min(end_frame, start_frame + args.limit)
    end_frame = min(end_frame, frame_count)

    cap.set(lane.cv2.CAP_PROP_POS_FRAMES, start_frame)
    out_path = output_dir / output_name(path, "__yolop_turn_experiment.mp4")
    writer = lane.cv2.VideoWriter(
        str(out_path),
        lane.cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    csv_path = output_dir / output_name(path, "__yolop_turn_debug.csv")
    csv_file = csv_path.open("w", newline="", encoding="utf8")
    csv_writer = csv.DictWriter(
        csv_file,
        fieldnames=[
            "frame",
            "time_sec",
            "confidence",
            "direction",
            "start_x",
            "start_y",
            "target_x",
            "target_y",
            "center_points",
        ],
    )
    csv_writer.writeheader()

    frame_idx = start_frame
    last_result = None
    last_annotated = None
    while frame_idx < end_frame:
        ok, frame = cap.read()
        if not ok:
            break

        if (frame_idx - start_frame) % max(1, args.every) == 0 or last_result is None:
            last_result, last_annotated = analyze_frame(adapter, frame, args)
        else:
            # For skipped inference frames, redraw the previous diagnostic on
            # the current frame would be misleading, so run the light overlay
            # only from the cached geometry.
            last_annotated = draw_turn_overlay(frame, last_result, args)

        writer.write(last_annotated)
        start = last_result.start_point or ("", "")
        target = last_result.target_point or ("", "")
        csv_writer.writerow(
            {
                "frame": frame_idx,
                "time_sec": "{:.3f}".format(frame_idx / fps),
                "confidence": "{:.3f}".format(last_result.confidence),
                "direction": last_result.turn_direction,
                "start_x": start[0],
                "start_y": start[1],
                "target_x": target[0],
                "target_y": target[1],
                "center_points": len(last_result.center_points or []),
            }
        )

        frame_idx += 1
        if (frame_idx - start_frame) % 60 == 0:
            print("Video {} processed {} frames".format(Path(path).name, frame_idx - start_frame))

    csv_file.close()
    cap.release()
    writer.release()
    print("Video {} done, frames: {}..{}".format(Path(path).name, start_frame, frame_idx - 1))
    print("  ->", out_path)
    print("  ->", csv_path)
    return [out_path, csv_path]


def write_run_meta(output_dir, args, inputs, outputs):
    meta = {
        "args": vars(args),
        "inputs": [str(path) for path in inputs],
        "outputs": [str(path) for path in outputs],
        "created_at": timestamp(),
        "note": "Pure-vision YOLOP lane-segmentation turn experiment; no CARLA waypoints.",
    }
    path = output_dir / "run_meta.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf8")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Offline turn experiment based on YOLOP lane segmentation only.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", default="", help="Image/video file or folder. Empty means latest captures session.")
    parser.add_argument("--capture-root", default=str(lane.DEFAULT_CAPTURE_ROOT))
    parser.add_argument("--output-root", default=str(lane.DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--yolop-onnx", default=str(lane.DEFAULT_YOLOP_ONNX))
    parser.add_argument("--yolop-width", type=int, default=lane.DEFAULT_YOLOP_WIDTH)
    parser.add_argument("--yolop-height", type=int, default=lane.DEFAULT_YOLOP_HEIGHT)
    parser.add_argument("--yolop-threshold", type=float, default=0.45)
    parser.add_argument("--normalize", choices=["imagenet", "zero-one"], default="imagenet")

    parser.add_argument("--start-frame", type=int, default=0, help="Video start frame for quick turn-section tests.")
    parser.add_argument("--end-frame", type=int, default=0, help="Video end frame; 0 means video end.")
    parser.add_argument("--limit", type=int, default=0, help="Limit processed video frames; 0 means no limit.")
    parser.add_argument("--every", type=int, default=1, help="Run YOLOP every N frames and reuse geometry between frames.")

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
    parser.add_argument("--turn-shift-ratio", type=float, default=0.055)
    parser.add_argument("--target-average-points", type=int, default=5)
    parser.add_argument("--min-center-points", type=int, default=8)
    parser.add_argument("--min-confidence", type=float, default=0.18)
    parser.add_argument("--draw-raw-mask", action="store_true", help="Also draw the original YOLOP mask under the cleaned mask.")
    return parser.parse_args()


def main():
    args = parse_args()
    lane.ensure_runtime()
    inputs = collect_inputs(args.input, args.capture_root)
    if not inputs:
        raise RuntimeError("No image/video inputs found.")

    output_dir = make_output_dir(args.output_root)
    adapter = lane.YOLOPAdapter(
        args.yolop_onnx,
        input_width=args.yolop_width,
        input_height=args.yolop_height,
        threshold=args.yolop_threshold,
        normalize=args.normalize,
    )

    print("Inputs:", len(inputs))
    print("Output:", output_dir)
    print("YOLOP ONNX:", args.yolop_onnx)
    print("Pure vision: YOLOP lane segmentation only, no waypoints.")

    outputs = []
    for path in inputs:
        suffix = Path(path).suffix.lower()
        if suffix in IMAGE_EXTS:
            outputs.extend(process_image(path, adapter, output_dir, args))
        elif suffix in VIDEO_EXTS:
            outputs.extend(process_video(path, adapter, output_dir, args))
        else:
            print("Skip unsupported file:", path)

    write_run_meta(output_dir, args, inputs, outputs)
    print("Done. Output dir:", output_dir)


if __name__ == "__main__":
    main()
