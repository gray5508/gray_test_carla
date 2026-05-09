"""
lane_demo_common.py

Shared CARLA + pygame helpers for the YOLOP and UFLD-v2 lane demos.

The demo pipeline is intentionally simple:
  camera image -> model adapter -> lane points / lane mask -> centerline pixels
  -> ground point in CARLA world -> plain direction line overlay.

These scripts are meant as a hackable starting point, not a production
autonomous-driving stack.
"""

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np


THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
TUTORIAL_DIR = PROJECT_ROOT / "carla_from_zero_to_ar_tutorial"
if str(TUTORIAL_DIR) not in sys.path:
    sys.path.insert(0, str(TUTORIAL_DIR))


from common import CAMERA_FOV  # noqa: E402
from common import CameraSensor  # noqa: E402
from common import build_camera_intrinsic_k  # noqa: E402
from common import connect_to_carla  # noqa: E402
from common import destroy_actors  # noqa: E402
from common import draw_text_lines  # noqa: E402
from common import get_ground_z  # noqa: E402
from common import get_keyboard_vehicle_control  # noqa: E402
from common import ground_point_in_vehicle_frame  # noqa: E402
from common import make_pygame_surface  # noqa: E402
from common import pixel_to_world_on_ground  # noqa: E402
from common import spawn_ego_vehicle  # noqa: E402
from common import world_to_pixel  # noqa: E402


DEMO_WIDTH = 960
DEMO_HEIGHT = 540


try:
    import cv2
except ImportError:  # pragma: no cover - optional dependency
    cv2 = None


@dataclass
class LaneObservation:
    """Model output after being normalized into demo-friendly geometry."""

    lane_mask: object = None
    lane_points: object = None
    center_pixels: object = None
    debug_lines: object = None


def add_common_args(parser):
    parser.add_argument("--width", type=int, default=DEMO_WIDTH)
    parser.add_argument("--height", type=int, default=DEMO_HEIGHT)
    parser.add_argument("--max-fps", type=int, default=60)
    parser.add_argument("--infer-every", type=int, default=2)
    parser.add_argument("--start-forward", type=float, default=5.0)
    parser.add_argument("--target-forward", type=float, default=18.0)
    parser.add_argument("--target-mode", choices=["turn", "farthest", "nearest"], default="turn")
    parser.add_argument("--turn-right-threshold", type=float, default=1.0)
    parser.add_argument("--line-width", type=int, default=5)
    parser.add_argument("--show-guide", action="store_true", help="Draw the selected white guide line.")
    parser.add_argument("--hide-target-line", action="store_true", help="Hide the yellow world-space target line.")
    parser.add_argument("--hide-model-overlay", action="store_true", help="Hide raw model lane mask / lane points.")
    parser.add_argument("--mock", action="store_true", help="Run with synthetic lanes and no model.")
    parser.add_argument("--mock-turn", choices=["left", "right", "straight"], default="left")


def import_onnxruntime():
    try:
        import onnxruntime as ort
    except ImportError:
        raise RuntimeError(
            "onnxruntime is not installed. Install it with: pip install onnxruntime"
        )
    return ort


def make_onnx_session(onnx_path):
    if not onnx_path:
        raise RuntimeError("Please pass --onnx path/to/model.onnx, or use --mock.")
    if not os.path.isfile(onnx_path):
        raise RuntimeError("ONNX model not found: {}".format(onnx_path))

    ort = import_onnxruntime()
    available = ort.get_available_providers()
    providers = []
    if "CUDAExecutionProvider" in available:
        providers.append("CUDAExecutionProvider")
    providers.append("CPUExecutionProvider")
    return ort.InferenceSession(onnx_path, providers=providers)


def resize_rgb(rgb, width, height):
    if cv2 is not None:
        return cv2.resize(rgb, (width, height), interpolation=cv2.INTER_LINEAR)

    # Nearest-neighbor fallback keeps the demo dependency-light.
    src_h, src_w = rgb.shape[:2]
    y_idx = (np.linspace(0, src_h - 1, height)).astype(np.int32)
    x_idx = (np.linspace(0, src_w - 1, width)).astype(np.int32)
    return rgb[y_idx][:, x_idx]


def resize_mask(mask, width, height):
    mask = mask.astype(np.uint8)
    if cv2 is not None:
        resized = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
        return resized.astype(bool)

    src_h, src_w = mask.shape[:2]
    y_idx = (np.linspace(0, src_h - 1, height)).astype(np.int32)
    x_idx = (np.linspace(0, src_w - 1, width)).astype(np.int32)
    return mask[y_idx][:, x_idx].astype(bool)


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
    """
    Convert a generic segmentation tensor to a boolean mask.

    Supports common ONNX layouts:
      [1, 2, H, W] class logits
      [1, 1, H, W] foreground logits/probabilities
      [1, H, W]
      [H, W]
    """
    arr = np.asarray(output)
    if arr.ndim == 4:
        arr = arr[0]
        if arr.shape[0] == 2:
            return np.argmax(arr, axis=0) == 1
        if arr.shape[0] == 1:
            arr = arr[0]
        else:
            # For odd exports, use the last channel as foreground.
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


def centerline_from_lane_mask(mask, sample_count=18):
    """
    Estimate lane center pixels from a lane-line mask.

    This is intentionally simple: for each sampled image row, look for lane pixels
    left and right of image center and take their midpoint.
    """
    if mask is None:
        return []

    mask = np.asarray(mask).astype(bool)
    h, w = mask.shape[:2]
    ys = np.linspace(int(h * 0.88), int(h * 0.35), sample_count).astype(np.int32)
    centers = []

    for y in ys:
        y0 = max(0, y - 2)
        y1 = min(h, y + 3)
        xs = np.where(mask[y0:y1].any(axis=0))[0]
        if len(xs) < 2:
            continue

        left = xs[xs < w * 0.5]
        right = xs[xs >= w * 0.5]
        if len(left) > 0 and len(right) > 0:
            center_x = 0.5 * (left.max() + right.min())
        else:
            center_x = float(np.mean(xs))
        centers.append((int(center_x), int(y)))

    return centers


def nearest_line_from_lane_mask(mask, sample_count=24):
    """
    Pick the lane-line pixels closest to image center.

    This is useful for early testing where we only want the current visible lane
    boundary/guide line, not an averaged center between multiple lanes.
    """
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


def select_nearest_lane(lanes, width, height):
    """
    Select the detected lane polyline whose nearest/bottom visible point is
    closest to image center.
    """
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


def centerline_from_lane_points(lanes, width, height, sample_count=18):
    if not lanes:
        return []

    ys = np.linspace(int(height * 0.88), int(height * 0.35), sample_count)
    centers = []

    prepared = []
    for lane in lanes:
        if len(lane) < 2:
            continue
        points = np.array(lane, dtype=np.float32)
        order = np.argsort(points[:, 1])
        xs = points[order, 0]
        lane_ys = points[order, 1]
        if lane_ys[-1] - lane_ys[0] < 2:
            continue
        prepared.append((xs, lane_ys))

    for y in ys:
        x_values = []
        for xs, lane_ys in prepared:
            if y < lane_ys[0] or y > lane_ys[-1]:
                continue
            x_values.append(float(np.interp(y, lane_ys, xs)))

        if not x_values:
            continue

        x_values = np.array(x_values)
        left = x_values[x_values < width * 0.5]
        right = x_values[x_values >= width * 0.5]
        if len(left) > 0 and len(right) > 0:
            center_x = 0.5 * (left.max() + right.min())
        else:
            center_x = float(np.mean(x_values))
        centers.append((int(center_x), int(y)))

    return centers


def world_location_to_vehicle_local(vehicle_transform, location):
    inv = np.array(vehicle_transform.get_inverse_matrix())
    point = np.array([location.x, location.y, location.z, 1.0], dtype=float)
    return np.dot(inv, point)


def choose_direction_target_world(
    world,
    vehicle,
    camera,
    k,
    guide_pixels,
    start_forward,
    target_forward,
    target_mode="turn",
    turn_right_threshold=1.0,
):
    """
    Convert guide pixels to ground-plane world points and choose a target.

    target_mode:
      nearest  -> point closest to target_forward
      farthest -> farthest usable point
      turn     -> first point whose lateral offset changes enough; fallback farthest
    """
    if not guide_pixels:
        return None, None

    vehicle_tf = vehicle.get_transform()
    camera_tf = camera.get_transform()
    ground_z = get_ground_z(world, vehicle_tf.location) + 0.04
    candidates = []

    for u, v in guide_pixels:
        hit = pixel_to_world_on_ground(u, v, camera_tf, k, ground_z)
        if hit is None:
            continue
        local = world_location_to_vehicle_local(vehicle_tf, hit)
        forward = float(local[0])
        right = float(local[1])
        if forward < start_forward + 0.5 or forward > 40.0:
            continue
        if abs(right) > 20.0:
            continue
        candidates.append((forward, right, hit, local))

    if not candidates:
        return None, None

    candidates.sort(key=lambda item: item[0])

    if target_mode == "nearest":
        target = min(candidates, key=lambda item: abs(item[0] - target_forward))
    elif target_mode == "turn":
        near = candidates[0]
        near_right = near[1]
        target = candidates[-1]
        for item in candidates:
            forward, right, _, _ = item
            if forward < start_forward + 2.0:
                continue
            if abs(right - near_right) >= turn_right_threshold:
                target = item
                break
    else:
        target = candidates[-1]

    _, _, target_world, target_local = target
    return target_world, target_local


def draw_plain_world_direction_line(
    pygame_module,
    display,
    world,
    vehicle,
    camera,
    k,
    target_world,
    start_forward,
    line_width,
):
    if target_world is None:
        return False

    start = ground_point_in_vehicle_frame(world, vehicle, start_forward, 0.0)
    start_pixel = world_to_pixel(
        start,
        camera.get_transform(),
        k,
        display.get_width(),
        display.get_height(),
        margin=160.0,
    )
    end_pixel = world_to_pixel(
        target_world,
        camera.get_transform(),
        k,
        display.get_width(),
        display.get_height(),
        margin=160.0,
    )
    if start_pixel is None or end_pixel is None:
        return False

    p0 = (int(start_pixel[0]), int(start_pixel[1]))
    p1 = (int(end_pixel[0]), int(end_pixel[1]))
    pygame_module.draw.line(display, (20, 20, 20), p0, p1, max(1, line_width + 4))
    pygame_module.draw.line(display, (255, 205, 35), p0, p1, max(1, line_width))
    pygame_module.draw.circle(display, (255, 205, 35), p1, max(5, line_width + 2))
    return True


def draw_observation_overlay(pygame_module, display, observation, show_model_overlay=True, show_guide=False):
    if observation is None:
        return

    if show_model_overlay and observation.lane_mask is not None:
        mask = np.asarray(observation.lane_mask).astype(bool)
        color = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
        color[mask] = (0, 190, 255)
        overlay = make_pygame_surface(pygame_module, color)
        overlay.set_colorkey((0, 0, 0))
        overlay.set_alpha(75)
        display.blit(overlay, (0, 0))

    if show_model_overlay and observation.lane_points:
        for lane in observation.lane_points:
            if len(lane) >= 2:
                pygame_module.draw.lines(display, (40, 220, 80), False, lane, 3)
            for point in lane[:: max(1, len(lane) // 18)]:
                pygame_module.draw.circle(display, (10, 80, 20), point, 3)

    if show_guide and observation.center_pixels:
        pts = observation.center_pixels
        if len(pts) >= 2:
            pygame_module.draw.lines(display, (255, 255, 255), False, pts, 3)
        for point in pts:
            pygame_module.draw.circle(display, (255, 255, 255), point, 4)


class MockLaneAdapter(object):
    name = "mock synthetic lane"

    def __init__(self, turn="left"):
        self.turn = turn

    def predict(self, rgb):
        h, w = rgb.shape[:2]
        if self.turn == "left":
            turn_scale = -0.18
        elif self.turn == "right":
            turn_scale = 0.18
        else:
            turn_scale = 0.0

        ys = np.linspace(int(h * 0.9), int(h * 0.35), 28)
        left_lane = []
        right_lane = []
        centers = []
        for idx, y in enumerate(ys):
            t = idx / max(1, len(ys) - 1)
            center = w * 0.5 + turn_scale * (t ** 1.6) * w
            lane_half_width = w * (0.22 - 0.08 * t)
            left_lane.append((int(center - lane_half_width), int(y)))
            right_lane.append((int(center + lane_half_width), int(y)))
            centers.append((int(center), int(y)))

        return LaneObservation(
            lane_points=[centers],
            center_pixels=centers,
            debug_lines=["mock guide line turn: {}".format(self.turn)],
        )


def run_carla_lane_demo(adapter, args, title):
    import pygame

    pygame.init()
    pygame.font.init()

    display = pygame.display.set_mode((args.width, args.height))
    pygame.display.set_caption(title)
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    k = build_camera_intrinsic_k(args.width, args.height, CAMERA_FOV)
    client, world = connect_to_carla()
    actors = []
    current_steer = 0.0
    observation = None
    infer_error = None
    frame_index = 0

    try:
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        camera = CameraSensor(
            world,
            vehicle,
            "sensor.camera.rgb",
            width=args.width,
            height=args.height,
        )
        actors.append(camera.actor)

        running = True
        while running:
            clock.tick(max(1, args.max_fps))
            frame_index += 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
                    running = False

            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            if camera.latest_rgb is not None:
                image = camera.latest_rgb
                if frame_index % max(1, args.infer_every) == 0:
                    try:
                        observation = adapter.predict(image)
                        infer_error = None
                    except Exception as exc:  # Keep the window alive while tuning adapters.
                        infer_error = "{}: {}".format(type(exc).__name__, exc)

                display.blit(make_pygame_surface(pygame, image), (0, 0))
            else:
                display.fill((10, 10, 10))

            draw_observation_overlay(
                pygame,
                display,
                observation,
                show_model_overlay=not args.hide_model_overlay,
                show_guide=args.show_guide,
            )

            target_world = None
            target_local = None
            if observation is not None and observation.center_pixels:
                target_world, target_local = choose_direction_target_world(
                    world,
                    vehicle,
                    camera,
                    k,
                    observation.center_pixels,
                    args.start_forward,
                    args.target_forward,
                    target_mode=args.target_mode,
                    turn_right_threshold=args.turn_right_threshold,
                )
                if not args.hide_target_line:
                    draw_plain_world_direction_line(
                        pygame,
                        display,
                        world,
                        vehicle,
                        camera,
                        k,
                        target_world,
                        args.start_forward,
                        args.line_width,
                    )

            hud = [
                "{} | ESC quit | W/A/S/D drive".format(title),
                "adapter: {}".format(adapter.name),
                "camera: {}x{} | max fps {} | infer every {} frame(s)".format(
                    args.width, args.height, args.max_fps, max(1, args.infer_every)
                ),
                "overlay: model={} guide={} target_line={}".format(
                    not args.hide_model_overlay,
                    args.show_guide,
                    not args.hide_target_line,
                ),
            ]
            if observation is not None:
                hud.append("guide pixels: {}".format(len(observation.center_pixels or [])))
                for line in (observation.debug_lines or [])[:3]:
                    hud.append(line)
            if target_local is not None:
                hud.append(
                    "line target vehicle frame: x={:.2f}m y={:.2f}m".format(
                        target_local[0], target_local[1]
                    )
                )
            else:
                hud.append("line target: waiting for usable guide line")
            if infer_error:
                hud.append("infer error: {}".format(infer_error[:120]))

            draw_text_lines(pygame, display, font, hud)
            pygame.display.flip()

    finally:
        destroy_actors(actors)
        pygame.quit()
        print("Cleaned up.")


def build_base_parser(description):
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_args(parser)
    return parser
