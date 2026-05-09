"""
offline_lane_detect.py

Run lane detection on captured CARLA screenshots and videos.

Examples:
  python offline_lane_detect.py --model yolop
  python offline_lane_detect.py --model ufld
  python offline_yolop_detect.py
  python offline_ufld_detect.py
  python offline_lane_detect.py --model yolop --input captures/session_xxx/videos/demo.mp4
  python offline_lane_detect.py --model both --input captures/session_xxx/screenshots

Outputs are written to:
  lane_detection_demos/offline_outputs/run_YYYYmmdd_HHMMSS/
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
DEFAULT_CAPTURE_ROOT = THIS_DIR / "captures"
DEFAULT_OUTPUT_ROOT = THIS_DIR / "offline_outputs"
DEFAULT_YOLOP_ONNX = THIS_DIR / "model" / "yolop" / "yolop-640-640.onnx"
DEFAULT_UFLD_ONNX = (
    THIS_DIR / "model" / "ufld-v2" / "resources" / "ufldv2_tusimple_res34_320x800.onnx"
)
DEFAULT_YOLOP_WIDTH = 640
DEFAULT_YOLOP_HEIGHT = 640
DEFAULT_UFLD_WIDTH = 800
DEFAULT_UFLD_HEIGHT = 320
DEFAULT_UFLD_CROP_RATIO = 0.8

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}


cv2 = None
np = None
ort = None


def prepare_windows_dll_search_path():
    if os.name != "nt":
        return

    env_root = Path(sys.executable).resolve().parent
    dll_dirs = [
        env_root,
        env_root / "Library" / "bin",
        env_root / "DLLs",
    ]

    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    path_parts_lower = {part.lower() for part in path_parts if part}

    for dll_dir in dll_dirs:
        if not dll_dir.exists():
            continue
        dll_dir_str = str(dll_dir)
        if dll_dir_str.lower() not in path_parts_lower:
            os.environ["PATH"] = dll_dir_str + os.pathsep + os.environ.get("PATH", "")
            path_parts_lower.add(dll_dir_str.lower())
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(dll_dir_str)


def require_runtime():
    prepare_windows_dll_search_path()
    try:
        import cv2
        import numpy as np
        import onnxruntime as ort
    except Exception as exc:
        raise RuntimeError(
            "Offline lane detection needs cv2, numpy and onnxruntime in this Python env.\n"
            "Current import failed: {}: {}\n"
            "Try fixing the carla_test conda env before running this script.".format(
                type(exc).__name__,
                exc,
            )
        )
    return cv2, np, ort


def ensure_runtime():
    global cv2, np, ort
    if cv2 is None or np is None or ort is None:
        cv2, np, ort = require_runtime()


@dataclass
class LaneObservation:
    lane_mask: object = None
    lane_points: object = None
    guide_pixels: object = None
    debug_lines: object = None


def timestamp():
    return time.strftime("%Y%m%d_%H%M%S")


def make_output_dir(output_root):
    output_dir = Path(output_root) / "run_{}".format(timestamp())
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def latest_capture_session(capture_root):
    capture_root = Path(capture_root)
    sessions = [p for p in capture_root.glob("session_*") if p.is_dir()]
    if not sessions:
        raise RuntimeError("No capture sessions found under {}".format(capture_root))
    sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return sessions[0]


def collect_inputs(input_path, capture_root):
    if input_path:
        root = Path(input_path)
    else:
        root = latest_capture_session(capture_root)

    if root.is_file():
        return [root]
    if not root.exists():
        raise RuntimeError("Input path does not exist: {}".format(root))

    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTS or suffix in VIDEO_EXTS:
            files.append(path)
    files.sort()
    return files


def make_session(onnx_path):
    if not Path(onnx_path).is_file():
        raise RuntimeError("ONNX model not found: {}".format(onnx_path))

    available = ort.get_available_providers()
    providers = []
    if "CUDAExecutionProvider" in available:
        providers.append("CUDAExecutionProvider")
    providers.append("CPUExecutionProvider")
    return ort.InferenceSession(str(onnx_path), providers=providers)


def resize_rgb(rgb, width, height):
    if rgb.shape[1] == width and rgb.shape[0] == height:
        return rgb
    return cv2.resize(rgb, (width, height), interpolation=cv2.INTER_LINEAR)


def resize_crop_bottom_rgb(rgb, width, height, crop_ratio):
    if crop_ratio <= 0 or crop_ratio >= 1.0:
        return resize_rgb(rgb, width, height)

    resized_height = int(round(height / crop_ratio))
    resized = cv2.resize(rgb, (width, resized_height), interpolation=cv2.INTER_LINEAR)
    return resized[-height:, :, :]


def resize_mask(mask, width, height):
    if mask.shape[1] == width and mask.shape[0] == height:
        return mask.astype(bool)
    resized = cv2.resize(mask.astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST)
    return resized.astype(bool)


def normalize_image(rgb, mode="imagenet"):
    image = rgb.astype(np.float32) / 255.0
    if mode == "imagenet":
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        image = (image - mean) / std
    return np.transpose(image, (2, 0, 1))[None, ...].astype(np.float32)


def softmax(values, axis=0):
    values = values - np.max(values, axis=axis, keepdims=True)
    exp = np.exp(values)
    return exp / np.sum(exp, axis=axis, keepdims=True)


def sigmoid(values):
    return 1.0 / (1.0 + np.exp(-values))


def output_shapes(session_outputs, outputs):
    return [
        "{}{}".format(meta.name, tuple(out.shape))
        for meta, out in zip(session_outputs, outputs)
    ]


def segmentation_output_to_mask(output, threshold=0.45):
    arr = np.asarray(output)
    if arr.ndim == 4:
        arr = arr[0]
        if arr.shape[0] == 2:
            return np.argmax(arr, axis=0) == 1
        if arr.shape[0] == 1:
            arr = arr[0]
        else:
            arr = arr[-1]
    elif arr.ndim == 3:
        arr = arr[0]

    if arr.max() > 1.0 or arr.min() < 0.0:
        arr = sigmoid(arr)
    return arr > threshold


def find_lane_segmentation_output(output_names, outputs):
    for name, out in zip(output_names, outputs):
        lower = name.lower()
        if ("lane" in lower or "ll" in lower) and np.asarray(out).ndim >= 3:
            return out, name

    four_d = [
        (name, out)
        for name, out in zip(output_names, outputs)
        if np.asarray(out).ndim == 4 and np.asarray(out).shape[1] <= 4
    ]
    if four_d:
        name, out = four_d[-1]
        return out, name

    return None, None


def nearest_line_from_lane_mask(mask, sample_count=24):
    if mask is None:
        return []

    mask = np.asarray(mask).astype(bool)
    h, w = mask.shape[:2]
    ys = np.linspace(int(h * 0.9), int(h * 0.28), sample_count).astype(np.int32)
    line = []

    for y in ys:
        y0 = max(0, y - 2)
        y1 = min(h, y + 3)
        xs = np.where(mask[y0:y1].any(axis=0))[0]
        if len(xs) == 0:
            continue
        x = int(xs[np.argmin(np.abs(xs - w * 0.5))])
        line.append((x, int(y)))
    return line


def find_by_name(output_names, outputs, token):
    for name, out in zip(output_names, outputs):
        if token in name.lower():
            return out, name
    return None, None


def find_ufld_outputs(output_names, outputs):
    loc_row, loc_name = find_by_name(output_names, outputs, "loc_row")
    exist_row, exist_name = find_by_name(output_names, outputs, "exist_row")
    loc_col, loc_col_name = find_by_name(output_names, outputs, "loc_col")
    exist_col, exist_col_name = find_by_name(output_names, outputs, "exist_col")
    if loc_row is not None and exist_row is not None:
        return loc_row, loc_name, exist_row, exist_name, loc_col, loc_col_name, exist_col, exist_col_name

    four_d = [(name, out) for name, out in zip(output_names, outputs) if np.asarray(out).ndim == 4]
    if loc_row is None and four_d:
        loc_name, loc_row = four_d[0]
    if exist_row is None:
        for name, out in four_d:
            arr = np.asarray(out)
            if 2 in arr.shape:
                exist_name, exist_row = name, out
                break
    return loc_row, loc_name, exist_row, exist_name, loc_col, loc_col_name, exist_col, exist_col_name


def squeeze_batch(arr):
    arr = np.asarray(arr)
    if arr.ndim >= 1 and arr.shape[0] == 1:
        return arr[0]
    return arr


def softmax_1d(values):
    values = np.asarray(values, dtype=np.float32)
    values = values - np.max(values)
    exp = np.exp(values)
    return exp / max(np.sum(exp), 1e-6)


def infer_ufld_dataset(onnx_path, input_width, input_height):
    name = Path(onnx_path).name.lower()
    if "tusimple" in name or (input_width == 800 and input_height == 320):
        return "tusimple"
    if "culane" in name:
        return "culane"
    if "curvelanes" in name:
        return "curvelanes"
    return "tusimple"


def ufld_row_anchor(dataset, count, image_height):
    dataset = dataset.lower()
    if dataset == "tusimple":
        anchors = np.linspace(160.0, 710.0, count) / 720.0
    elif dataset == "culane":
        anchors = np.linspace(0.42, 1.0, count)
    elif dataset == "curvelanes":
        anchors = np.linspace(0.4, 1.0, count)
    else:
        anchors = np.linspace(0.42, 1.0, count)
    return anchors * float(image_height)


def ufld_col_anchor(count, image_width):
    return np.linspace(0.0, 1.0, count) * float(image_width)


def decode_ufld_lanes(
    loc_row,
    exist_row,
    loc_col,
    exist_col,
    image_width,
    image_height,
    dataset="tusimple",
    confidence=0.45,
    local_width=1,
):
    loc = squeeze_batch(loc_row)
    exist = squeeze_batch(exist_row)

    if loc.ndim != 3:
        raise RuntimeError("Expected loc_row with 3 dims after squeeze, got {}".format(loc.shape))

    if loc.shape[-1] > 8 and loc.shape[0] <= 8:
        loc = np.transpose(loc, (2, 1, 0))
    if loc.shape[-1] > 8:
        raise RuntimeError("Cannot infer lane dimension from loc_row shape {}".format(loc.shape))

    grid_dim, row_dim, lane_dim = loc.shape
    lanes = []
    row_anchor = ufld_row_anchor(dataset, row_dim, image_height)

    row_valid = None
    if exist is not None and exist.ndim == 3:
        if exist.shape[0] == 2:
            row_valid = np.argmax(exist, axis=0) == 1
        elif exist.shape[-1] == 2:
            row_valid = np.argmax(exist, axis=-1) == 1
    if row_valid is None or row_valid.shape != (row_dim, lane_dim):
        row_prob = softmax(loc, axis=0)
        row_valid = np.max(row_prob, axis=0) > confidence

    row_lane_idx = [1, 2] if lane_dim >= 4 else list(range(lane_dim))
    for lane_idx in row_lane_idx:
        if np.count_nonzero(row_valid[:, lane_idx]) <= row_dim / 2:
            continue
        points = []
        for row_idx in range(row_dim):
            if not row_valid[row_idx, lane_idx]:
                continue
            max_idx = int(np.argmax(loc[:, row_idx, lane_idx]))
            low = max(0, max_idx - local_width)
            high = min(grid_dim - 1, max_idx + local_width)
            indices = np.arange(low, high + 1, dtype=np.float32)
            weights = softmax_1d(loc[low : high + 1, row_idx, lane_idx])
            grid_pos = float(np.sum(weights * indices) + 0.5)
            x = grid_pos / max(1.0, grid_dim - 1.0) * float(image_width)
            y = row_anchor[row_idx]
            if 0 <= x < image_width:
                points.append((int(x), int(y)))
        if len(points) >= 4:
            lanes.append(points)

    if loc_col is None or exist_col is None:
        return lanes

    col = squeeze_batch(loc_col)
    col_exist = squeeze_batch(exist_col)
    if col.ndim != 3:
        return lanes
    if col.shape[-1] > 8 and col.shape[0] <= 8:
        col = np.transpose(col, (2, 1, 0))
    if col.shape[-1] > 8:
        return lanes

    col_grid_dim, col_dim, col_lane_dim = col.shape
    col_anchor = ufld_col_anchor(col_dim, image_width)
    col_valid = None
    if col_exist is not None and col_exist.ndim == 3:
        if col_exist.shape[0] == 2:
            col_valid = np.argmax(col_exist, axis=0) == 1
        elif col_exist.shape[-1] == 2:
            col_valid = np.argmax(col_exist, axis=-1) == 1
    if col_valid is None or col_valid.shape != (col_dim, col_lane_dim):
        col_prob = softmax(col, axis=0)
        col_valid = np.max(col_prob, axis=0) > confidence

    col_lane_idx = [0, 3] if col_lane_dim >= 4 else list(range(col_lane_dim))
    for lane_idx in col_lane_idx:
        if np.count_nonzero(col_valid[:, lane_idx]) <= col_dim / 4:
            continue
        points = []
        for col_idx in range(col_dim):
            if not col_valid[col_idx, lane_idx]:
                continue
            max_idx = int(np.argmax(col[:, col_idx, lane_idx]))
            low = max(0, max_idx - local_width)
            high = min(col_grid_dim - 1, max_idx + local_width)
            indices = np.arange(low, high + 1, dtype=np.float32)
            weights = softmax_1d(col[low : high + 1, col_idx, lane_idx])
            grid_pos = float(np.sum(weights * indices) + 0.5)
            y = grid_pos / max(1.0, col_grid_dim - 1.0) * float(image_height)
            x = col_anchor[col_idx]
            if 0 <= y < image_height:
                points.append((int(x), int(y)))
        if len(points) >= 4:
            lanes.append(points)
    return lanes


def select_nearest_lane(lanes, width, height):
    if not lanes:
        return []

    candidates = []
    for lane in lanes:
        if len(lane) < 2:
            continue
        points = np.array(lane, dtype=np.float32)
        bottom_idx = int(np.argmax(points[:, 1]))
        bottom_x = float(points[bottom_idx, 0])
        bottom_y = float(points[bottom_idx, 1])
        if bottom_y < height * 0.35:
            continue
        candidates.append((abs(bottom_x - width * 0.5), bottom_y, lane))

    if not candidates:
        return []

    candidates.sort(key=lambda item: (item[0], -item[1]))
    selected = candidates[0][2]
    selected = sorted(selected, key=lambda point: point[1], reverse=True)
    return [(int(x), int(y)) for x, y in selected]


class YOLOPAdapter(object):
    name = "yolop"

    def __init__(self, onnx_path, input_width=640, input_height=640, threshold=0.45, normalize="imagenet"):
        self.session = make_session(onnx_path)
        self.input_meta = self.session.get_inputs()[0]
        self.output_meta = self.session.get_outputs()
        self.input_name = self.input_meta.name
        self.input_width = input_width
        self.input_height = input_height
        self.threshold = threshold
        self.normalize = normalize

    def predict(self, bgr):
        image_h, image_w = bgr.shape[:2]
        rgb = bgr[:, :, ::-1]
        resized = resize_rgb(rgb, self.input_width, self.input_height)
        tensor = normalize_image(resized, self.normalize)
        outputs = self.session.run(None, {self.input_name: tensor})
        output_names = [meta.name for meta in self.output_meta]
        shapes = output_shapes(self.output_meta, outputs)

        lane_output, lane_name = find_lane_segmentation_output(output_names, outputs)
        if lane_output is None:
            return LaneObservation(
                guide_pixels=[],
                debug_lines=["no lane output", "outputs: {}".format("; ".join(shapes)[:160])],
            )

        small_mask = segmentation_output_to_mask(lane_output, threshold=self.threshold)
        lane_mask = resize_mask(small_mask, image_w, image_h)
        guide = nearest_line_from_lane_mask(lane_mask)
        return LaneObservation(
            lane_mask=lane_mask,
            guide_pixels=guide,
            debug_lines=[
                "YOLOP lane output: {}".format(lane_name),
                "mask pixels: {}".format(int(np.count_nonzero(lane_mask))),
                "guide pixels: {}".format(len(guide)),
            ],
        )


class UFLDAdapter(object):
    name = "ufld"

    def __init__(
        self,
        onnx_path,
        input_width=DEFAULT_UFLD_WIDTH,
        input_height=DEFAULT_UFLD_HEIGHT,
        confidence=0.45,
        dataset="auto",
        crop_ratio=DEFAULT_UFLD_CROP_RATIO,
        normalize="imagenet",
    ):
        self.session = make_session(onnx_path)
        self.input_meta = self.session.get_inputs()[0]
        self.output_meta = self.session.get_outputs()
        self.input_name = self.input_meta.name
        self.input_width = input_width
        self.input_height = input_height
        self.confidence = confidence
        self.dataset = infer_ufld_dataset(onnx_path, input_width, input_height) if dataset == "auto" else dataset
        self.crop_ratio = crop_ratio
        self.normalize = normalize

    def predict(self, bgr):
        image_h, image_w = bgr.shape[:2]
        rgb = bgr[:, :, ::-1]
        resized = resize_crop_bottom_rgb(rgb, self.input_width, self.input_height, self.crop_ratio)
        tensor = normalize_image(resized, self.normalize)
        outputs = self.session.run(None, {self.input_name: tensor})
        output_names = [meta.name for meta in self.output_meta]
        shapes = output_shapes(self.output_meta, outputs)

        (
            loc_row,
            loc_name,
            exist_row,
            exist_name,
            loc_col,
            loc_col_name,
            exist_col,
            exist_col_name,
        ) = find_ufld_outputs(output_names, outputs)
        if loc_row is None or exist_row is None:
            return LaneObservation(
                guide_pixels=[],
                debug_lines=["loc_row/exist_row not found", "outputs: {}".format("; ".join(shapes)[:160])],
            )

        lanes = decode_ufld_lanes(
            loc_row,
            exist_row,
            loc_col,
            exist_col,
            image_w,
            image_h,
            dataset=self.dataset,
            confidence=self.confidence,
        )
        guide = select_nearest_lane(lanes, image_w, image_h)
        return LaneObservation(
            lane_points=lanes,
            guide_pixels=guide,
            debug_lines=[
                "UFLD row: {} | col: {}".format(loc_name, loc_col_name or "none"),
                "lanes: {} | guide pixels: {}".format(len(lanes), len(guide)),
                "dataset: {} | crop ratio: {}".format(self.dataset, self.crop_ratio),
            ],
        )


def draw_overlay(bgr, obs, show_guide=True, alpha=0.45):
    out = bgr.copy()

    if obs.lane_mask is not None:
        mask = np.asarray(obs.lane_mask).astype(bool)
        color = np.zeros_like(out)
        color[mask] = (255, 190, 0)
        out = cv2.addWeighted(out, 1.0, color, alpha, 0.0)

    if obs.lane_points:
        for lane in obs.lane_points:
            if len(lane) >= 2:
                cv2.polylines(out, [np.array(lane, dtype=np.int32)], False, (60, 230, 60), 3)
            for point in lane[:: max(1, len(lane) // 18)]:
                cv2.circle(out, tuple(point), 3, (10, 120, 20), -1)

    if show_guide and obs.guide_pixels:
        pts = np.array(obs.guide_pixels, dtype=np.int32)
        if len(pts) >= 2:
            cv2.polylines(out, [pts], False, (255, 255, 255), 3)
        for point in obs.guide_pixels:
            cv2.circle(out, tuple(point), 4, (255, 255, 255), -1)

    y = 28
    for line in (obs.debug_lines or [])[:5]:
        cv2.putText(out, line, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 3, cv2.LINE_AA)
        cv2.putText(out, line, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
        y += 28

    return out


def make_adapters(args):
    adapters = []
    if args.model in ("yolop", "both"):
        adapters.append(
            YOLOPAdapter(
                args.yolop_onnx,
                input_width=args.yolop_width,
                input_height=args.yolop_height,
                threshold=args.yolop_threshold,
                normalize=args.normalize,
            )
        )
    if args.model in ("ufld", "both"):
        adapters.append(
            UFLDAdapter(
                args.ufld_onnx,
                input_width=args.ufld_width,
                input_height=args.ufld_height,
                confidence=args.ufld_confidence,
                dataset=args.ufld_dataset,
                crop_ratio=args.ufld_crop_ratio,
                normalize=args.normalize,
            )
        )
    return adapters


def output_name(input_path, adapter_name, suffix):
    stem = input_path.stem
    return "{}__{}{}".format(stem, adapter_name, suffix)


def process_image(path, adapters, output_dir, show_guide):
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        print("Skip unreadable image:", path)
        return []

    outputs = []
    for adapter in adapters:
        obs = adapter.predict(bgr)
        annotated = draw_overlay(bgr, obs, show_guide=show_guide)
        out_path = output_dir / output_name(path, adapter.name, "_annotated.png")
        cv2.imwrite(str(out_path), annotated)
        outputs.append(out_path)
        print("Image {} -> {}".format(path.name, out_path))
    return outputs


def process_video(path, adapters, output_dir, show_guide, every=1, limit=0):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        print("Skip unreadable video:", path)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 1e-3:
        fps = 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    writers = {}
    last_obs = {}
    outputs = []
    for adapter in adapters:
        out_path = output_dir / output_name(path, adapter.name, "_annotated.mp4")
        writers[adapter.name] = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))
        outputs.append(out_path)

    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if limit and frame_idx >= limit:
            break

        for adapter in adapters:
            if frame_idx % max(1, every) == 0 or adapter.name not in last_obs:
                last_obs[adapter.name] = adapter.predict(frame)
            annotated = draw_overlay(frame, last_obs[adapter.name], show_guide=show_guide)
            writers[adapter.name].write(annotated)

        frame_idx += 1
        if frame_idx % 60 == 0:
            print("Video {} processed {} frames".format(path.name, frame_idx))

    cap.release()
    for writer in writers.values():
        writer.release()

    print("Video {} done, frames: {}".format(path.name, frame_idx))
    for path_out in outputs:
        print("  ->", path_out)
    return outputs


def write_run_metadata(output_dir, args, inputs, outputs):
    meta = {
        "args": vars(args),
        "inputs": [str(p) for p in inputs],
        "outputs": [str(p) for p in outputs],
        "created_at": timestamp(),
    }
    path = output_dir / "run_meta.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf8")


def run_offline(args):
    ensure_runtime()
    inputs = collect_inputs(args.input, args.capture_root)
    if not inputs:
        raise RuntimeError("No image/video inputs found.")

    output_dir = make_output_dir(args.output_root)
    adapters = make_adapters(args)
    print("Inputs:", len(inputs))
    print("Output:", output_dir)
    print("Models:", ", ".join(adapter.name for adapter in adapters))

    if args.model in ("yolop", "both"):
        print("YOLOP ONNX:", args.yolop_onnx)
        print("YOLOP input (HxW): {}x{}".format(args.yolop_height, args.yolop_width))
    if args.model in ("ufld", "both"):
        print("UFLD ONNX:", args.ufld_onnx)
        print("UFLD input (HxW): {}x{}".format(args.ufld_height, args.ufld_width))
        print("UFLD dataset/crop:", args.ufld_dataset, args.ufld_crop_ratio)

    all_outputs = []
    for path in inputs:
        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTS:
            all_outputs.extend(process_image(path, adapters, output_dir, args.show_guide))
        elif suffix in VIDEO_EXTS:
            all_outputs.extend(process_video(path, adapters, output_dir, args.show_guide, args.every, args.limit))
        else:
            print("Skip unsupported file:", path)

    write_run_metadata(output_dir, args, inputs, all_outputs)
    print("Done. Output dir:", output_dir)
    return output_dir, all_outputs


def parse_args():
    parser = argparse.ArgumentParser(
        description="Offline lane detection on captured images/videos.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--model", choices=["yolop", "ufld", "both"], default="yolop")
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

    parser.add_argument("--ufld-onnx", default=str(DEFAULT_UFLD_ONNX))
    parser.add_argument("--ufld-width", type=int, default=DEFAULT_UFLD_WIDTH)
    parser.add_argument("--ufld-height", type=int, default=DEFAULT_UFLD_HEIGHT)
    parser.add_argument("--ufld-confidence", type=float, default=0.45)
    parser.add_argument("--ufld-dataset", choices=["auto", "tusimple", "culane", "curvelanes"], default="auto")
    parser.add_argument("--ufld-crop-ratio", type=float, default=DEFAULT_UFLD_CROP_RATIO)
    return parser.parse_args()


def main():
    args = parse_args()
    run_offline(args)


if __name__ == "__main__":
    main()
