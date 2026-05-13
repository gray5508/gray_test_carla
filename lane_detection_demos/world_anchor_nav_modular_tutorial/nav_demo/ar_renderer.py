# -*- coding: utf-8 -*-
"""AR 箭头和调试几何绘制。

本模块里的图像都是 OpenCV 的 BGR 图像，不是 pygame 的 RGB surface。
因此颜色元组如 `(30, 90, 255)` 是 BGR 顺序。最后在 `app.py` 中才会把
BGR 转回 RGB，再交给 pygame 显示。
"""

from .runtime_deps import lane
from .geometry import (
    clamp_projected_pixel,
    project_ground_polygon,
    project_vehicle_ground_to_pixel,
    project_world_point_to_pixel,
    project_world_polygon,
    vehicle_ground_to_world_point,
)
from .models import DEFAULT_HEIGHT, DEFAULT_WIDTH, NAV_LEFT, NAV_RIGHT, NAV_STRAIGHT
from .world_anchor import (
    ground_arrow_polygon,
    ground_points_to_world,
    ground_segment_from_locked_arrow,
)

def draw_debug_geometry(bgr, result, args):
    """绘制 YOLOP mask、左右车道点和中心线，帮助理解检测结果。"""
    if result is None:
        return bgr

    out = bgr
    if args.show_debug_mask and result.clean_mask is not None:
        color = lane.np.zeros_like(out)
        color[result.clean_mask.astype(bool)] = (255, 255, 0)
        out = lane.cv2.addWeighted(out, 1.0, color, 0.28, 0.0)

    if args.show_debug_geometry:
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

def nav_color(nav_mode):
    """不同导航意图使用不同颜色，便于观察 straight/left/right。"""
    if nav_mode == NAV_STRAIGHT:
        return (30, 90, 255)
    if nav_mode == NAV_LEFT:
        return (255, 95, 70)
    if nav_mode == NAV_RIGHT:
        return (30, 200, 255)
    return (30, 90, 255)

def blend_overlay(base, overlay, alpha):
    """把 overlay 按透明度混合到 base 上，结果直接写回 base。"""
    lane.cv2.addWeighted(overlay, alpha, base, 1.0 - alpha, 0.0, dst=base)

def draw_ground_polygon_layer(bgr, points, args, color, alpha, width, height, outline=False, thickness=2):
    """绘制车辆局部地面多边形。适用于 ground 投影模式。"""
    projected = project_ground_polygon(points, args, width, height)
    if projected is None or len(projected) < 3:
        return False

    layer = bgr.copy()
    if outline:
        lane.cv2.polylines(layer, [projected], True, color, thickness, lane.cv2.LINE_AA)
    else:
        lane.cv2.fillPoly(layer, [projected], color, lane.cv2.LINE_AA)
    blend_overlay(bgr, layer, alpha)
    return True

def draw_world_polygon_layer(
    bgr,
    points_world,
    camera_transform,
    args,
    color,
    alpha,
    width,
    height,
    outline=False,
    thickness=2,
):
    """绘制世界坐标多边形。适用于 world 锚点模式。"""
    projected = project_world_polygon(points_world, camera_transform, args, width, height)
    if projected is None or len(projected) < 3:
        return False

    layer = bgr.copy()
    if outline:
        lane.cv2.polylines(layer, [projected], True, color, thickness, lane.cv2.LINE_AA)
    else:
        lane.cv2.fillPoly(layer, [projected], color, lane.cv2.LINE_AA)
    blend_overlay(bgr, layer, alpha)
    return True

def draw_ground_flow_chevrons(bgr, start_ground, target_ground, color, now, args):
    """在 ground 投影箭头上绘制沿方向流动的 V 形光标。"""
    vec = target_ground - start_ground
    length = float(lane.np.linalg.norm(vec))
    if length < 1.4:
        return

    direction = vec / length
    normal = lane.np.asarray([-direction[1], direction[0]], dtype=lane.np.float32)
    head_length = min(args.ground_arrow_head_length_m, max(0.45, length * 0.45))
    flow_start = min(length * 0.25, 1.3)
    span = max(0.1, length - head_length - flow_start)
    chevrons = max(0, int(args.arrow_chevrons))
    width = int(getattr(args, "width", DEFAULT_WIDTH))
    height = int(getattr(args, "height", DEFAULT_HEIGHT))

    moving = bgr.copy()
    drew_any = False
    for idx in range(chevrons):
        t = (now * args.arrow_flow_speed + idx / float(max(1, chevrons))) % 1.0
        center = start_ground + direction * (flow_start + span * t)
        tip = center + direction * (args.ground_arrow_flow_length_m * 0.55)
        back = center - direction * (args.ground_arrow_flow_length_m * 0.45)
        left = back + normal * (args.ground_arrow_body_width_m * 0.48)
        right = back - normal * (args.ground_arrow_body_width_m * 0.48)

        tip_px = project_vehicle_ground_to_pixel(tip[0], tip[1], args)
        left_px = project_vehicle_ground_to_pixel(left[0], left[1], args)
        right_px = project_vehicle_ground_to_pixel(right[0], right[1], args)
        if tip_px is None or left_px is None or right_px is None:
            continue

        tip_i = clamp_projected_pixel(tip_px, width, height)
        left_i = clamp_projected_pixel(left_px, width, height)
        right_i = clamp_projected_pixel(right_px, width, height)
        brightness = 0.22 + 0.48 * (1.0 - abs(t - 0.5) * 2.0)
        chevron_color = tuple(int(255 * brightness + color[channel] * (1.0 - brightness)) for channel in range(3))
        lane.cv2.line(moving, left_i, tip_i, chevron_color, 2, lane.cv2.LINE_AA)
        lane.cv2.line(moving, right_i, tip_i, chevron_color, 2, lane.cv2.LINE_AA)
        drew_any = True

    if drew_any:
        blend_overlay(bgr, moving, args.arrow_flow_alpha)

def draw_world_flow_chevrons(bgr, anchor, camera_transform, color, now, args):
    """在世界锚点箭头上绘制流动 chevron。"""
    start_ground = anchor.start_ground
    target_ground = anchor.target_ground
    vec = target_ground - start_ground
    length = float(lane.np.linalg.norm(vec))
    if length < 1.4:
        return

    direction = vec / length
    normal = lane.np.asarray([-direction[1], direction[0]], dtype=lane.np.float32)
    head_length = min(args.ground_arrow_head_length_m, max(0.45, length * 0.45))
    flow_start = min(length * 0.25, 1.3)
    span = max(0.1, length - head_length - flow_start)
    chevrons = max(0, int(args.arrow_chevrons))
    width = int(getattr(args, "width", DEFAULT_WIDTH))
    height = int(getattr(args, "height", DEFAULT_HEIGHT))

    moving = bgr.copy()
    drew_any = False
    for idx in range(chevrons):
        t = (now * args.arrow_flow_speed + idx / float(max(1, chevrons))) % 1.0
        center = start_ground + direction * (flow_start + span * t)
        tip = center + direction * (args.ground_arrow_flow_length_m * 0.55)
        back = center - direction * (args.ground_arrow_flow_length_m * 0.45)
        left = back + normal * (args.ground_arrow_body_width_m * 0.48)
        right = back - normal * (args.ground_arrow_body_width_m * 0.48)

        tip_world = vehicle_ground_to_world_point(tip[0], tip[1], anchor.vehicle_to_world, args)
        left_world = vehicle_ground_to_world_point(left[0], left[1], anchor.vehicle_to_world, args)
        right_world = vehicle_ground_to_world_point(right[0], right[1], anchor.vehicle_to_world, args)
        tip_px = project_world_point_to_pixel(tip_world, camera_transform, args)
        left_px = project_world_point_to_pixel(left_world, camera_transform, args)
        right_px = project_world_point_to_pixel(right_world, camera_transform, args)
        if tip_px is None or left_px is None or right_px is None:
            continue

        tip_i = clamp_projected_pixel((tip_px[0], tip_px[1]), width, height)
        left_i = clamp_projected_pixel((left_px[0], left_px[1]), width, height)
        right_i = clamp_projected_pixel((right_px[0], right_px[1]), width, height)
        brightness = 0.22 + 0.48 * (1.0 - abs(t - 0.5) * 2.0)
        chevron_color = tuple(int(255 * brightness + color[channel] * (1.0 - brightness)) for channel in range(3))
        lane.cv2.line(moving, left_i, tip_i, chevron_color, 2, lane.cv2.LINE_AA)
        lane.cv2.line(moving, right_i, tip_i, chevron_color, 2, lane.cv2.LINE_AA)
        drew_any = True

    if drew_any:
        blend_overlay(bgr, moving, args.arrow_flow_alpha)

def draw_ground_projected_arrow(bgr, locked_arrow, now, args):
    """绘制每帧跟随车辆局部坐标的地面箭头。"""
    start_ground, target_ground = ground_segment_from_locked_arrow(locked_arrow, args)
    if start_ground is None or target_ground is None:
        return False

    vec = target_ground - start_ground
    length = float(lane.np.linalg.norm(vec))
    if length < args.ground_arrow_min_length_m:
        return False

    height, width = bgr.shape[:2]
    color = nav_color(locked_arrow.nav_mode)
    pulse = 0.5 + 0.5 * lane.np.sin(now * args.arrow_pulse_speed * 6.2831853)

    glow_points = ground_arrow_polygon(
        start_ground,
        target_ground,
        args.ground_arrow_body_width_m + args.ground_arrow_glow_extra_width_m,
        args.ground_arrow_head_width_m + args.ground_arrow_glow_extra_width_m * 1.8,
        args.ground_arrow_head_length_m,
    )
    main_points = ground_arrow_polygon(
        start_ground,
        target_ground,
        args.ground_arrow_body_width_m,
        args.ground_arrow_head_width_m,
        args.ground_arrow_head_length_m,
    )
    inner_points = ground_arrow_polygon(
        start_ground + (target_ground - start_ground) * 0.12,
        target_ground - (target_ground - start_ground) * 0.10,
        args.ground_arrow_body_width_m * 0.36,
        args.ground_arrow_head_width_m * 0.36,
        args.ground_arrow_head_length_m * 0.72,
    )
    if glow_points is None or main_points is None:
        return False

    if not draw_ground_polygon_layer(
        bgr,
        glow_points,
        args,
        color,
        args.ground_arrow_glow_alpha + pulse * 0.04,
        width,
        height,
    ):
        return False

    draw_ground_polygon_layer(
        bgr,
        main_points,
        args,
        color,
        args.ground_arrow_alpha,
        width,
        height,
    )
    if inner_points is not None:
        draw_ground_polygon_layer(
            bgr,
            inner_points,
            args,
            (255, 255, 255),
            args.ground_arrow_inner_alpha + pulse * 0.04,
            width,
            height,
        )
    draw_ground_polygon_layer(
        bgr,
        main_points,
        args,
        color,
        args.ground_arrow_edge_alpha,
        width,
        height,
        outline=True,
        thickness=2,
    )
    draw_ground_flow_chevrons(bgr, start_ground, target_ground, color, now, args)
    return True

def draw_world_anchored_arrow(bgr, anchor, camera_transform, now, args):
    """绘制固定在 CARLA 世界坐标中的 AR 箭头。"""
    if anchor is None:
        return False

    vec = anchor.target_ground - anchor.start_ground
    length = float(lane.np.linalg.norm(vec))
    if length < args.ground_arrow_min_length_m:
        return False

    height, width = bgr.shape[:2]
    color = nav_color(anchor.nav_mode)
    pulse = 0.5 + 0.5 * lane.np.sin(now * args.arrow_pulse_speed * 6.2831853)

    glow_ground = ground_arrow_polygon(
        anchor.start_ground,
        anchor.target_ground,
        args.ground_arrow_body_width_m + args.ground_arrow_glow_extra_width_m,
        args.ground_arrow_head_width_m + args.ground_arrow_glow_extra_width_m * 1.8,
        args.ground_arrow_head_length_m,
    )
    main_ground = ground_arrow_polygon(
        anchor.start_ground,
        anchor.target_ground,
        args.ground_arrow_body_width_m,
        args.ground_arrow_head_width_m,
        args.ground_arrow_head_length_m,
    )
    inner_ground = ground_arrow_polygon(
        anchor.start_ground + (anchor.target_ground - anchor.start_ground) * 0.12,
        anchor.target_ground - (anchor.target_ground - anchor.start_ground) * 0.10,
        args.ground_arrow_body_width_m * 0.36,
        args.ground_arrow_head_width_m * 0.36,
        args.ground_arrow_head_length_m * 0.72,
    )
    if glow_ground is None or main_ground is None:
        return False

    glow_world = ground_points_to_world(glow_ground, anchor, args)
    main_world = ground_points_to_world(main_ground, anchor, args)
    inner_world = ground_points_to_world(inner_ground, anchor, args) if inner_ground is not None else None

    if not draw_world_polygon_layer(
        bgr,
        glow_world,
        camera_transform,
        args,
        color,
        args.ground_arrow_glow_alpha + pulse * 0.04,
        width,
        height,
    ):
        return False

    draw_world_polygon_layer(
        bgr,
        main_world,
        camera_transform,
        args,
        color,
        args.ground_arrow_alpha,
        width,
        height,
    )
    if inner_world is not None:
        draw_world_polygon_layer(
            bgr,
            inner_world,
            camera_transform,
            args,
            (255, 255, 255),
            args.ground_arrow_inner_alpha + pulse * 0.04,
            width,
            height,
        )
    draw_world_polygon_layer(
        bgr,
        main_world,
        camera_transform,
        args,
        color,
        args.ground_arrow_edge_alpha,
        width,
        height,
        outline=True,
        thickness=2,
    )
    draw_world_flow_chevrons(bgr, anchor, camera_transform, color, now, args)

    target_pixel = project_world_point_to_pixel(anchor.target_world, camera_transform, args)
    if target_pixel is not None:
        if args.world_anchor_expire_mode == "pass":
            label = "WORLD {} | until pass | conf {:.2f}".format(
                anchor.nav_mode.upper(),
                anchor.confidence,
            )
        else:
            seconds_left = max(0.0, anchor.expires_at - now)
            label = "WORLD {} | hold {:.1f}s | conf {:.2f}".format(
                anchor.nav_mode.upper(),
                seconds_left,
                anchor.confidence,
            )
        x = max(12, min(width - 420, int(target_pixel[0]) + 12))
        y = max(28, int(target_pixel[1]) - 12)
        lane.cv2.putText(bgr, label, (x, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.66, (20, 20, 20), 3, lane.cv2.LINE_AA)
        lane.cv2.putText(bgr, label, (x, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.66, (255, 255, 255), 1, lane.cv2.LINE_AA)
    return True

def draw_glow_line(bgr, start, target, color, now, args):
    """屏幕空间发光箭头，用作 screen 模式和投影失败时的 fallback。"""
    start = lane.np.asarray(start, dtype=lane.np.float32)
    target = lane.np.asarray(target, dtype=lane.np.float32)
    vec = target - start
    length = float(lane.np.linalg.norm(vec))
    if length < 8.0:
        return
    direction = vec / length
    normal = lane.np.asarray([-direction[1], direction[0]], dtype=lane.np.float32)

    pulse = 0.5 + 0.5 * lane.np.sin(now * args.arrow_pulse_speed * 6.2831853)
    main_width = int(args.arrow_width + pulse * 2.0)
    glow_width = int(args.arrow_glow_width + pulse * 7.0)
    head_len = min(args.arrow_head_max_len, max(args.arrow_head_min_len, length * 0.28))
    head_half = main_width * (1.65 + 0.15 * pulse)
    body_end = target - direction * (head_len * 0.72)

    # 分层绘制：先画柔和外光，再画中层光，最后画实体线。
    # 分层的好处是可以分别调 alpha，让箭头既显眼又不完全遮住路面。
    glow = bgr.copy()
    lane.cv2.line(glow, tuple(start.astype(int)), tuple(body_end.astype(int)), color, glow_width, lane.cv2.LINE_AA)
    blend_overlay(bgr, glow, args.arrow_glow_alpha)

    glow_mid = bgr.copy()
    lane.cv2.line(glow_mid, tuple(start.astype(int)), tuple(body_end.astype(int)), color, max(main_width + 9, 10), lane.cv2.LINE_AA)
    blend_overlay(bgr, glow_mid, args.arrow_mid_alpha)

    body = bgr.copy()
    lane.cv2.line(body, tuple(start.astype(int)), tuple(body_end.astype(int)), color, main_width, lane.cv2.LINE_AA)
    blend_overlay(bgr, body, args.arrow_body_alpha)

    tip = target
    base = target - direction * head_len
    left = base + normal * head_half
    right = base - normal * head_half
    head = lane.np.asarray([tip, left, right], dtype=lane.np.int32)
    head_layer = bgr.copy()
    lane.cv2.fillConvexPoly(head_layer, head, color, lane.cv2.LINE_AA)
    blend_overlay(bgr, head_layer, 0.86)

    inner = bgr.copy()
    inner_tip = target - direction * 7.0
    inner_base = target - direction * (head_len * 0.62)
    inner_left = inner_base + normal * (head_half * 0.45)
    inner_right = inner_base - normal * (head_half * 0.45)
    inner_head = lane.np.asarray([inner_tip, inner_left, inner_right], dtype=lane.np.int32)
    lane.cv2.fillConvexPoly(inner, inner_head, (255, 255, 255), lane.cv2.LINE_AA)
    blend_overlay(bgr, inner, 0.22 + 0.16 * pulse)

    # 移动 chevron 和可选粒子让箭头有“流动方向”的感觉，不需要外部素材。
    moving = bgr.copy()
    span = max(1.0, length - head_len - 18.0)
    chevrons = max(1, int(args.arrow_chevrons))
    for idx in range(chevrons):
        t = (now * args.arrow_flow_speed + idx / float(chevrons)) % 1.0
        center = start + direction * (18.0 + span * t)
        tip_c = center + direction * (args.arrow_chevron_len * 0.60)
        left_c = center - direction * (args.arrow_chevron_len * 0.45) + normal * (main_width * 0.95)
        right_c = center - direction * (args.arrow_chevron_len * 0.45) - normal * (main_width * 0.95)
        brightness = 0.25 + 0.50 * (1.0 - abs(t - 0.5) * 2.0)
        chevron_color = tuple(int(255 * brightness + color[channel] * (1.0 - brightness)) for channel in range(3))
        lane.cv2.line(moving, tuple(left_c.astype(int)), tuple(tip_c.astype(int)), chevron_color, 3, lane.cv2.LINE_AA)
        lane.cv2.line(moving, tuple(right_c.astype(int)), tuple(tip_c.astype(int)), chevron_color, 3, lane.cv2.LINE_AA)
        if args.arrow_show_particles:
            particle = center - direction * 6.0
            radius = int(2 + 2 * brightness)
            lane.cv2.circle(moving, tuple(particle.astype(int)), radius, (255, 255, 255), -1, lane.cv2.LINE_AA)
    blend_overlay(bgr, moving, args.arrow_flow_alpha)

    # 起点脉冲让箭头更像一个被投影到路面上的 AR 标记。
    anchor = bgr.copy()
    radius = int(args.arrow_anchor_radius + pulse * 5.0)
    lane.cv2.circle(anchor, tuple(start.astype(int)), radius + 7, color, 2, lane.cv2.LINE_AA)
    lane.cv2.circle(anchor, tuple(start.astype(int)), radius, (255, 255, 255), 2, lane.cv2.LINE_AA)
    blend_overlay(bgr, anchor, 0.50)

def draw_simple_arrow(bgr, locked_arrow, now):
    """最简单的 OpenCV 箭头，适合调试几何，不追求 AR 视觉效果。"""
    color = nav_color(locked_arrow.nav_mode)
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

def draw_locked_arrow(bgr, locked_arrow, now, args):
    """根据参数选择 screen/ground 风格绘制锁定箭头。"""
    if locked_arrow is None:
        return

    seconds_left = max(0.0, locked_arrow.expires_at - now)
    color = nav_color(locked_arrow.nav_mode)
    if args.arrow_projection == "ground":
        if not draw_ground_projected_arrow(bgr, locked_arrow, now, args):
            draw_glow_line(bgr, locked_arrow.start, locked_arrow.target, color, now, args)
    elif args.arrow_style == "simple":
        draw_simple_arrow(bgr, locked_arrow, now)
    else:
        draw_glow_line(bgr, locked_arrow.start, locked_arrow.target, color, now, args)

    label = "NAV {} | hold {:.1f}s | conf {:.2f}".format(
        locked_arrow.nav_mode.upper(),
        seconds_left,
        locked_arrow.confidence,
    )
    x = max(12, min(bgr.shape[1] - 360, locked_arrow.target[0] + 12))
    y = max(28, locked_arrow.target[1] - 12)
    lane.cv2.putText(bgr, label, (x, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.66, (20, 20, 20), 3, lane.cv2.LINE_AA)
    lane.cv2.putText(bgr, label, (x, y), lane.cv2.FONT_HERSHEY_SIMPLEX, 0.66, (255, 255, 255), 1, lane.cv2.LINE_AA)
