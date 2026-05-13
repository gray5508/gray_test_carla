# -*- coding: utf-8 -*-
"""世界锚点箭头状态。

三种箭头投影方式的区别：

    - screen：箭头直接粘在屏幕像素上，车辆动了也不具备真实空间感。
    - ground：箭头每帧按当前车辆局部坐标重算，像始终挂在车前方。
    - world：箭头锁定后转成 CARLA 世界坐标，之后像画在地面上。

本模块负责第三种方式，也就是本教程的核心。
"""

from .runtime_deps import lane
from .geometry import (
    pixel_to_vehicle_ground,
    straight_right_meters,
    vehicle_ground_to_world_point,
    world_point_to_vehicle_local,
)
from .models import NAV_STRAIGHT, WorldArrowAnchor

def scaled_ground_segment(start, target, args):
    """按参数缩短箭头长度，避免视觉上过长覆盖太多路面。"""
    scale = max(0.10, min(1.0, float(args.render_arrow_length_scale)))
    return start, start + (target - start) * scale

def ground_segment_from_locked_arrow(locked_arrow, args):
    """把锁定箭头从屏幕像素恢复成车辆局部地面线段。

    直行箭头直接使用米制参数更稳定；转弯箭头来自 YOLOP 像素目标点，
    因此需要通过 `pixel_to_vehicle_ground()` 反投影到地面。
    """
    if locked_arrow.nav_mode == NAV_STRAIGHT:
        start = lane.np.asarray(
            [args.arrow_start_meters, straight_right_meters(args)],
            dtype=lane.np.float32,
        )
        target = lane.np.asarray(
            [args.straight_target_forward_meters, straight_right_meters(args)],
            dtype=lane.np.float32,
        )
        return scaled_ground_segment(start, target, args)

    start_ground = pixel_to_vehicle_ground(locked_arrow.start, args)
    target_ground = pixel_to_vehicle_ground(locked_arrow.target, args)
    if start_ground is None or target_ground is None:
        return None, None
    start = lane.np.asarray(start_ground, dtype=lane.np.float32)
    target = lane.np.asarray(target_ground, dtype=lane.np.float32)
    return scaled_ground_segment(start, target, args)

def ground_arrow_polygon(start_ground, target_ground, body_width, head_width, head_length):
    """根据地面起点和终点生成箭头七边形。

    返回的每个点都是 `(forward_m, right_m)`，单位是米。绘制时再根据
    当前投影模式把这些点投影到屏幕。
    """
    vec = target_ground - start_ground
    length = float(lane.np.linalg.norm(vec))
    if length < 0.35:
        return None

    direction = vec / length
    normal = lane.np.asarray([-direction[1], direction[0]], dtype=lane.np.float32)
    head_length = min(float(head_length), max(0.45, length * 0.45))
    body_end = target_ground - direction * head_length
    body_half = max(0.05, float(body_width) * 0.5)
    head_half = max(body_half * 1.15, float(head_width) * 0.5)

    return [
        start_ground + normal * body_half,
        body_end + normal * body_half,
        body_end + normal * head_half,
        target_ground,
        body_end - normal * head_half,
        body_end - normal * body_half,
        start_ground - normal * body_half,
    ]

def ground_points_to_world(points_ground, anchor, args):
    """把一组车辆局部地面点转换成世界坐标点。"""
    return [
        vehicle_ground_to_world_point(float(point[0]), float(point[1]), anchor.vehicle_to_world, args)
        for point in points_ground
    ]

def create_world_arrow_anchor(locked_arrow, vehicle_transform, now, args):
    """锁定瞬间创建世界锚点。

    这一步只在箭头刚稳定时做一次：把车辆局部地面线段和端点转成世界坐标。
    后续每帧只重新投影这些世界点，不再跟随车辆局部坐标移动。
    """
    start_ground, target_ground = ground_segment_from_locked_arrow(locked_arrow, args)
    if start_ground is None or target_ground is None:
        return None
    if float(lane.np.linalg.norm(target_ground - start_ground)) < args.ground_arrow_min_length_m:
        return None

    vehicle_to_world = lane.np.asarray(vehicle_transform.get_matrix(), dtype=float)
    start_world = vehicle_ground_to_world_point(start_ground[0], start_ground[1], vehicle_to_world, args)
    target_world = vehicle_ground_to_world_point(target_ground[0], target_ground[1], vehicle_to_world, args)
    return WorldArrowAnchor(
        nav_mode=locked_arrow.nav_mode,
        start_ground=start_ground,
        target_ground=target_ground,
        vehicle_to_world=vehicle_to_world,
        start_world=start_world,
        target_world=target_world,
        confidence=locked_arrow.confidence,
        created_at=now,
        expires_at=locked_arrow.expires_at,
    )

class WorldArrowAnchorTracker(object):
    """维护当前世界锚点，并决定它何时过期。"""

    def __init__(self, args):
        self.args = args
        self.anchor = None
        self.last_status = "no world anchor"

    def clear(self):
        """清除当前世界锚点。导航意图变化或车辆开过锚点时会调用。"""
        self.anchor = None
        self.last_status = "world anchor cleared"

    def pass_reference_world(self, anchor):
        """选择用起点、中心点或终点判断车辆是否已经开过箭头。"""
        if self.args.world_anchor_pass_point == "start":
            return anchor.start_world
        if self.args.world_anchor_pass_point == "center":
            return (anchor.start_world + anchor.target_world) * 0.5
        return anchor.target_world

    def has_vehicle_passed_anchor(self, anchor, vehicle_transform):
        """判断车辆是否已经开过世界锚点参考点。"""
        reference_world = self.pass_reference_world(anchor)
        reference_local = world_point_to_vehicle_local(reference_world, vehicle_transform)
        return float(reference_local[0]) <= float(self.args.world_anchor_pass_margin_m)

    def update(self, locked_arrow, vehicle_transform, now):
        """根据锁定箭头和车辆位置更新世界锚点。

        如果已有锚点，就优先保持它，让箭头固定在原来的世界位置。
        如果没有锚点但出现新的锁定箭头，则创建一个新的世界锚点。
        """
        if self.anchor is not None:
            if self.args.world_anchor_expire_mode == "pass":
                if self.has_vehicle_passed_anchor(self.anchor, vehicle_transform):
                    self.clear()
                    self.last_status = "world anchor passed"
                    return None
                if locked_arrow is not None and locked_arrow.nav_mode == self.anchor.nav_mode:
                    self.anchor.expires_at = max(self.anchor.expires_at, locked_arrow.expires_at)
                    self.anchor.confidence = locked_arrow.confidence
                self.last_status = "holding world anchor until passed"
                return self.anchor

            if now <= self.anchor.expires_at:
                if locked_arrow is not None and locked_arrow.nav_mode == self.anchor.nav_mode:
                    # Keep the original geometry fixed in world coordinates, but
                    # let the tracker extend the display lifetime if it remains valid.
                    self.anchor.expires_at = max(self.anchor.expires_at, locked_arrow.expires_at)
                    self.anchor.confidence = locked_arrow.confidence
                self.last_status = "using fixed world anchor"
                return self.anchor

            self.clear()
            self.last_status = "world anchor expired"

        if locked_arrow is None:
            return None

        self.anchor = create_world_arrow_anchor(locked_arrow, vehicle_transform, now, self.args)
        if self.anchor is None:
            self.last_status = "world anchor create failed"
        else:
            self.last_status = "created fixed world anchor"
            print(
                "[WORLD-ANCHOR] nav={} start_world=({:.2f},{:.2f},{:.2f}) target_world=({:.2f},{:.2f},{:.2f})".format(
                    self.anchor.nav_mode,
                    self.anchor.start_world[0],
                    self.anchor.start_world[1],
                    self.anchor.start_world[2],
                    self.anchor.target_world[0],
                    self.anchor.target_world[1],
                    self.anchor.target_world[2],
                )
            )
        return self.anchor

def world_anchor_relative_text(anchor, vehicle_transform):
    """生成 HUD 文本，显示世界锚点相对当前车辆的位置。"""
    if anchor is None:
        return "World anchor: none"
    start_local = world_point_to_vehicle_local(anchor.start_world, vehicle_transform)
    target_local = world_point_to_vehicle_local(anchor.target_world, vehicle_transform)
    return (
        "World anchor rel: start x={:.1f}m y={:.1f}m | target x={:.1f}m y={:.1f}m".format(
            start_local[0],
            start_local[1],
            target_local[0],
            target_local[1],
        )
    )
