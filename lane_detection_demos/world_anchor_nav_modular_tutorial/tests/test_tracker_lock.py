# -*- coding: utf-8 -*-
"""导航箭头状态机测试。

这个测试模拟两帧相近的左转候选。状态机收到足够稳定的候选后，应该锁定
一个 `LockedNavArrow`。
"""

import unittest
from types import SimpleNamespace

from nav_demo.models import NAV_LEFT, NavCandidate
from nav_demo.navigation import NavigationArrowTracker


def make_args():
    return SimpleNamespace(
        stability_window_seconds=3.2,
        max_candidate_history=5,
        stability_confirmations=2,
        stable_target_radius=130.0,
        arrow_smoothing_alpha=0.35,
        arrow_hold_seconds=6.0,
    )


class TrackerLockTest(unittest.TestCase):
    def test_locks_after_stable_candidates(self):
        tracker = NavigationArrowTracker(make_args())
        tracker.set_nav_mode(NAV_LEFT)
        first = NavCandidate(NAV_LEFT, (640, 600), (430, 320), 0.8, 20, NAV_LEFT, 10.0)
        second = NavCandidate(NAV_LEFT, (642, 602), (434, 322), 0.7, 19, NAV_LEFT, 10.5)
        self.assertIsNone(tracker.push(first, 10.0))
        locked = tracker.push(second, 10.5)
        self.assertIsNotNone(locked)
        self.assertEqual(locked.nav_mode, NAV_LEFT)
        self.assertGreater(locked.expires_at, 10.5)


if __name__ == "__main__":
    unittest.main()
