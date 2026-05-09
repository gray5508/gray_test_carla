from .geometry import arrow_start_pixel
from .geometry import choose_straight_target
from .geometry import choose_turn_target
from .geometry import straight_arrow_start_pixel
from .geometry import straight_line_inside_current_lane
from .models import NAV_NONE, NAV_STRAIGHT, NavCandidate


def make_turn_args(config):
    class TurnArgs(object):
        pass

    turn_args = TurnArgs()
    turn_args.roi_top_ratio = config.roi_top_ratio
    turn_args.scan_top_ratio = config.scan_top_ratio
    turn_args.scan_bottom_ratio = config.scan_bottom_ratio
    turn_args.scan_rows = config.scan_rows
    turn_args.scan_band = config.scan_band
    turn_args.min_segment_width = config.min_segment_width
    turn_args.max_segment_width_ratio = config.max_segment_width_ratio
    turn_args.vehicle_x_ratio = config.vehicle_x_ratio
    turn_args.initial_half_lane_width_ratio = config.initial_half_lane_width_ratio
    turn_args.max_jump_ratio = config.max_jump_ratio
    turn_args.smooth_samples = config.smooth_samples
    turn_args.arrow_start_y_ratio = config.arrow_start_y_ratio
    turn_args.turn_shift_ratio = config.turn_shift_ratio
    turn_args.target_average_points = config.target_average_points
    turn_args.min_center_points = config.min_center_points
    turn_args.min_confidence = config.min_confidence
    turn_args.draw_raw_mask = False
    return turn_args


class LaneInterpreter(object):
    """Turns a YOLOP lane mask result into a navigation candidate."""

    def __init__(self, config):
        self.config = config

    def make_candidate(self, result, nav_mode, width, height, now):
        config = self.config
        if nav_mode == NAV_NONE or result is None:
            return None
        if result.confidence < config.min_confidence:
            return None
        if len(result.center_points or []) < config.min_center_points:
            return None

        points = result.smooth_center or result.center_points or []

        if nav_mode == NAV_STRAIGHT:
            start = straight_arrow_start_pixel(width, height, config)
            target = choose_straight_target(points, start, width, height, config)
            if target is None:
                return None
            if not straight_line_inside_current_lane(result, start, target, width, config):
                return None
            direction = NAV_STRAIGHT
        else:
            start = arrow_start_pixel(width, height, config)
            target, direction, shift = choose_turn_target(points, start, width, height, nav_mode, config)
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

