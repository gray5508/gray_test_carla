"""
carla_yolop_ground_arrow_demo.py

Realtime CARLA + YOLOP lane-segmentation navigation hint demo with a
ground-projected AR arrow.

This version separates "navigation intent" from "vision detection":
  - You press a key to say the intended route: straight / left / right.
  - YOLOP only checks whether the current lane geometry supports that intent.
  - A stable arrow is locked for a few seconds, so it behaves like a navigation
    hint instead of a per-frame model visualization.

No CARLA waypoints are used.

Controls:
  W/A/S/D or arrow keys : drive
  1                    : navigation intent = straight
  2                    : navigation intent = left
  3                    : navigation intent = right
  C or 0               : clear navigation intent and arrow
  M                    : toggle debug geometry
  ESC                  : quit
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pygame


THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
TUTORIAL_DIR = PROJECT_ROOT / "carla_from_zero_to_ar_tutorial"
if str(TUTORIAL_DIR) not in sys.path:
    sys.path.insert(0, str(TUTORIAL_DIR))


import offline_lane_detect as lane  # noqa: E402


# common.py imports numpy immediately. Prepare the conda DLL path first so
# direct launches with envs\carla_test\python.exe work on Windows.
lane.prepare_windows_dll_search_path()


from common import CAMERA_FOV  # noqa: E402
from common import CameraSensor  # noqa: E402
from common import build_camera_intrinsic_k  # noqa: E402
from common import connect_to_carla  # noqa: E402
from common import destroy_actors  # noqa: E402
from common import DRIVER_CAMERA_TRANSFORM  # noqa: E402
from common import draw_text_lines  # noqa: E402
from common import get_keyboard_vehicle_control  # noqa: E402
from common import make_pygame_surface  # noqa: E402
from common import spawn_ego_vehicle  # noqa: E402

from offline_yolop_turn_experiment import estimate_current_lane  # noqa: E402


DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
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


def set_world_async(world):
    original_settings = world.get_settings()
    if original_settings.synchronous_mode:
        settings = world.get_settings()
        settings.synchronous_mode = False
        settings.fixed_delta_seconds = None
        world.apply_settings(settings)
        print("World was synchronous; switched to asynchronous mode.")
    else:
        print("World is already asynchronous.")
    return original_settings


def fmt_point(point):
    if not point:
        return "-"
    return "({}, {})".format(int(point[0]), int(point[1]))


def point_distance(a, b):
    dx = float(a[0] - b[0])
    dy = float(a[1] - b[1])
    return (dx * dx + dy * dy) ** 0.5


def mean_point(points):
    if not points:
        return None
    x = sum(point[0] for point in points) / float(len(points))
    y = sum(point[1] for point in points) / float(len(points))
    return int(x), int(y)


def blend_points(old, new, alpha):
    return (
        int(round((1.0 - alpha) * old[0] + alpha * new[0])),
        int(round((1.0 - alpha) * old[1] + alpha * new[1])),
    )


def closest_point_by_y(points, target_y):
    if not points:
        return None
    return min(points, key=lambda point: abs(point[1] - target_y))


def pixel_to_vehicle_ground(point, args):
    k = getattr(args, "camera_k", None)
    camera_mount = getattr(args, "camera_mount_transform", None)
    if k is None or camera_mount is None:
        return None

    u, v = point
    fx = k[0, 0]
    fy = k[1, 1]
    cx = k[0, 2]
    cy = k[1, 2]

    ray_cv = lane.np.array([(u - cx) / fx, (v - cy) / fy, 1.0], dtype=float)
    # OpenCV camera: x right, y down, z forward.
    # CARLA/UE camera: x forward, y right, z up.
    ray_ue = lane.np.array([ray_cv[2], ray_cv[0], -ray_cv[1]], dtype=float)

    camera_to_vehicle = lane.np.array(camera_mount.get_matrix())
    origin = lane.np.dot(camera_to_vehicle, lane.np.array([0.0, 0.0, 0.0, 1.0], dtype=float))
    ray_point = lane.np.dot(
        camera_to_vehicle,
        lane.np.array([ray_ue[0], ray_ue[1], ray_ue[2], 1.0], dtype=float),
    )
    direction = ray_point - origin
    if abs(direction[2]) < 1e-8:
        return None

    ground_z = getattr(args, "vehicle_ground_z", 0.0)
    scale = (ground_z - origin[2]) / direction[2]
    if scale <= 0.0:
        return None

    hit = origin + scale * direction
    return float(hit[0]), float(hit[1])


def vehicle_ground_to_pixel(forward_m, right_m, args, width, height):
    k = getattr(args, "camera_k", None)
    camera_mount = getattr(args, "camera_mount_transform", None)
    if k is None or camera_mount is None:
        return None

    vehicle_to_camera = lane.np.array(camera_mount.get_inverse_matrix())
    ground_z = getattr(args, "vehicle_ground_z", 0.0)
    point_vehicle = lane.np.array([forward_m, right_m, ground_z, 1.0], dtype=float)
    point_ue = lane.np.dot(vehicle_to_camera, point_vehicle)
    point_cv = lane.np.array([point_ue[1], -point_ue[2], point_ue[0]], dtype=float)
    if point_cv[2] <= 0.05:
        return None

    projected = lane.np.dot(k, point_cv)
    u = projected[0] / projected[2]
    v = projected[1] / projected[2]
    if u < 0 or u >= width or v < 0 or v >= height:
        return None
    return int(u), int(v)


def project_vehicle_ground_to_pixel(forward_m, right_m, args):
    k = getattr(args, "camera_k", None)
    camera_mount = getattr(args, "camera_mount_transform", None)
    if k is None or camera_mount is None:
        return None

    vehicle_to_camera = lane.np.array(camera_mount.get_inverse_matrix())
    ground_z = getattr(args, "vehicle_ground_z", 0.0)
    point_vehicle = lane.np.array([forward_m, right_m, ground_z, 1.0], dtype=float)
    point_ue = lane.np.dot(vehicle_to_camera, point_vehicle)
    point_cv = lane.np.array([point_ue[1], -point_ue[2], point_ue[0]], dtype=float)
    if point_cv[2] <= 0.05:
        return None

    projected = lane.np.dot(k, point_cv)
    u = projected[0] / projected[2]
    v = projected[1] / projected[2]
    if not lane.np.isfinite(u) or not lane.np.isfinite(v):
        return None
    return float(u), float(v)


def clamp_projected_pixel(point, width, height, margin=4000):
    x, y = point
    x = max(-margin, min(width + margin, float(x)))
    y = max(-margin, min(height + margin, float(y)))
    return int(round(x)), int(round(y))


def project_ground_polygon(points, args, width, height):
    projected = []
    for forward_m, right_m in points:
        pixel = project_vehicle_ground_to_pixel(forward_m, right_m, args)
        if pixel is None:
            return None
        projected.append(clamp_projected_pixel(pixel, width, height))
    return lane.np.asarray(projected, dtype=lane.np.int32)


def arrow_start_pixel(width, height, args):
    metric_start = vehicle_ground_to_pixel(args.arrow_start_meters, 0.0, args, width, height)
    if metric_start is not None:
        return metric_start
    return (
        int(width * args.vehicle_x_ratio),
        int(height * args.arrow_start_y_ratio),
    )


def straight_right_meters(args):
    if args.straight_right_meters is not None:
        return float(args.straight_right_meters)

    camera_mount = getattr(args, "camera_mount_transform", None)
    if camera_mount is not None:
        return float(camera_mount.location.y)
    return 0.0


def straight_arrow_start_pixel(width, height, args):
    metric_start = vehicle_ground_to_pixel(
        args.arrow_start_meters,
        straight_right_meters(args),
        args,
        width,
        height,
    )
    if metric_start is not None:
        return metric_start
    return arrow_start_pixel(width, height, args)


def points_with_forward_distance(points, args):
    measured = []
    for point in points or []:
        hit = pixel_to_vehicle_ground(point, args)
        if hit is None:
            continue
        forward_m, right_m = hit
        measured.append((forward_m, right_m, point))
    return measured


def valid_target_points(points, args):
    min_forward = args.arrow_start_meters + args.min_arrow_length_meters
    max_forward = args.max_target_forward_meters
    measured = points_with_forward_distance(points, args)
    return [
        item
        for item in measured
        if min_forward <= item[0] <= max_forward
    ]


def classify_geometry(points, start, width, height, args):
    if not points or start is None:
        return "unknown", 0.0, None

    candidates = valid_target_points(points, args)
    if candidates:
        _, _, target = max(candidates, key=lambda item: item[0])
    else:
        target = closest_point_by_y(points, height * args.turn_target_y_ratio)
        if target is None:
            target = points[-1]

    dx = float(target[0] - start[0])
    shift = abs(dx) / float(max(1, width))
    if shift < args.turn_shift_ratio:
        return NAV_STRAIGHT, shift, target
    if dx < 0:
        return NAV_LEFT, shift, target
    return NAV_RIGHT, shift, target


def choose_straight_target(points, start, width, height, args):
    # Straight navigation should look straight in the image: draw the fixed
    # vehicle-forward line from about 5m to 10m, and only allow it when YOLOP's
    # current-lane geometry supports that line.
    target = vehicle_ground_to_pixel(
        args.straight_target_forward_meters,
        straight_right_meters(args),
        args,
        width,
        height,
    )
    if target is None:
        return None
    return target


def interpolate_x_at_y(points, y):
    if not points:
        return None

    ordered = sorted(points, key=lambda point: point[1])
    if y < ordered[0][1] or y > ordered[-1][1]:
        return None

    for idx in range(len(ordered) - 1):
        x0, y0 = ordered[idx]
        x1, y1 = ordered[idx + 1]
        if y0 == y1:
            continue
        if y0 <= y <= y1 or y1 <= y <= y0:
            ratio = (float(y) - y0) / float(y1 - y0)
            return float(x0) + ratio * float(x1 - x0)
    return None


def point_on_line(start, target, ratio):
    x = float(start[0]) + ratio * float(target[0] - start[0])
    y = float(start[1]) + ratio * float(target[1] - start[1])
    return x, y


def straight_line_inside_current_lane(result, start, target, width, args):
    if result is None:
        return False

    center_points = result.smooth_center or result.center_points or []
    if len(center_points) < args.min_center_points:
        return False

    sample_count = max(3, int(args.straight_validation_samples))
    sample_ratios = lane.np.linspace(0.0, 1.0, sample_count)
    accepted = 0
    checked = 0

    for ratio in sample_ratios:
        x, y = point_on_line(start, target, ratio)
        left_x = interpolate_x_at_y(result.left_points, y)
        right_x = interpolate_x_at_y(result.right_points, y)

        if left_x is not None and right_x is not None and abs(right_x - left_x) >= args.min_lane_width_px:
            low = min(left_x, right_x) + args.straight_boundary_margin_px
            high = max(left_x, right_x) - args.straight_boundary_margin_px
            if low > high:
                low, high = min(left_x, right_x), max(left_x, right_x)
            checked += 1
            if low <= x <= high:
                accepted += 1
            continue

        center_x = interpolate_x_at_y(center_points, y)
        if center_x is not None:
            checked += 1
            if abs(x - center_x) <= width * args.straight_center_tolerance_ratio:
                accepted += 1

    if checked < args.min_straight_validation_checks:
        return False
    return accepted / float(checked) >= args.straight_validation_ratio


def choose_turn_target(points, start, width, height, nav_mode, args):
    if not points:
        return None, "unknown", 0.0

    candidates = []
    for forward_m, right_m, point in valid_target_points(points, args):
        dx = float(point[0] - start[0])
        shift = abs(dx) / float(max(1, width))
        if nav_mode == NAV_LEFT and dx < 0 and shift >= args.turn_min_shift_ratio:
            candidates.append((forward_m, shift, point))
        elif nav_mode == NAV_RIGHT and dx > 0 and shift >= args.turn_min_shift_ratio:
            candidates.append((forward_m, shift, point))

    if candidates:
        forward_m, shift, target = max(candidates, key=lambda item: item[0])
        return target, nav_mode, shift

    direction, shift, target = classify_geometry(points, start, width, height, args)
    if direction != nav_mode:
        return None, direction, shift
    if shift < args.turn_min_shift_ratio:
        return None, direction, shift
    return target, direction, shift


class NavigationArrowTracker(object):
    def __init__(self, args):
        self.args = args
        self.nav_mode = NAV_NONE
        self.candidates = []
        self.locked = None
        self.last_status = "choose 1/2/3"

    def set_nav_mode(self, nav_mode):
        if nav_mode != self.nav_mode:
            self.nav_mode = nav_mode
            self.candidates = []
            self.locked = None
            self.last_status = "nav set to {}".format(nav_mode)

    def clear(self):
        self.nav_mode = NAV_NONE
        self.candidates = []
        self.locked = None
        self.last_status = "cleared"

    def active_arrow(self, now):
        if self.locked is None:
            return None
        if now > self.locked.expires_at:
            return None
        if self.locked.nav_mode != self.nav_mode:
            return None
        return self.locked

    def push(self, candidate, now):
        if self.nav_mode == NAV_NONE:
            self.last_status = "no navigation intent"
            return self.active_arrow(now)
        if candidate is None:
            self.last_status = "no {} geometry yet".format(self.nav_mode)
            return self.active_arrow(now)
        if candidate.nav_mode != self.nav_mode:
            self.last_status = "candidate does not match nav"
            return self.active_arrow(now)

        self.candidates.append(candidate)
        self.candidates = [
            item
            for item in self.candidates
            if now - item.created_at <= self.args.stability_window_seconds
            and item.nav_mode == self.nav_mode
        ][-self.args.max_candidate_history :]

        if len(self.candidates) < self.args.stability_confirmations:
            self.last_status = "collecting {} stable samples {}/{}".format(
                self.nav_mode,
                len(self.candidates),
                self.args.stability_confirmations,
            )
            return self.active_arrow(now)

        recent = self.candidates[-self.args.stability_confirmations :]
        target_mean = mean_point([item.target for item in recent])
        start_mean = mean_point([item.start for item in recent])
        if target_mean is None or start_mean is None:
            self.last_status = "candidate mean failed"
            return self.active_arrow(now)

        max_spread = max(point_distance(item.target, target_mean) for item in recent)
        if max_spread > self.args.stable_target_radius:
            self.last_status = "{} target unstable {:.0f}px".format(self.nav_mode, max_spread)
            return self.active_arrow(now)

        confidence = sum(item.confidence for item in recent) / float(len(recent))
        if self.locked is not None and now <= self.locked.expires_at:
            start = blend_points(self.locked.start, start_mean, self.args.arrow_smoothing_alpha)
            target = blend_points(self.locked.target, target_mean, self.args.arrow_smoothing_alpha)
        else:
            start = start_mean
            target = target_mean

        self.locked = LockedNavArrow(
            nav_mode=self.nav_mode,
            start=start,
            target=target,
            confidence=confidence,
            locked_at=now,
            expires_at=now + self.args.arrow_hold_seconds,
        )
        self.last_status = "locked {} for {:.1f}s".format(self.nav_mode, self.args.arrow_hold_seconds)
        return self.locked


def make_turn_args(args):
    class TurnArgs(object):
        pass

    turn_args = TurnArgs()
    turn_args.roi_top_ratio = args.roi_top_ratio
    turn_args.scan_top_ratio = args.scan_top_ratio
    turn_args.scan_bottom_ratio = args.scan_bottom_ratio
    turn_args.scan_rows = args.scan_rows
    turn_args.scan_band = args.scan_band
    turn_args.min_segment_width = args.min_segment_width
    turn_args.max_segment_width_ratio = args.max_segment_width_ratio
    turn_args.vehicle_x_ratio = args.vehicle_x_ratio
    turn_args.initial_half_lane_width_ratio = args.initial_half_lane_width_ratio
    turn_args.max_jump_ratio = args.max_jump_ratio
    turn_args.smooth_samples = args.smooth_samples
    turn_args.arrow_start_y_ratio = args.arrow_start_y_ratio
    turn_args.turn_shift_ratio = args.turn_shift_ratio
    turn_args.target_average_points = args.target_average_points
    turn_args.min_center_points = args.min_center_points
    turn_args.min_confidence = args.min_confidence
    turn_args.draw_raw_mask = False
    return turn_args


def predict_yolop_mask(adapter, bgr):
    obs = adapter.predict(bgr)
    if obs.lane_mask is None:
        return None, obs.debug_lines or []
    return obs.lane_mask.astype(bool), obs.debug_lines or []


def make_nav_candidate(result, nav_mode, args, width, height, now):
    if nav_mode == NAV_NONE or result is None:
        return None
    if result.confidence < args.min_confidence:
        return None
    if len(result.center_points or []) < args.min_center_points:
        return None

    points = result.smooth_center or result.center_points or []

    if nav_mode == NAV_STRAIGHT:
        start = straight_arrow_start_pixel(width, height, args)
        target = choose_straight_target(points, start, width, height, args)
        if target is None:
            return None
        if not straight_line_inside_current_lane(result, start, target, width, args):
            return None
        direction = NAV_STRAIGHT
    else:
        start = arrow_start_pixel(width, height, args)
        target, direction, shift = choose_turn_target(points, start, width, height, nav_mode, args)
        if target is None:
            return None

    return NavCandidate(
        nav_mode=nav_mode,
        start=start,
        target=tuple(target),
        confidence=float(result.confidence),
        center_points=len(result.center_points or []),
        direction=direction,
        created_at=now,
    )


def run_detection(adapter, rgb, args, frame_id, nav_mode):
    started = time.time()
    try:
        bgr = rgb[:, :, ::-1].copy()
        mask, model_debug = predict_yolop_mask(adapter, bgr)
        if mask is None:
            result = EmptyResult(["YOLOP lane mask missing"] + model_debug[:2])
            candidate = None
        else:
            result = estimate_current_lane(mask, make_turn_args(args))
            candidate = make_nav_candidate(result, nav_mode, args, rgb.shape[1], rgb.shape[0], time.time())
        inference_ms = (time.time() - started) * 1000.0
        return DetectionPacket(result, candidate, inference_ms, frame_id, nav_mode)
    except Exception as exc:
        inference_ms = (time.time() - started) * 1000.0
        return DetectionPacket(None, None, inference_ms, frame_id, nav_mode, "{}: {}".format(type(exc).__name__, exc))


def draw_debug_geometry(bgr, result, args):
    if result is None:
        return bgr

    out = bgr
    if args.show_debug_mask and result.clean_mask is not None:
        color = lane.np.zeros_like(out)
        color[result.clean_mask.astype(bool)] = (255, 255, 0)
        out = lane.cv2.addWeighted(out, 1.0, color, 0.28, 0.0)

    if args.show_debug_geometry:
        if result.left_points:
            for point in result.left_points[::3]:
                lane.cv2.circle(out, tuple(point), 3, (80, 180, 255), -1, lane.cv2.LINE_AA)
        if result.right_points:
            for point in result.right_points[::3]:
                lane.cv2.circle(out, tuple(point), 3, (255, 160, 80), -1, lane.cv2.LINE_AA)
        if result.smooth_center and len(result.smooth_center) >= 2:
            pts = lane.np.asarray(result.smooth_center, dtype=lane.np.int32)
            lane.cv2.polylines(out, [pts], False, (60, 230, 60), 3, lane.cv2.LINE_AA)
    return out


def nav_color(nav_mode):
    if nav_mode == NAV_STRAIGHT:
        return (30, 90, 255)
    if nav_mode == NAV_LEFT:
        return (255, 95, 70)
    if nav_mode == NAV_RIGHT:
        return (30, 200, 255)
    return (30, 90, 255)


def blend_overlay(base, overlay, alpha):
    lane.cv2.addWeighted(overlay, alpha, base, 1.0 - alpha, 0.0, dst=base)


def ground_segment_from_locked_arrow(locked_arrow, args):
    if locked_arrow.nav_mode == NAV_STRAIGHT:
        start = lane.np.asarray(
            [args.arrow_start_meters, straight_right_meters(args)],
            dtype=lane.np.float32,
        )
        target = lane.np.asarray(
            [args.straight_target_forward_meters, straight_right_meters(args)],
            dtype=lane.np.float32,
        )
        return start, target

    start_ground = pixel_to_vehicle_ground(locked_arrow.start, args)
    target_ground = pixel_to_vehicle_ground(locked_arrow.target, args)
    if start_ground is None or target_ground is None:
        return None, None
    return (
        lane.np.asarray(start_ground, dtype=lane.np.float32),
        lane.np.asarray(target_ground, dtype=lane.np.float32),
    )


def ground_arrow_polygon(start_ground, target_ground, body_width, head_width, head_length):
    vec = target_ground - start_ground
    length = float(lane.np.linalg.norm(vec))
    if length < 0.35:
        return None

    direction = vec / length
    normal = lane.np.asarray([-direction[1], direction[0]], dtype=lane.np.float32)
    head_length = min(float(head_length), max(0.45, length * 0.45))
    body_end = target_ground - direction * head_length
    body_half = max(0.05, float(body_width) * 0.5)
    head_half = max(body_half * 1.15, float(head_width) * 0.5)

    return [
        start_ground + normal * body_half,
        body_end + normal * body_half,
        body_end + normal * head_half,
        target_ground,
        body_end - normal * head_half,
        body_end - normal * body_half,
        start_ground - normal * body_half,
    ]


def draw_ground_polygon_layer(bgr, points, args, color, alpha, width, height, outline=False, thickness=2):
    projected = project_ground_polygon(points, args, width, height)
    if projected is None or len(projected) < 3:
        return False

    layer = bgr.copy()
    if outline:
        lane.cv2.polylines(layer, [projected], True, color, thickness, lane.cv2.LINE_AA)
    else:
        lane.cv2.fillPoly(layer, [projected], color, lane.cv2.LINE_AA)
    blend_overlay(bgr, layer, alpha)
    return True


def draw_ground_flow_chevrons(bgr, start_ground, target_ground, color, now, args):
    vec = target_ground - start_ground
    length = float(lane.np.linalg.norm(vec))
    if length < 1.4:
        return

    direction = vec / length
    normal = lane.np.asarray([-direction[1], direction[0]], dtype=lane.np.float32)
    head_length = min(args.ground_arrow_head_length_m, max(0.45, length * 0.45))
    flow_start = min(length * 0.25, 1.3)
    span = max(0.1, length - head_length - flow_start)
    chevrons = max(0, int(args.arrow_chevrons))
    width = int(getattr(args, "width", DEFAULT_WIDTH))
    height = int(getattr(args, "height", DEFAULT_HEIGHT))

    moving = bgr.copy()
    drew_any = False
    for idx in range(chevrons):
        t = (now * args.arrow_flow_speed + idx / float(max(1, chevrons))) % 1.0
        center = start_ground + direction * (flow_start + span * t)
        tip = center + direction * (args.ground_arrow_flow_length_m * 0.55)
        back = center - direction * (args.ground_arrow_flow_length_m * 0.45)
        left = back + normal * (args.ground_arrow_body_width_m * 0.48)
        right = back - normal * (args.ground_arrow_body_width_m * 0.48)

        tip_px = project_vehicle_ground_to_pixel(tip[0], tip[1], args)
        left_px = project_vehicle_ground_to_pixel(left[0], left[1], args)
        right_px = project_vehicle_ground_to_pixel(right[0], right[1], args)
        if tip_px is None or left_px is None or right_px is None:
            continue

        tip_i = clamp_projected_pixel(tip_px, width, height)
        left_i = clamp_projected_pixel(left_px, width, height)
        right_i = clamp_projected_pixel(right_px, width, height)
        brightness = 0.22 + 0.48 * (1.0 - abs(t - 0.5) * 2.0)
        chevron_color = tuple(int(255 * brightness + color[channel] * (1.0 - brightness)) for channel in range(3))
        lane.cv2.line(moving, left_i, tip_i, chevron_color, 2, lane.cv2.LINE_AA)
        lane.cv2.line(moving, right_i, tip_i, chevron_color, 2, lane.cv2.LINE_AA)
        drew_any = True

    if drew_any:
        blend_overlay(bgr, moving, args.arrow_flow_alpha)


def draw_ground_projected_arrow(bgr, locked_arrow, now, args):
    start_ground, target_ground = ground_segment_from_locked_arrow(locked_arrow, args)
    if start_ground is None or target_ground is None:
        return False

    vec = target_ground - start_ground
    length = float(lane.np.linalg.norm(vec))
    if length < args.ground_arrow_min_length_m:
        return False

    height, width = bgr.shape[:2]
    color = nav_color(locked_arrow.nav_mode)
    pulse = 0.5 + 0.5 * lane.np.sin(now * args.arrow_pulse_speed * 6.2831853)

    glow_points = ground_arrow_polygon(
        start_ground,
        target_ground,
        args.ground_arrow_body_width_m + args.ground_arrow_glow_extra_width_m,
        args.ground_arrow_head_width_m + args.ground_arrow_glow_extra_width_m * 1.8,
        args.ground_arrow_head_length_m,
    )
    main_points = ground_arrow_polygon(
        start_ground,
        target_ground,
        args.ground_arrow_body_width_m,
        args.ground_arrow_head_width_m,
        args.ground_arrow_head_length_m,
    )
    inner_points = ground_arrow_polygon(
        start_ground + (target_ground - start_ground) * 0.12,
        target_ground - (target_ground - start_ground) * 0.10,
        args.ground_arrow_body_width_m * 0.36,
        args.ground_arrow_head_width_m * 0.36,
        args.ground_arrow_head_length_m * 0.72,
    )
    if glow_points is None or main_points is None:
        return False

    if not draw_ground_polygon_layer(
        bgr,
        glow_points,
        args,
        color,
        args.ground_arrow_glow_alpha + pulse * 0.04,
        width,
        height,
    ):
        return False

    draw_ground_polygon_layer(
        bgr,
        main_points,
        args,
        color,
        args.ground_arrow_alpha,
        width,
        height,
    )
    if inner_points is not None:
        draw_ground_polygon_layer(
            bgr,
            inner_points,
            args,
            (255, 255, 255),
            args.ground_arrow_inner_alpha + pulse * 0.04,
            width,
            height,
        )
    draw_ground_polygon_layer(
        bgr,
        main_points,
        args,
        color,
        args.ground_arrow_edge_alpha,
        width,
        height,
        outline=True,
        thickness=2,
    )
    draw_ground_flow_chevrons(bgr, start_ground, target_ground, color, now, args)
    return True


def draw_glow_line(bgr, start, target, color, now, args):
    start = lane.np.asarray(start, dtype=lane.np.float32)
    target = lane.np.asarray(target, dtype=lane.np.float32)
    vec = target - start
    length = float(lane.np.linalg.norm(vec))
    if length < 8.0:
        return
    direction = vec / length
    normal = lane.np.asarray([-direction[1], direction[0]], dtype=lane.np.float32)

    pulse = 0.5 + 0.5 * lane.np.sin(now * args.arrow_pulse_speed * 6.2831853)
    main_width = int(args.arrow_width + pulse * 2.0)
    glow_width = int(args.arrow_glow_width + pulse * 7.0)
    head_len = min(args.arrow_head_max_len, max(args.arrow_head_min_len, length * 0.28))
    head_half = main_width * (1.65 + 0.15 * pulse)
    body_end = target - direction * (head_len * 0.72)

    # Soft outer glow, medium glow, then solid body. This is intentionally drawn
    # in BGR/OpenCV space because the camera frame is already a cv2 image here.
    glow = bgr.copy()
    lane.cv2.line(glow, tuple(start.astype(int)), tuple(body_end.astype(int)), color, glow_width, lane.cv2.LINE_AA)
    blend_overlay(bgr, glow, args.arrow_glow_alpha)

    glow_mid = bgr.copy()
    lane.cv2.line(glow_mid, tuple(start.astype(int)), tuple(body_end.astype(int)), color, max(main_width + 9, 10), lane.cv2.LINE_AA)
    blend_overlay(bgr, glow_mid, args.arrow_mid_alpha)

    body = bgr.copy()
    lane.cv2.line(body, tuple(start.astype(int)), tuple(body_end.astype(int)), color, main_width, lane.cv2.LINE_AA)
    blend_overlay(bgr, body, args.arrow_body_alpha)

    tip = target
    base = target - direction * head_len
    left = base + normal * head_half
    right = base - normal * head_half
    head = lane.np.asarray([tip, left, right], dtype=lane.np.int32)
    head_layer = bgr.copy()
    lane.cv2.fillConvexPoly(head_layer, head, color, lane.cv2.LINE_AA)
    blend_overlay(bgr, head_layer, 0.86)

    inner = bgr.copy()
    inner_tip = target - direction * 7.0
    inner_base = target - direction * (head_len * 0.62)
    inner_left = inner_base + normal * (head_half * 0.45)
    inner_right = inner_base - normal * (head_half * 0.45)
    inner_head = lane.np.asarray([inner_tip, inner_left, inner_right], dtype=lane.np.int32)
    lane.cv2.fillConvexPoly(inner, inner_head, (255, 255, 255), lane.cv2.LINE_AA)
    blend_overlay(bgr, inner, 0.22 + 0.16 * pulse)

    # Moving chevrons and light particles make the arrow feel alive without
    # requiring any external image files.
    moving = bgr.copy()
    span = max(1.0, length - head_len - 18.0)
    chevrons = max(1, int(args.arrow_chevrons))
    for idx in range(chevrons):
        t = (now * args.arrow_flow_speed + idx / float(chevrons)) % 1.0
        center = start + direction * (18.0 + span * t)
        tip_c = center + direction * (args.arrow_chevron_len * 0.60)
        left_c = center - direction * (args.arrow_chevron_len * 0.45) + normal * (main_width * 0.95)
        right_c = center - direction * (args.arrow_chevron_len * 0.45) - normal * (main_width * 0.95)
        brightness = 0.25 + 0.50 * (1.0 - abs(t - 0.5) * 2.0)
        chevron_color = tuple(int(255 * brightness + color[channel] * (1.0 - brightness)) for channel in range(3))
        lane.cv2.line(moving, tuple(left_c.astype(int)), tuple(tip_c.astype(int)), chevron_color, 3, lane.cv2.LINE_AA)
        lane.cv2.line(moving, tuple(right_c.astype(int)), tuple(tip_c.astype(int)), chevron_color, 3, lane.cv2.LINE_AA)
        if args.arrow_show_particles:
            particle = center - direction * 6.0
            radius = int(2 + 2 * brightness)
            lane.cv2.circle(moving, tuple(particle.astype(int)), radius, (255, 255, 255), -1, lane.cv2.LINE_AA)
    blend_overlay(bgr, moving, args.arrow_flow_alpha)

    # Small origin pulse. It reads like a projected AR anchor on the road.
    anchor = bgr.copy()
    radius = int(args.arrow_anchor_radius + pulse * 5.0)
    lane.cv2.circle(anchor, tuple(start.astype(int)), radius + 7, color, 2, lane.cv2.LINE_AA)
    lane.cv2.circle(anchor, tuple(start.astype(int)), radius, (255, 255, 255), 2, lane.cv2.LINE_AA)
    blend_overlay(bgr, anchor, 0.50)


def draw_simple_arrow(bgr, locked_arrow, now):
    color = nav_color(locked_arrow.nav_mode)
    lane.cv2.arrowedLine(
        bgr,
        tuple(locked_arrow.start),
        tuple(locked_arrow.target),
        color,
        5,
        lane.cv2.LINE_AA,
        tipLength=0.18,
    )
    lane.cv2.circle(bgr, tuple(locked_arrow.start), 7, color, -1, lane.cv2.LINE_AA)
    lane.cv2.circle(bgr, tuple(locked_arrow.target), 8, color, -1, lane.cv2.LINE_AA)


def draw_locked_arrow(bgr, locked_arrow, now, args):
    if locked_arrow is None:
        return

    seconds_left = max(0.0, locked_arrow.expires_at - now)
    color = nav_color(locked_arrow.nav_mode)
    if args.arrow_projection == "ground":
        if not draw_ground_projected_arrow(bgr, locked_arrow, now, args):
            draw_glow_line(bgr, locked_arrow.start, locked_arrow.target, color, now, args)
    elif args.arrow_style == "simple":
        draw_simple_arrow(bgr, locked_arrow, now)
    else:
        draw_glow_line(bgr, locked_arrow.start, locked_arrow.target, color, now, args)

    label = "NAV {} | hold {:.1f}s | conf {:.2f}".format(
        locked_arrow.nav_mode.upper(),
        seconds_left,
        locked_arrow.confidence,
    )
    x = max(12, min(bgr.shape[1] - 360, locked_arrow.target[0] + 12))
    y = max(28, locked_arrow.target[1] - 12)
    lane.cv2.putText(bgr, label, (x, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.66, (20, 20, 20), 3, lane.cv2.LINE_AA)
    lane.cv2.putText(bgr, label, (x, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.66, (255, 255, 255), 1, lane.cv2.LINE_AA)


def draw_detection_status(bgr, packet, tracker, detecting):
    lines = ["nav intent: {}".format(tracker.nav_mode.upper())]
    if packet is None:
        lines.append("YOLOP: waiting")
    elif packet.error:
        lines.append("YOLOP error: {}".format(packet.error[:80]))
    else:
        lines.append("YOLOP: frame {} | {:.0f} ms | nav {}".format(packet.frame_id, packet.inference_ms, packet.nav_mode))
        if packet.result is not None:
            lines.append(
                "geometry: {} | conf {:.2f} | pts {}".format(
                    packet.result.turn_direction,
                    packet.result.confidence,
                    len(packet.result.center_points or []),
                )
            )
        if packet.candidate is not None:
            lines.append("candidate target: {}".format(fmt_point(packet.candidate.target)))
    lines.append("tracker: {}".format(tracker.last_status))
    if detecting:
        lines.append("detecting...")

    y = 28
    for text in lines[:6]:
        lane.cv2.putText(bgr, text, (18, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.68, (20, 20, 20), 3, lane.cv2.LINE_AA)
        lane.cv2.putText(bgr, text, (18, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 1, lane.cv2.LINE_AA)
        y += 26


def parse_args():
    parser = argparse.ArgumentParser(
        description="Realtime CARLA YOLOP navigation-intent ground-projected AR arrow demo.",
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

    parser.add_argument("--arrow-projection", choices=["ground", "screen"], default="ground")
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

    parser.add_argument("--show-debug-geometry", action="store_true", default=False)
    parser.add_argument("--show-debug-mask", action="store_true", default=False)
    args = parser.parse_args()
    args.vehicle_ground_z = 0.0
    return args


def set_nav_from_key(event, tracker):
    if event.key == pygame.K_1:
        tracker.set_nav_mode(NAV_STRAIGHT)
        print("Navigation intent: STRAIGHT")
        return True
    if event.key == pygame.K_2:
        tracker.set_nav_mode(NAV_LEFT)
        print("Navigation intent: LEFT")
        return True
    if event.key == pygame.K_3:
        tracker.set_nav_mode(NAV_RIGHT)
        print("Navigation intent: RIGHT")
        return True
    if event.key in (pygame.K_c, pygame.K_0):
        tracker.clear()
        print("Navigation intent cleared.")
        return True
    return False


def main():
    args = parse_args()
    args.height = int(args.height)
    args.width = int(args.width)
    lane.ensure_runtime()

    pygame.init()
    pygame.font.init()
    display = pygame.display.set_mode((args.width, args.height))
    pygame.display.set_caption("CARLA YOLOP ground AR arrow | 1/2/3 | C clear | ESC quit")
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    # Mirrors lesson 08's camera setup. This script still draws a 2D near-field
    # anchor; later you can replace it with calibrated IPM/depth for real 5m.
    _k = build_camera_intrinsic_k(args.width, args.height, CAMERA_FOV)

    client, world = connect_to_carla()
    original_settings = set_world_async(world)
    actors = []
    current_steer = 0.0

    adapter = lane.YOLOPAdapter(
        args.yolop_onnx,
        input_width=args.yolop_width,
        input_height=args.yolop_height,
        threshold=args.yolop_threshold,
        normalize=args.normalize,
    )
    tracker = NavigationArrowTracker(args)
    executor = ThreadPoolExecutor(max_workers=1)
    pending_future = None
    next_detection_time = 0.0
    last_packet = None
    last_result = None
    show_debug = args.show_debug_geometry or args.show_debug_mask

    print("Realtime YOLOP ground-projected navigation hint demo")
    print("YOLOP:", args.yolop_onnx)
    print("Controls: 1 straight | 2 left | 3 right | C/0 clear | M debug | ESC quit")

    try:
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        sensor_tick = "0.0"
        if args.camera_fps > 0:
            sensor_tick = str(1.0 / args.camera_fps)
        camera = CameraSensor(
            world,
            vehicle,
            "sensor.camera.rgb",
            width=args.width,
            height=args.height,
            fov=CAMERA_FOV,
            sensor_tick=sensor_tick,
        )
        actors.append(camera.actor)
        args.camera_k = _k
        args.camera_mount_transform = camera.transform

        running = True
        while running:
            clock.tick(max(1, args.display_fps))
            now = time.time()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_m:
                        show_debug = not show_debug
                        print("Debug overlay:", show_debug)
                    else:
                        set_nav_from_key(event, tracker)

            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            if pending_future is not None and pending_future.done():
                last_packet = pending_future.result()
                pending_future = None
                if last_packet.error:
                    print("[YOLOP] error:", last_packet.error)
                else:
                    last_result = last_packet.result
                    tracker.push(last_packet.candidate, now)
                    if last_packet.candidate is not None:
                        print(
                            "[YOLOP] frame={} {:.0f}ms nav={} target={} conf={:.2f} status={}".format(
                                last_packet.frame_id,
                                last_packet.inference_ms,
                                last_packet.candidate.nav_mode,
                                fmt_point(last_packet.candidate.target),
                                last_packet.candidate.confidence,
                                tracker.last_status,
                            )
                        )
                    else:
                        print(
                            "[YOLOP] frame={} {:.0f}ms nav={} no candidate status={}".format(
                                last_packet.frame_id,
                                last_packet.inference_ms,
                                last_packet.nav_mode,
                                tracker.last_status,
                            )
                        )

            if (
                camera.latest_rgb is not None
                and pending_future is None
                and now >= next_detection_time
                and tracker.nav_mode != NAV_NONE
            ):
                frame_id = camera.latest_image.frame if camera.latest_image is not None else "-"
                rgb_for_detection = camera.latest_rgb.copy()
                pending_future = executor.submit(
                    run_detection,
                    adapter,
                    rgb_for_detection,
                    args,
                    frame_id,
                    tracker.nav_mode,
                )
                next_detection_time = now + max(0.2, args.detect_interval)

            if camera.latest_rgb is not None:
                bgr = camera.latest_rgb[:, :, ::-1].copy()
                if show_debug:
                    bgr = draw_debug_geometry(bgr, last_result, args)
                locked_arrow = tracker.active_arrow(now)
                draw_locked_arrow(bgr, locked_arrow, now, args)
                draw_detection_status(bgr, last_packet, tracker, pending_future is not None)
                display.blit(make_pygame_surface(pygame, bgr[:, :, ::-1]), (0, 0))
            else:
                display.fill((10, 10, 10))

            hud = [
                "YOLOP nav hint | 1 straight | 2 left | 3 right | C/0 clear | M debug | ESC quit",
                "Drive: W/A/S/D or arrows | targets are filtered to {:.0f}m ahead.".format(
                    args.max_target_forward_meters
                ),
                "YOLOP every {:.1f}s | lock after {} stable samples | hold {:.1f}s".format(
                    args.detect_interval,
                    args.stability_confirmations,
                    args.arrow_hold_seconds,
                ),
                "Arrow projection: {} | body {:.2f}m | head {:.2f}m".format(
                    args.arrow_projection,
                    args.ground_arrow_body_width_m,
                    args.ground_arrow_head_width_m,
                ),
                "Current nav: {} | active arrow: {} | debug: {}".format(
                    tracker.nav_mode.upper(),
                    tracker.active_arrow(now) is not None,
                    show_debug,
                ),
            ]
            draw_text_lines(pygame, display, font, hud, y=args.height - 126, line_height=22)
            pygame.display.flip()

    finally:
        if pending_future is not None:
            pending_future.cancel()
        executor.shutdown(wait=False)
        destroy_actors(actors)
        world.apply_settings(original_settings)
        pygame.quit()
        print("Restored original world settings.")
        print("Cleaned up.")


if __name__ == "__main__":
    main()
