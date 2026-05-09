from pathlib import Path
import argparse
import sys
import time


SUBPROJECT_DIR = Path(__file__).resolve().parents[1]
if str(SUBPROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(SUBPROJECT_DIR))

from nav_learning.arrow_renderer import ArrowRenderer  # noqa: E402
from nav_learning.models import LockedNavArrow, NAV_LEFT, NAV_RIGHT, NAV_STRAIGHT  # noqa: E402
from nav_learning.paths import ensure_runtime, latest_capture_image, lane  # noqa: E402
from nav_learning.settings import build_parser, config_from_args  # noqa: E402


def read_background(path, width, height):
    ensure_runtime()
    image = None
    if path:
        image = lane.cv2.imread(str(path))
    if image is None:
        image = lane.np.zeros((height, width, 3), dtype=lane.np.uint8)
        image[:] = (35, 38, 42)
        lane.cv2.line(image, (width // 2, height), (width // 2, height // 3), (80, 80, 80), 2, lane.cv2.LINE_AA)
    return lane.cv2.resize(image, (width, height), interpolation=lane.cv2.INTER_AREA)


def main():
    parser = build_parser("Preview only the AR arrow renderer.")
    parser.add_argument("--image", default=None, help="Optional background image. Empty means latest capture screenshot.")
    parser.add_argument("--output", default=str(SUBPROJECT_DIR / "outputs" / "arrow_preview.jpg"))
    args = parser.parse_args()
    config = config_from_args(args)

    image_path = Path(args.image) if args.image else latest_capture_image()
    bgr = read_background(image_path, config.width, config.height)
    renderer = ArrowRenderer(config)
    now = time.time()
    arrows = [
        LockedNavArrow(NAV_STRAIGHT, (640, 562), (640, 410), 0.92, now, now + 3.0),
        LockedNavArrow(NAV_LEFT, (450, 570), (280, 350), 0.88, now, now + 3.0),
        LockedNavArrow(NAV_RIGHT, (830, 570), (1000, 350), 0.86, now, now + 3.0),
    ]
    for arrow in arrows:
        renderer.draw_locked_arrow(bgr, arrow, now)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lane.cv2.imwrite(str(output), bgr)
    print("Saved arrow preview:", output)


if __name__ == "__main__":
    main()

