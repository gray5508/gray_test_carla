from pathlib import Path
import argparse
import sys
import time

import pygame


SUBPROJECT_DIR = Path(__file__).resolve().parents[1]
if str(SUBPROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(SUBPROJECT_DIR))

from nav_learning.arrow_renderer import ArrowRenderer  # noqa: E402
from nav_learning.models import LockedNavArrow, NAV_LEFT, NAV_NONE, NAV_RIGHT, NAV_STRAIGHT  # noqa: E402
from nav_learning.paths import ensure_runtime, latest_capture_image, lane  # noqa: E402
from nav_learning.pygame_view import PygameWindow  # noqa: E402
from nav_learning.settings import build_parser, config_from_args  # noqa: E402


def background(config, image_path):
    ensure_runtime()
    image = lane.cv2.imread(str(image_path)) if image_path else None
    if image is None:
        image = lane.np.zeros((config.height, config.width, 3), dtype=lane.np.uint8)
        image[:] = (35, 38, 42)
    return lane.cv2.resize(image, (config.width, config.height), interpolation=lane.cv2.INTER_AREA)


def arrow_for_mode(nav_mode, now):
    if nav_mode == NAV_STRAIGHT:
        return LockedNavArrow(nav_mode, (640, 562), (640, 410), 0.90, now, now + 999.0)
    if nav_mode == NAV_LEFT:
        return LockedNavArrow(nav_mode, (450, 570), (280, 350), 0.88, now, now + 999.0)
    if nav_mode == NAV_RIGHT:
        return LockedNavArrow(nav_mode, (830, 570), (1000, 350), 0.88, now, now + 999.0)
    return None


def main():
    parser = build_parser("Open only the pygame window and arrow drawing path.")
    parser.add_argument("--image", default=None, help="Optional background image. Empty means latest capture screenshot.")
    args = parser.parse_args()
    config = config_from_args(args)

    image_path = Path(args.image) if args.image else latest_capture_image()
    base = background(config, image_path)
    renderer = ArrowRenderer(config)
    window = PygameWindow(config.width, config.height, "pygame module test | 1/2/3 | C clear | ESC quit")
    nav_mode = NAV_STRAIGHT

    try:
        running = True
        while running:
            window.tick(config.display_fps)
            now = time.time()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_1:
                        nav_mode = NAV_STRAIGHT
                    elif event.key == pygame.K_2:
                        nav_mode = NAV_LEFT
                    elif event.key == pygame.K_3:
                        nav_mode = NAV_RIGHT
                    elif event.key in (pygame.K_c, pygame.K_0):
                        nav_mode = NAV_NONE

            frame = base.copy()
            renderer.draw_locked_arrow(frame, arrow_for_mode(nav_mode, now), now)
            window.blit_bgr(frame)
            window.draw_text_lines(
                [
                    "Pygame-only test: 1 straight | 2 left | 3 right | C clear | ESC quit",
                    "Current nav: {}".format(nav_mode.upper()),
                    "This test does not use CARLA or YOLOP.",
                ],
                y=config.height - 82,
            )
            window.flip()
    finally:
        window.close()


if __name__ == "__main__":
    main()

