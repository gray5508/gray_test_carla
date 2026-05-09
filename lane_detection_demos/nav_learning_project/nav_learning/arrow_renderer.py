from .geometry import fmt_point
from .models import NAV_LEFT, NAV_RIGHT, NAV_STRAIGHT
from .paths import ensure_runtime, lane


class ArrowRenderer(object):
    """Draws debug lane geometry and the final navigation arrow."""

    def __init__(self, config):
        ensure_runtime()
        self.config = config

    def nav_color(self, nav_mode):
        if nav_mode == NAV_STRAIGHT:
            return (30, 90, 255)
        if nav_mode == NAV_LEFT:
            return (255, 95, 70)
        if nav_mode == NAV_RIGHT:
            return (30, 200, 255)
        return (30, 90, 255)

    def blend_overlay(self, base, overlay, alpha):
        lane.cv2.addWeighted(overlay, alpha, base, 1.0 - alpha, 0.0, dst=base)

    def draw_lane_debug(self, bgr, result, show_geometry=False, show_mask=False):
        if result is None:
            return bgr

        out = bgr
        if show_mask and result.clean_mask is not None:
            color = lane.np.zeros_like(out)
            color[result.clean_mask.astype(bool)] = (255, 255, 0)
            out = lane.cv2.addWeighted(out, 1.0, color, 0.28, 0.0)

        if show_geometry:
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

    def draw_glow_line(self, bgr, start, target, color, now):
        config = self.config
        start = lane.np.asarray(start, dtype=lane.np.float32)
        target = lane.np.asarray(target, dtype=lane.np.float32)
        vec = target - start
        length = float(lane.np.linalg.norm(vec))
        if length < 8.0:
            return
        direction = vec / length
        normal = lane.np.asarray([-direction[1], direction[0]], dtype=lane.np.float32)

        pulse = 0.5 + 0.5 * lane.np.sin(now * config.arrow_pulse_speed * 6.2831853)
        main_width = int(config.arrow_width + pulse * 2.0)
        glow_width = int(config.arrow_glow_width + pulse * 7.0)
        head_len = min(config.arrow_head_max_len, max(config.arrow_head_min_len, length * 0.28))
        head_half = main_width * (1.65 + 0.15 * pulse)
        body_end = target - direction * (head_len * 0.72)

        glow = bgr.copy()
        lane.cv2.line(glow, tuple(start.astype(int)), tuple(body_end.astype(int)), color, glow_width, lane.cv2.LINE_AA)
        self.blend_overlay(bgr, glow, config.arrow_glow_alpha)

        glow_mid = bgr.copy()
        lane.cv2.line(
            glow_mid,
            tuple(start.astype(int)),
            tuple(body_end.astype(int)),
            color,
            max(main_width + 9, 10),
            lane.cv2.LINE_AA,
        )
        self.blend_overlay(bgr, glow_mid, config.arrow_mid_alpha)

        body = bgr.copy()
        lane.cv2.line(body, tuple(start.astype(int)), tuple(body_end.astype(int)), color, main_width, lane.cv2.LINE_AA)
        self.blend_overlay(bgr, body, config.arrow_body_alpha)

        tip = target
        base = target - direction * head_len
        left = base + normal * head_half
        right = base - normal * head_half
        head = lane.np.asarray([tip, left, right], dtype=lane.np.int32)
        head_layer = bgr.copy()
        lane.cv2.fillConvexPoly(head_layer, head, color, lane.cv2.LINE_AA)
        self.blend_overlay(bgr, head_layer, 0.86)

        inner = bgr.copy()
        inner_tip = target - direction * 7.0
        inner_base = target - direction * (head_len * 0.62)
        inner_left = inner_base + normal * (head_half * 0.45)
        inner_right = inner_base - normal * (head_half * 0.45)
        inner_head = lane.np.asarray([inner_tip, inner_left, inner_right], dtype=lane.np.int32)
        lane.cv2.fillConvexPoly(inner, inner_head, (255, 255, 255), lane.cv2.LINE_AA)
        self.blend_overlay(bgr, inner, 0.22 + 0.16 * pulse)

        moving = bgr.copy()
        span = max(1.0, length - head_len - 18.0)
        chevrons = max(1, int(config.arrow_chevrons))
        for idx in range(chevrons):
            t = (now * config.arrow_flow_speed + idx / float(chevrons)) % 1.0
            center = start + direction * (18.0 + span * t)
            tip_c = center + direction * (config.arrow_chevron_len * 0.60)
            left_c = center - direction * (config.arrow_chevron_len * 0.45) + normal * (main_width * 0.95)
            right_c = center - direction * (config.arrow_chevron_len * 0.45) - normal * (main_width * 0.95)
            brightness = 0.25 + 0.50 * (1.0 - abs(t - 0.5) * 2.0)
            chevron_color = tuple(
                int(255 * brightness + color[channel] * (1.0 - brightness))
                for channel in range(3)
            )
            lane.cv2.line(moving, tuple(left_c.astype(int)), tuple(tip_c.astype(int)), chevron_color, 3, lane.cv2.LINE_AA)
            lane.cv2.line(moving, tuple(right_c.astype(int)), tuple(tip_c.astype(int)), chevron_color, 3, lane.cv2.LINE_AA)
            if config.arrow_show_particles:
                particle = center - direction * 6.0
                radius = int(2 + 2 * brightness)
                lane.cv2.circle(moving, tuple(particle.astype(int)), radius, (255, 255, 255), -1, lane.cv2.LINE_AA)
        self.blend_overlay(bgr, moving, config.arrow_flow_alpha)

        anchor = bgr.copy()
        radius = int(config.arrow_anchor_radius + pulse * 5.0)
        lane.cv2.circle(anchor, tuple(start.astype(int)), radius + 7, color, 2, lane.cv2.LINE_AA)
        lane.cv2.circle(anchor, tuple(start.astype(int)), radius, (255, 255, 255), 2, lane.cv2.LINE_AA)
        self.blend_overlay(bgr, anchor, 0.50)

    def draw_simple_arrow(self, bgr, locked_arrow, now):
        color = self.nav_color(locked_arrow.nav_mode)
        lane.cv2.arrowedLine(
            bgr,
            tuple(locked_arrow.start),
            tuple(locked_arrow.target),
            color,
            5,
            lane.cv2.LINE_AA,
            tipLength=0.18,
        )
        lane.cv2.circle(bgr, tuple(locked_arrow.start), 7, color, -1, lane.cv2.LINE_AA)
        lane.cv2.circle(bgr, tuple(locked_arrow.target), 8, color, -1, lane.cv2.LINE_AA)

    def draw_locked_arrow(self, bgr, locked_arrow, now):
        if locked_arrow is None:
            return

        seconds_left = max(0.0, locked_arrow.expires_at - now)
        color = self.nav_color(locked_arrow.nav_mode)
        if self.config.arrow_style == "simple":
            self.draw_simple_arrow(bgr, locked_arrow, now)
        else:
            self.draw_glow_line(bgr, locked_arrow.start, locked_arrow.target, color, now)

        label = "NAV {} | hold {:.1f}s | conf {:.2f}".format(
            locked_arrow.nav_mode.upper(),
            seconds_left,
            locked_arrow.confidence,
        )
        x = max(12, min(bgr.shape[1] - 360, locked_arrow.target[0] + 12))
        y = max(28, locked_arrow.target[1] - 12)
        lane.cv2.putText(bgr, label, (x, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.66, (20, 20, 20), 3, lane.cv2.LINE_AA)
        lane.cv2.putText(bgr, label, (x, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.66, (255, 255, 255), 1, lane.cv2.LINE_AA)

    def draw_detection_status(self, bgr, packet, tracker, detecting):
        lines = ["nav intent: {}".format(tracker.nav_mode.upper())]
        if packet is None:
            lines.append("YOLOP: waiting")
        elif packet.error:
            lines.append("YOLOP error: {}".format(packet.error[:80]))
        else:
            lines.append("YOLOP: frame {} | {:.0f} ms | nav {}".format(packet.frame_id, packet.inference_ms, packet.nav_mode))
            if packet.result is not None:
                lines.append(
                    "geometry: {} | conf {:.2f} | pts {}".format(
                        packet.result.turn_direction,
                        packet.result.confidence,
                        len(packet.result.center_points or []),
                    )
                )
            if packet.candidate is not None:
                lines.append("candidate target: {}".format(fmt_point(packet.candidate.target)))
        lines.append("tracker: {}".format(tracker.last_status))
        if detecting:
            lines.append("detecting...")

        y = 28
        for text in lines[:6]:
            lane.cv2.putText(bgr, text, (18, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.68, (20, 20, 20), 3, lane.cv2.LINE_AA)
            lane.cv2.putText(bgr, text, (18, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 1, lane.cv2.LINE_AA)
            y += 26

