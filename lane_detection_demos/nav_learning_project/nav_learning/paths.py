from pathlib import Path
import sys


PACKAGE_DIR = Path(__file__).resolve().parent
SUBPROJECT_DIR = PACKAGE_DIR.parent
LANE_DEMO_DIR = SUBPROJECT_DIR.parent
PROJECT_ROOT = LANE_DEMO_DIR.parent
TUTORIAL_DIR = PROJECT_ROOT / "carla_from_zero_to_ar_tutorial"


def add_repo_paths():
    for path in (LANE_DEMO_DIR, TUTORIAL_DIR):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)


add_repo_paths()

import offline_lane_detect as lane  # noqa: E402


lane.prepare_windows_dll_search_path()


def ensure_runtime():
    lane.ensure_runtime()
    return lane


def latest_capture_image():
    candidates = sorted(
        (LANE_DEMO_DIR / "captures").glob("session_*/screenshots/*.*"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        if path.suffix.lower() in lane.IMAGE_EXTS:
            return path
    return None


def latest_capture_video():
    candidates = sorted(
        (LANE_DEMO_DIR / "captures").glob("session_*/videos/*.*"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        if path.suffix.lower() in lane.VIDEO_EXTS:
            return path
    return None

