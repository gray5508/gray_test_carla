# -*- coding: utf-8 -*-
"""导航意图与箭头稳定锁定。

YOLOP 每次推理只能给出“这一帧看起来怎样”。真实 UI 不能直接照着每一帧画，
否则箭头会抖动。因此本模块做两件事：

    1. 根据当前导航意图 straight/left/right，从车道几何中生成候选箭头。
    2. 连续收集多个候选，如果目标点足够接近，才锁定一个可显示箭头。
"""

from .geometry import (
    arrow_start_pixel,
    blend_points,
    choose_straight_target,
    choose_turn_target,
    mean_point,
    point_distance,
    straight_arrow_start_pixel,
    straight_line_inside_current_lane,
)
from .models import LockedNavArrow, NAV_NONE, NAV_STRAIGHT, NavCandidate

class NavigationArrowTracker(object):
    """把多帧候选箭头变成稳定显示箭头的状态机。"""

    def __init__(self, args):
        self.args = args
        self.nav_mode = NAV_NONE
        self.candidates = []
        self.locked = None
        self.last_status = "choose 1/2/3"

    def set_nav_mode(self, nav_mode):
        """切换导航意图。

        一旦意图变化，旧候选和旧锁定箭头都不再可信，所以要清空。
        """
        if nav_mode != self.nav_mode:
            self.nav_mode = nav_mode
            self.candidates = []
            self.locked = None
            self.last_status = "nav set to {}".format(nav_mode)

    def clear(self):
        """清除导航意图和当前箭头。对应键盘 `C` 或 `0`。"""
        self.nav_mode = NAV_NONE
        self.candidates = []
        self.locked = None
        self.last_status = "cleared"

    def active_arrow(self, now):
        """返回当前仍然有效的锁定箭头。过期或意图不匹配时返回 None。"""
        if self.locked is None:
            return None
        if now > self.locked.expires_at:
            return None
        if self.locked.nav_mode != self.nav_mode:
            return None
        return self.locked

    def push(self, candidate, now):
        """向状态机推入一个候选箭头，并在稳定时锁定。

        稳定性的判断不是看置信度最高的一帧，而是看最近几次候选目标点是否
        聚在一起。这样可以过滤掉单帧 YOLOP 抖动和车道扫描误差。
        """
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

def make_nav_candidate(result, nav_mode, args, width, height, now):
    """把一帧车道几何结果转换成导航候选箭头。

    这里是“导航意图”和“视觉检测”的交汇点：
        - nav_mode 来自键盘或上层规划。
        - result 来自 YOLOP lane mask 的几何解析。
        - 如果两者匹配，才返回 NavCandidate。
    """
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
