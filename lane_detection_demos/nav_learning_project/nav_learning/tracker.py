from .geometry import blend_points, mean_point, point_distance
from .models import LockedNavArrow, NAV_NONE


class NavigationArrowTracker(object):
    """Collects candidate arrows and locks a stable one for a few seconds."""

    def __init__(self, config):
        self.config = config
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
        config = self.config
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
            if now - item.created_at <= config.stability_window_seconds
            and item.nav_mode == self.nav_mode
        ][-config.max_candidate_history :]

        if len(self.candidates) < config.stability_confirmations:
            self.last_status = "collecting {} stable samples {}/{}".format(
                self.nav_mode,
                len(self.candidates),
                config.stability_confirmations,
            )
            return self.active_arrow(now)

        recent = self.candidates[-config.stability_confirmations :]
        target_mean = mean_point([item.target for item in recent])
        start_mean = mean_point([item.start for item in recent])
        if target_mean is None or start_mean is None:
            self.last_status = "candidate mean failed"
            return self.active_arrow(now)

        max_spread = max(point_distance(item.target, target_mean) for item in recent)
        if max_spread > config.stable_target_radius:
            self.last_status = "{} target unstable {:.0f}px".format(self.nav_mode, max_spread)
            return self.active_arrow(now)

        confidence = sum(item.confidence for item in recent) / float(len(recent))
        if self.locked is not None and now <= self.locked.expires_at:
            start = blend_points(self.locked.start, start_mean, config.arrow_smoothing_alpha)
            target = blend_points(self.locked.target, target_mean, config.arrow_smoothing_alpha)
        else:
            start = start_mean
            target = target_mean

        self.locked = LockedNavArrow(
            nav_mode=self.nav_mode,
            start=start,
            target=target,
            confidence=confidence,
            locked_at=now,
            expires_at=now + config.arrow_hold_seconds,
        )
        self.last_status = "locked {} for {:.1f}s".format(self.nav_mode, config.arrow_hold_seconds)
        return self.locked

