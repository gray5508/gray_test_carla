from pathlib import Path
import sys
import time


SUBPROJECT_DIR = Path(__file__).resolve().parents[1]
if str(SUBPROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(SUBPROJECT_DIR))

from nav_learning.models import NAV_STRAIGHT, NavCandidate  # noqa: E402
from nav_learning.settings import AppConfig  # noqa: E402
from nav_learning.tracker import NavigationArrowTracker  # noqa: E402


def main():
    config = AppConfig()
    tracker = NavigationArrowTracker(config)
    tracker.set_nav_mode(NAV_STRAIGHT)

    now = time.time()
    samples = [
        ((640, 560), (640, 410)),
        ((641, 561), (642, 412)),
        ((639, 559), (641, 411)),
        ((640, 560), (640, 410)),
    ]

    print("Tracker test: push several slightly jittered straight candidates.")
    for idx, (start, target) in enumerate(samples, 1):
        candidate = NavCandidate(
            nav_mode=NAV_STRAIGHT,
            start=start,
            target=target,
            confidence=0.80 + idx * 0.02,
            center_points=25,
            direction=NAV_STRAIGHT,
            created_at=now + idx * 0.3,
        )
        active = tracker.push(candidate, now + idx * 0.3)
        print(
            "#{:02d} status={} active={}".format(
                idx,
                tracker.last_status,
                active is not None,
            )
        )
        if active is not None:
            print("     locked start={} target={} conf={:.2f}".format(active.start, active.target, active.confidence))


if __name__ == "__main__":
    main()

