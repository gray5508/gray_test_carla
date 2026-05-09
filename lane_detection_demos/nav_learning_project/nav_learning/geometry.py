from .models import NAV_LEFT, NAV_RIGHT, NAV_STRAIGHT
from .paths import lane


def fmt_point(point):
    if not point:
        return "-"
    return "({}, {})".format(int(point[0]), int(point[1]))


def point_distance(a, b):
    dx = float(a[0] - b[0])
    dy = float(a[1] - b[1])
    return (dx * dx + dy * dy) ** 0.5


def mean_point(points):
    if not points:
        return None
    x = sum(point[0] for point in points) / float(len(points))
    y = sum(point[1] for point in points) / float(len(points))
    return int(x), int(y)


def blend_points(old, new, alpha):
    return (
        int(round((1.0 - alpha) * old[0] + alpha * new[0])),
        int(round((1.0 - alpha) * old[1] + alpha * new[1])),
    )


def closest_point_by_y(points, target_y):
    if not points:
        return None
    return min(points, key=lambda point: abs(point[1] - target_y))


def pixel_to_vehicle_ground(point, config):
    k = getattr(config, "camera_k", None)
    camera_mount = getattr(config, "camera_mount_transform", None)
    if k is None or camera_mount is None:
        return None

    u, v = point
    fx = k[0, 0]
    fy = k[1, 1]
    cx = k[0, 2]
    cy = k[1, 2]

    ray_cv = lane.np.array([(u - cx) / fx, (v - cy) / fy, 1.0], dtype=float)
    # OpenCV camera: x right, y down, z forward.
    # CARLA/UE camera: x forward, y right, z up.
    ray_ue = lane.np.array([ray_cv[2], ray_cv[0], -ray_cv[1]], dtype=float)

    camera_to_vehicle = lane.np.array(camera_mount.get_matrix())
    origin = lane.np.dot(camera_to_vehicle, lane.np.array([0.0, 0.0, 0.0, 1.0], dtype=float))
    ray_point = lane.np.dot(
        camera_to_vehicle,
        lane.np.array([ray_ue[0], ray_ue[1], ray_ue[2], 1.0], dtype=float),
    )
    direction = ray_point - origin
    if abs(direction[2]) < 1e-8:
        return None

    ground_z = getattr(config, "vehicle_ground_z", 0.0)
    scale = (ground_z - origin[2]) / direction[2]
    if scale <= 0.0:
        return None

    hit = origin + scale * direction
    return float(hit[0]), float(hit[1])


def vehicle_ground_to_pixel(forward_m, right_m, config, width, height):
    k = getattr(config, "camera_k", None)
    camera_mount = getattr(config, "camera_mount_transform", None)
    if k is None or camera_mount is None:
        return None

    vehicle_to_camera = lane.np.array(camera_mount.get_inverse_matrix())
    ground_z = getattr(config, "vehicle_ground_z", 0.0)
    point_vehicle = lane.np.array([forward_m, right_m, ground_z, 1.0], dtype=float)
    point_ue = lane.np.dot(vehicle_to_camera, point_vehicle)
    point_cv = lane.np.array([point_ue[1], -point_ue[2], point_ue[0]], dtype=float)
    if point_cv[2] <= 0.05:
        return None

    projected = lane.np.dot(k, point_cv)
    u = projected[0] / projected[2]
    v = projected[1] / projected[2]
    if u < 0 or u >= width or v < 0 or v >= height:
        return None
    return int(u), int(v)


def arrow_start_pixel(width, height, config):
    metric_start = vehicle_ground_to_pixel(config.arrow_start_meters, 0.0, config, width, height)
    if metric_start is not None:
        return metric_start
    return (
        int(width * config.vehicle_x_ratio),
        int(height * config.arrow_start_y_ratio),
    )


def straight_right_meters(config):
    if config.straight_right_meters is not None:
        return float(config.straight_right_meters)

    camera_mount = getattr(config, "camera_mount_transform", None)
    if camera_mount is not None:
        return float(camera_mount.location.y)
    return 0.0


def straight_arrow_start_pixel(width, height, config):
    metric_start = vehicle_ground_to_pixel(
        config.arrow_start_meters,
        straight_right_meters(config),
        config,
        width,
        height,
    )
    if metric_start is not None:
        return metric_start
    return arrow_start_pixel(width, height, config)


def points_with_forward_distance(points, config):
    measured = []
    for point in points or []:
        hit = pixel_to_vehicle_ground(point, config)
        if hit is None:
            continue
        forward_m, right_m = hit
        measured.append((forward_m, right_m, point))
    return measured


def valid_target_points(points, config):
    min_forward = config.arrow_start_meters + config.min_arrow_length_meters
    max_forward = config.max_target_forward_meters
    measured = points_with_forward_distance(points, config)
    return [
        item
        for item in measured
        if min_forward <= item[0] <= max_forward
    ]


def classify_geometry(points, start, width, height, config):
    if not points or start is None:
        return "unknown", 0.0, None

    candidates = valid_target_points(points, config)
    if candidates:
        _, _, target = max(candidates, key=lambda item: item[0])
    else:
        target = closest_point_by_y(points, height * config.turn_target_y_ratio)
        if target is None:
            target = points[-1]

    dx = float(target[0] - start[0])
    shift = abs(dx) / float(max(1, width))
    if shift < config.turn_shift_ratio:
        return NAV_STRAIGHT, shift, target
    if dx < 0:
        return NAV_LEFT, shift, target
    return NAV_RIGHT, shift, target


def choose_straight_target(points, start, width, height, config):
    return vehicle_ground_to_pixel(
        config.straight_target_forward_meters,
        straight_right_meters(config),
        config,
        width,
        height,
    )


def interpolate_x_at_y(points, y):
    if not points:
        return None

    ordered = sorted(points, key=lambda point: point[1])
    if y < ordered[0][1] or y > ordered[-1][1]:
        return None

    for idx in range(len(ordered) - 1):
        x0, y0 = ordered[idx]
        x1, y1 = ordered[idx + 1]
        if y0 == y1:
            continue
        if y0 <= y <= y1 or y1 <= y <= y0:
            ratio = (float(y) - y0) / float(y1 - y0)
            return float(x0) + ratio * float(x1 - x0)
    return None


def point_on_line(start, target, ratio):
    x = float(start[0]) + ratio * float(target[0] - start[0])
    y = float(start[1]) + ratio * float(target[1] - start[1])
    return x, y


def straight_line_inside_current_lane(result, start, target, width, config):
    if result is None:
        return False

    center_points = result.smooth_center or result.center_points or []
    if len(center_points) < config.min_center_points:
        return False

    sample_count = max(3, int(config.straight_validation_samples))
    sample_ratios = lane.np.linspace(0.0, 1.0, sample_count)
    accepted = 0
    checked = 0

    for ratio in sample_ratios:
        x, y = point_on_line(start, target, ratio)
        left_x = interpolate_x_at_y(result.left_points, y)
        right_x = interpolate_x_at_y(result.right_points, y)

        if left_x is not None and right_x is not None and abs(right_x - left_x) >= config.min_lane_width_px:
            low = min(left_x, right_x) + config.straight_boundary_margin_px
            high = max(left_x, right_x) - config.straight_boundary_margin_px
            if low > high:
                low, high = min(left_x, right_x), max(left_x, right_x)
            checked += 1
            if low <= x <= high:
                accepted += 1
            continue

        center_x = interpolate_x_at_y(center_points, y)
        if center_x is not None:
            checked += 1
            if abs(x - center_x) <= width * config.straight_center_tolerance_ratio:
                accepted += 1

    if checked < config.min_straight_validation_checks:
        return False
    return accepted / float(checked) >= config.straight_validation_ratio


def choose_turn_target(points, start, width, height, nav_mode, config):
    if not points:
        return None, "unknown", 0.0

    candidates = []
    for forward_m, right_m, point in valid_target_points(points, config):
        dx = float(point[0] - start[0])
        shift = abs(dx) / float(max(1, width))
        if nav_mode == NAV_LEFT and dx < 0 and shift >= config.turn_min_shift_ratio:
            candidates.append((forward_m, shift, point))
        elif nav_mode == NAV_RIGHT and dx > 0 and shift >= config.turn_min_shift_ratio:
            candidates.append((forward_m, shift, point))

    if candidates:
        forward_m, shift, target = max(candidates, key=lambda item: item[0])
        return target, nav_mode, shift

    direction, shift, target = classify_geometry(points, start, width, height, config)
    if direction != nav_mode:
        return None, direction, shift
    if shift < config.turn_min_shift_ratio:
        return None, direction, shift
    return target, direction, shift

