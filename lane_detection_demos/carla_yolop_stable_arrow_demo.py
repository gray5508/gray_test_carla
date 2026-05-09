"""
carla_yolop_stable_arrow_demo.py

Realtime CARLA + pygame demo using YOLOP lane segmentation to draw a stable
navigation-style arrow.

Goal:
  - Drive manually in CARLA.
  - Run YOLOP only once per second, not every frame.
  - Convert the lane mask into a visual route centerline.
  - Lock a stable arrow target for a few seconds to avoid jitter.
  - Do not use CARLA waypoints.

Controls:
  W/A/S/D or arrow keys : drive
  R                    : reset the locked arrow
  M                    : toggle mask/centerline debug overlay
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


# common.py imports numpy immediately. When launching directly with
# C:\Users\...\envs\carla_test\python.exe on Windows, conda's Library\bin may
# not be on the DLL search path yet, so prepare it before importing common.py.
lane.prepare_windows_dll_search_path()


from common import CAMERA_FOV  # noqa: E402
from common import CameraSensor  # noqa: E402
from common import build_camera_intrinsic_k  # noqa: E402
from common import connect_to_carla  # noqa: E402
from common import destroy_actors  # noqa: E402
from common import draw_text_lines  # noqa: E402
from common import get_keyboard_vehicle_control  # noqa: E402
from common import make_pygame_surface  # noqa: E402
from common import spawn_ego_vehicle  # noqa: E402

from offline_yolop_turn_experiment import estimate_current_lane  # noqa: E402


DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720


@dataclass
class ArrowCandidate:
    target: tuple
    start: tuple
    direction: str
    confidence: float
    center_points: int
    created_at: float


@dataclass
class LockedArrow:
    target: tuple
    start: tuple
    direction: str
    confidence: float
    locked_at: float
    expires_at: float


@dataclass
class DetectionPacket:
    result: object
    candidate: ArrowCandidate
    inference_ms: float
    frame_id: object
    error: str = ""


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


def direction_compatible(a, b):
    if a == b:
        return True
    if "unknown" in (a, b):
        return False
    # Straight can smoothly become a turn near intersections; allow it to help
    # confirm a stable target instead of forcing the arrow to disappear.
    if a == "straight/weak" or b == "straight/weak":
        return True
    return False


def mean_point(points):
    if not points:
        return None
    x = sum(point[0] for point in points) / float(len(points))
    y = sum(point[1] for point in points) / float(len(points))
    return int(x), int(y)


def point_distance(a, b):
    dx = float(a[0] - b[0])
    dy = float(a[1] - b[1])
    return (dx * dx + dy * dy) ** 0.5


def blend_points(old, new, alpha):
    x = int(round((1.0 - alpha) * old[0] + alpha * new[0]))
    y = int(round((1.0 - alpha) * old[1] + alpha * new[1]))
    return x, y


class StableArrowTracker(object):
    def __init__(self, args):
        self.args = args
        self.candidates = []
        self.locked = None
        self.last_status = "waiting for YOLOP"

    def reset(self):
        self.candidates = []
        self.locked = None
        self.last_status = "reset"

    def active_arrow(self, now):
        if self.locked is None:
            return None
        if now > self.locked.expires_at:
            return None
        return self.locked

    def push(self, candidate, now):
        if candidate is None:
            self.last_status = "no valid candidate"
            return self.active_arrow(now)

        self.candidates.append(candidate)
        self.candidates = [
            item
            for item in self.candidates
            if now - item.created_at <= self.args.stability_window_seconds
        ][-self.args.max_candidate_history :]

        recent = [
            item
            for item in self.candidates
            if direction_compatible(item.direction, candidate.direction)
        ]
        if len(recent) < self.args.stability_confirmations:
            self.last_status = "collecting stable candidates {}/{}".format(
                len(recent),
                self.args.stability_confirmations,
            )
            return self.active_arrow(now)

        recent = recent[-self.args.stability_confirmations :]
        target_mean = mean_point([item.target for item in recent])
        start_mean = mean_point([item.start for item in recent])
        if target_mean is None or start_mean is None:
            self.last_status = "candidate mean failed"
            return self.active_arrow(now)

        max_distance = max(point_distance(item.target, target_mean) for item in recent)
        if max_distance > self.args.stable_target_radius:
            self.last_status = "target not stable, spread {:.1f}px".format(max_distance)
            return self.active_arrow(now)

        confidence = sum(item.confidence for item in recent) / float(len(recent))
        direction = self.majority_direction(recent)

        if self.locked is not None and now <= self.locked.expires_at:
            start = blend_points(self.locked.start, start_mean, self.args.arrow_smoothing_alpha)
            target = blend_points(self.locked.target, target_mean, self.args.arrow_smoothing_alpha)
        else:
            start = start_mean
            target = target_mean

        self.locked = LockedArrow(
            target=target,
            start=start,
            direction=direction,
            confidence=confidence,
            locked_at=now,
            expires_at=now + self.args.arrow_hold_seconds,
        )
        self.last_status = "locked {} for {:.1f}s".format(direction, self.args.arrow_hold_seconds)
        return self.locked

    @staticmethod
    def majority_direction(candidates):
        counts = {}
        for item in candidates:
            counts[item.direction] = counts.get(item.direction, 0) + 1
        return sorted(counts.items(), key=lambda pair: pair[1], reverse=True)[0][0]


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


def make_candidate(result, args, width, height, now):
    if result is None:
        return None
    if not result.target_point or result.confidence < args.min_confidence:
        return None

    if args.fixed_arrow_start:
        start = (
            int(width * args.vehicle_x_ratio),
            int(height * args.arrow_start_y_ratio),
        )
    else:
        start = tuple(result.start_point) if result.start_point else (
            int(width * args.vehicle_x_ratio),
            int(height * args.arrow_start_y_ratio),
        )

    return ArrowCandidate(
        target=tuple(result.target_point),
        start=start,
        direction=result.turn_direction,
        confidence=float(result.confidence),
        center_points=len(result.center_points or []),
        created_at=now,
    )


def run_detection(adapter, rgb, args, frame_id):
    started = time.time()
    try:
        bgr = rgb[:, :, ::-1].copy()
        mask, model_debug = predict_yolop_mask(adapter, bgr)
        if mask is None:
            result = EmptyResult(["YOLOP lane mask missing"] + model_debug[:2])
            candidate = None
        else:
            turn_args = make_turn_args(args)
            result = estimate_current_lane(mask, turn_args)
            candidate = make_candidate(result, args, rgb.shape[1], rgb.shape[0], time.time())
        elapsed_ms = (time.time() - started) * 1000.0
        return DetectionPacket(result, candidate, elapsed_ms, frame_id)
    except Exception as exc:
        elapsed_ms = (time.time() - started) * 1000.0
        return DetectionPacket(None, None, elapsed_ms, frame_id, error="{}: {}".format(type(exc).__name__, exc))


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


def predict_yolop_mask(adapter, bgr):
    obs = adapter.predict(bgr)
    if obs.lane_mask is None:
        return None, obs.debug_lines or []
    return obs.lane_mask.astype(bool), obs.debug_lines or []


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


def draw_locked_arrow(bgr, locked_arrow, now):
    if locked_arrow is None:
        return

    seconds_left = max(0.0, locked_arrow.expires_at - now)
    color = (0, 0, 255)
    lane.cv2.arrowedLine(
        bgr,
        tuple(locked_arrow.start),
        tuple(locked_arrow.target),
        color,
        5,
        lane.cv2.LINE_AA,
        tipLength=0.18,
    )
    lane.cv2.circle(bgr, tuple(locked_arrow.start), 7, (0, 0, 180), -1, lane.cv2.LINE_AA)
    lane.cv2.circle(bgr, tuple(locked_arrow.target), 8, color, -1, lane.cv2.LINE_AA)

    label = "{} | hold {:.1f}s | conf {:.2f}".format(
        locked_arrow.direction,
        seconds_left,
        locked_arrow.confidence,
    )
    lane.cv2.putText(bgr, label, (locked_arrow.target[0] + 12, locked_arrow.target[1] - 12),
                     lane.cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 3, lane.cv2.LINE_AA)
    lane.cv2.putText(bgr, label, (locked_arrow.target[0] + 12, locked_arrow.target[1] - 12),
                     lane.cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1, lane.cv2.LINE_AA)


def draw_detection_status(bgr, packet, tracker, detecting):
    lines = []
    if packet is None:
        lines.append("YOLOP: waiting")
    elif packet.error:
        lines.append("YOLOP error: {}".format(packet.error[:80]))
    else:
        lines.append("YOLOP: frame {} | {:.0f} ms".format(packet.frame_id, packet.inference_ms))
        if packet.result is not None:
            lines.append(
                "candidate: {} | conf {:.2f} | pts {}".format(
                    packet.result.turn_direction,
                    packet.result.confidence,
                    len(packet.result.center_points or []),
                )
            )
    lines.append("tracker: {}".format(tracker.last_status))
    if detecting:
        lines.append("detecting...")

    y = 28
    for text in lines[:5]:
        lane.cv2.putText(bgr, text, (18, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.68, (20, 20, 20), 3, lane.cv2.LINE_AA)
        lane.cv2.putText(bgr, text, (18, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 1, lane.cv2.LINE_AA)
        y += 26


def parse_args():
    parser = argparse.ArgumentParser(
        description="Realtime CARLA YOLOP stable arrow demo.",
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

    parser.add_argument("--detect-interval", type=float, default=1.0, help="YOLOP inference interval in seconds.")
    parser.add_argument("--arrow-hold-seconds", type=float, default=3.0)
    parser.add_argument("--stability-confirmations", type=int, default=2)
    parser.add_argument("--stability-window-seconds", type=float, default=3.2)
    parser.add_argument("--max-candidate-history", type=int, default=5)
    parser.add_argument("--stable-target-radius", type=float, default=120.0)
    parser.add_argument("--arrow-smoothing-alpha", type=float, default=0.35)
    parser.add_argument(
        "--free-arrow-start",
        action="store_true",
        help="Use the detected centerline start instead of a fixed near-field anchor.",
    )

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

    parser.add_argument(
        "--no-debug-geometry",
        dest="show_debug_geometry",
        action="store_false",
        default=True,
        help="Hide detected centerline/scan-point debug geometry.",
    )
    parser.add_argument("--show-debug-mask", action="store_true", default=False)
    args = parser.parse_args()
    args.fixed_arrow_start = not args.free_arrow_start
    return args


def main():
    args = parse_args()
    lane.ensure_runtime()

    pygame.init()
    pygame.font.init()
    display = pygame.display.set_mode((args.width, args.height))
    pygame.display.set_caption("CARLA YOLOP stable arrow | R reset | M debug | ESC quit")
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    # Kept here to mirror lesson 08's camera-geometry setup. The current demo
    # uses a fixed pixel anchor for the "about 5m ahead" start point; for a real
    # vehicle, replace that with calibrated IPM/depth geometry.
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
    tracker = StableArrowTracker(args)
    executor = ThreadPoolExecutor(max_workers=1)
    pending_future = None
    next_detection_time = 0.0
    last_packet = None
    last_result = None
    show_debug = args.show_debug_geometry or args.show_debug_mask

    print("Realtime YOLOP stable arrow demo")
    print("YOLOP:", args.yolop_onnx)
    print("Detect interval: {:.2f}s | arrow hold: {:.2f}s".format(args.detect_interval, args.arrow_hold_seconds))
    print("Controls: W/A/S/D drive | R reset arrow | M debug overlay | ESC quit")

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
                    elif event.key == pygame.K_r:
                        tracker.reset()
                        print("Arrow tracker reset.")
                    elif event.key == pygame.K_m:
                        show_debug = not show_debug
                        print("Debug overlay:", show_debug)

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
                    cand = last_packet.candidate
                    if cand is not None:
                        print(
                            "[YOLOP] frame={} {:.0f}ms dir={} conf={:.2f} target={} status={}".format(
                                last_packet.frame_id,
                                last_packet.inference_ms,
                                cand.direction,
                                cand.confidence,
                                fmt_point(cand.target),
                                tracker.last_status,
                            )
                        )
                    else:
                        print(
                            "[YOLOP] frame={} {:.0f}ms no candidate status={}".format(
                                last_packet.frame_id,
                                last_packet.inference_ms,
                                tracker.last_status,
                            )
                        )

            if (
                camera.latest_rgb is not None
                and pending_future is None
                and now >= next_detection_time
            ):
                frame_id = camera.latest_image.frame if camera.latest_image is not None else "-"
                rgb_for_detection = camera.latest_rgb.copy()
                pending_future = executor.submit(run_detection, adapter, rgb_for_detection, args, frame_id)
                next_detection_time = now + max(0.2, args.detect_interval)

            if camera.latest_rgb is not None:
                bgr = camera.latest_rgb[:, :, ::-1].copy()
                if show_debug:
                    bgr = draw_debug_geometry(bgr, last_result, args)
                locked_arrow = tracker.active_arrow(now)
                draw_locked_arrow(bgr, locked_arrow, now)
                draw_detection_status(bgr, last_packet, tracker, pending_future is not None)
                rgb_display = bgr[:, :, ::-1]
                display.blit(make_pygame_surface(pygame, rgb_display), (0, 0))
            else:
                display.fill((10, 10, 10))

            hud = [
                "CARLA YOLOP stable arrow | W/A/S/D drive | R reset | M debug | ESC quit",
                "YOLOP every {:.1f}s | lock after {} stable samples | hold {:.1f}s".format(
                    args.detect_interval,
                    args.stability_confirmations,
                    args.arrow_hold_seconds,
                ),
                "Keyboard focus: {} | click pygame window if controls do not respond".format(pygame.key.get_focused()),
                "Debug overlay: {} | active arrow: {}".format(show_debug, tracker.active_arrow(now) is not None),
                "Note: start point is a fixed near-field pixel anchor, standing in for about 5m ahead.",
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
