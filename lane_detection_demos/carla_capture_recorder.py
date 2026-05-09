"""
carla_capture_recorder.py

Capture CARLA camera images for offline lane-model testing.

Controls:
  W/A/S/D or arrow keys : drive
  C                    : save current frame as PNG
  V                    : start / stop video recording
  ESC                  : quit

Outputs:
  lane_detection_demos/captures/session_YYYYmmdd_HHMMSS/
    screenshots/
    videos/

Video recording uses OpenCV when available. If cv2 is not installed, the script
falls back to saving a PNG image sequence for each recording.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pygame


THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
TUTORIAL_DIR = PROJECT_ROOT / "carla_from_zero_to_ar_tutorial"
if str(TUTORIAL_DIR) not in sys.path:
    sys.path.insert(0, str(TUTORIAL_DIR))


from common import CAMERA_FOV  # noqa: E402
from common import CameraSensor  # noqa: E402
from common import connect_to_carla  # noqa: E402
from common import destroy_actors  # noqa: E402
from common import draw_text_lines  # noqa: E402
from common import get_keyboard_vehicle_control  # noqa: E402
from common import make_pygame_surface  # noqa: E402
from common import spawn_ego_vehicle  # noqa: E402


try:
    import cv2
except ImportError:  # pragma: no cover - optional dependency
    cv2 = None


DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720


def set_world_async(world):
    """
    Manual pygame driving needs the CARLA world to advance by itself.

    If a previous lesson left the server in synchronous mode, the vehicle and
    camera will look frozen unless this script calls world.tick(). For capture,
    async mode is simpler and more responsive.
    """
    original_settings = world.get_settings()
    if original_settings.synchronous_mode:
        settings = world.get_settings()
        settings.synchronous_mode = False
        settings.fixed_delta_seconds = None
        world.apply_settings(settings)
        print("World was synchronous; switched to asynchronous mode for capture.")
    else:
        print("World is already asynchronous.")
    return original_settings


def timestamp():
    return time.strftime("%Y%m%d_%H%M%S")


def make_session_dirs(output_root):
    session_dir = output_root / "session_{}".format(timestamp())
    screenshot_dir = session_dir / "screenshots"
    video_dir = session_dir / "videos"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)
    return session_dir, screenshot_dir, video_dir


def save_rgb_png(rgb, path):
    path = Path(path)
    if cv2 is not None:
        cv2.imwrite(str(path), rgb[:, :, ::-1])
    else:
        surface = make_pygame_surface(pygame, rgb)
        pygame.image.save(surface, str(path))
    return path


class VideoRecorder(object):
    """Small wrapper around cv2.VideoWriter with PNG-sequence fallback."""

    def __init__(self, video_dir, width, height, fps):
        self.video_dir = Path(video_dir)
        self.width = int(width)
        self.height = int(height)
        self.fps = float(fps)
        self.recording = False
        self.writer = None
        self.frame_dir = None
        self.output_path = None
        self.frame_count = 0
        self.started_at = None
        self.last_write_time = 0.0

    def start(self):
        name = "recording_{}".format(timestamp())
        self.frame_count = 0
        self.started_at = time.time()
        self.last_write_time = 0.0

        if cv2 is not None:
            self.output_path = self.video_dir / "{}.mp4".format(name)
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.writer = cv2.VideoWriter(
                str(self.output_path),
                fourcc,
                self.fps,
                (self.width, self.height),
            )
            if not self.writer.isOpened():
                self.writer.release()
                self.writer = None
                self.output_path = None

        if self.writer is None:
            self.frame_dir = self.video_dir / "{}_frames".format(name)
            self.frame_dir.mkdir(parents=True, exist_ok=True)
            self.output_path = self.frame_dir

        self.recording = True
        return self.output_path

    def should_write_now(self):
        now = time.time()
        if self.last_write_time <= 0.0:
            self.last_write_time = now
            return True

        interval = 1.0 / max(1.0, self.fps)
        if now - self.last_write_time >= interval:
            self.last_write_time = now
            return True
        return False

    def write(self, rgb):
        if not self.recording or not self.should_write_now():
            return False

        if self.writer is not None:
            self.writer.write(rgb[:, :, ::-1])
        else:
            frame_path = self.frame_dir / "frame_{:06d}.png".format(self.frame_count)
            save_rgb_png(rgb, frame_path)

        self.frame_count += 1
        return True

    def stop(self):
        if not self.recording:
            return None

        if self.writer is not None:
            self.writer.release()
            self.writer = None

        meta_path = None
        if self.output_path is not None:
            meta_path = Path(str(self.output_path) + ".json")
            meta = {
                "output": str(self.output_path),
                "fps": self.fps,
                "width": self.width,
                "height": self.height,
                "frames": self.frame_count,
                "duration_seconds": time.time() - self.started_at if self.started_at else None,
                "format": "mp4" if self.frame_dir is None else "png_sequence",
            }
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf8")

        stopped_path = self.output_path
        self.recording = False
        self.output_path = None
        self.frame_dir = None
        self.frame_count = 0
        self.started_at = None
        self.last_write_time = 0.0
        return stopped_path, meta_path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Capture CARLA camera screenshots and videos.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--display-fps", type=int, default=60)
    parser.add_argument("--record-fps", type=int, default=30)
    parser.add_argument(
        "--output-root",
        default=str(THIS_DIR / "captures"),
        help="Root folder for capture sessions.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_root = Path(args.output_root)
    session_dir, screenshot_dir, video_dir = make_session_dirs(output_root)

    pygame.init()
    pygame.font.init()
    display = pygame.display.set_mode((args.width, args.height))
    pygame.display.set_caption("CARLA capture recorder | C screenshot | V record")
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    client, world = connect_to_carla()
    original_settings = set_world_async(world)
    actors = []
    current_steer = 0.0
    saved_message = "Session: {}".format(session_dir)
    screenshot_count = 0
    last_saved_screenshot = "-"
    last_saved_video = "-"
    recorder = VideoRecorder(video_dir, args.width, args.height, args.record_fps)

    print("Capture session:", session_dir)
    print("Controls: C screenshot | V start/stop recording | ESC quit")

    try:
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        camera = CameraSensor(
            world,
            vehicle,
            "sensor.camera.rgb",
            width=args.width,
            height=args.height,
            fov=CAMERA_FOV,
        )
        actors.append(camera.actor)

        running = True
        while running:
            clock.tick(max(1, args.display_fps))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_c:
                        if camera.latest_rgb is not None:
                            screenshot_count += 1
                            image_frame = camera.latest_image.frame if camera.latest_image else 0
                            path = screenshot_dir / "shot_{:04d}_frame_{}.png".format(
                                screenshot_count,
                                image_frame,
                            )
                            save_rgb_png(camera.latest_rgb, path)
                            last_saved_screenshot = str(path)
                            saved_message = "Saved screenshot: {}".format(path.name)
                            print(saved_message, "->", path)
                        else:
                            saved_message = "No camera frame yet; screenshot skipped."
                            print(saved_message)
                    elif event.key == pygame.K_v:
                        if recorder.recording:
                            result = recorder.stop()
                            if result:
                                video_path, meta_path = result
                                last_saved_video = str(video_path)
                                saved_message = "Saved recording: {}".format(Path(video_path).name)
                                print(saved_message, "->", video_path)
                                if meta_path:
                                    print("Metadata ->", meta_path)
                        else:
                            started_path = recorder.start()
                            saved_message = "Recording started: {}".format(Path(started_path).name)
                            print(saved_message, "->", started_path)

            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            if camera.latest_rgb is not None:
                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))
                recorder.write(camera.latest_rgb)
            else:
                display.fill((10, 10, 10))

            if recorder.recording:
                pygame.draw.circle(display, (255, 30, 30), (args.width - 32, 32), 12)

            hud = [
                "CARLA Capture | C screenshot | V record toggle | ESC quit",
                "W/A/S/D or arrow keys drive | size {}x{} | display {} fps | record {} fps".format(
                    args.width,
                    args.height,
                    args.display_fps,
                    args.record_fps,
                ),
                "Keyboard focus: {} | click this pygame window before driving/capture".format(
                    pygame.key.get_focused()
                ),
                "Recording: {} | frames: {}".format(recorder.recording, recorder.frame_count),
                saved_message,
                "Last screenshot: {}".format(last_saved_screenshot),
                "Last video/sequence: {}".format(last_saved_video),
            ]
            draw_text_lines(pygame, display, font, hud)
            pygame.display.flip()

    finally:
        if recorder.recording:
            result = recorder.stop()
            if result:
                print("Recording stopped on exit ->", result[0])
        destroy_actors(actors)
        world.apply_settings(original_settings)
        print("Restored original world settings.")
        pygame.quit()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
