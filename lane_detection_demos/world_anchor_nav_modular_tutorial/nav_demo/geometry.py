# -*- coding: utf-8 -*-
"""坐标转换与车道几何判断。

这个文件是整份教程最值得慢读的模块之一。它解决两类问题：

    1. 坐标转换：
       图像像素 <-> 车辆局部地面坐标 <-> CARLA 世界坐标。

    2. 车道几何：
       YOLOP 只给出车道 mask/中心线，本模块负责判断这些点是否支持
       straight/left/right 这类导航意图。

学习建议：
    先看 `pixel_to_vehicle_ground()` 和 `project_world_point_to_pixel()`，
    再看 `choose_straight_target()`、`choose_turn_target()`。前者是数学基础，
    后者是“把数学用于导航”的部分。
"""

from .runtime_deps import lane
from .models import NAV_LEFT, NAV_NONE, NAV_RIGHT, NAV_STRAIGHT

def fmt_point(point):
    if not point:
        return "-"
    return "({}, {})".format(int(point[0]), int(point[1]))

def point_distance(a, b):
    """计算两个像素点之间的欧氏距离，用于判断候选目标是否稳定。"""
    dx = float(a[0] - b[0])
    dy = float(a[1] - b[1])
    return (dx * dx + dy * dy) ** 0.5

def mean_point(points):
    """求一组像素点的平均值，导航状态机会用它平滑多个候选箭头。"""
    if not points:
        return None
    x = sum(point[0] for point in points) / float(len(points))
    y = sum(point[1] for point in points) / float(len(points))
    return int(x), int(y)

def blend_points(old, new, alpha):
    """指数平滑两个点，alpha 越大，新点影响越明显。"""
    return (
        int(round((1.0 - alpha) * old[0] + alpha * new[0])),
        int(round((1.0 - alpha) * old[1] + alpha * new[1])),
    )

def closest_point_by_y(points, target_y):
    if not points:
        return None
    return min(points, key=lambda point: abs(point[1] - target_y))

def pixel_to_vehicle_ground(point, args):
    """把图像像素反投影到车辆局部地面坐标。

    输入的 `point` 是图像像素 `(u, v)`。函数会：

    1. 用相机内参 K 把像素变成 OpenCV 相机坐标中的射线。
    2. 把 OpenCV 相机坐标转换成 CARLA/Unreal 相机坐标。
    3. 用相机安装姿态把射线转到车辆局部坐标。
    4. 让射线与地面平面 `z = vehicle_ground_z` 求交。

    返回 `(forward_m, right_m)`，也就是车辆前方多少米、右侧多少米。
    如果射线朝向不合理或无法与地面相交，返回 None。
    """
    k = getattr(args, "camera_k", None)
    camera_mount = getattr(args, "camera_mount_transform", None)
    if k is None or camera_mount is None:
        return None

    u, v = point
    fx = k[0, 0]
    fy = k[1, 1]
    cx = k[0, 2]
    cy = k[1, 2]

    ray_cv = lane.np.array([(u - cx) / fx, (v - cy) / fy, 1.0], dtype=float)
    # OpenCV 相机坐标：x 向右，y 向下，z 向前。
    # CARLA/UE 相机坐标：x 向前，y 向右，z 向上。
    # 这里做的是坐标轴重排，不是旋转矩阵学习题里的“随便换个名字”。
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

    ground_z = getattr(args, "vehicle_ground_z", 0.0)
    scale = (ground_z - origin[2]) / direction[2]
    if scale <= 0.0:
        return None

    hit = origin + scale * direction
    return float(hit[0]), float(hit[1])

def vehicle_ground_to_pixel(forward_m, right_m, args, width, height):
    """把车辆局部地面点投影到图像像素。

    这个函数用于“我知道箭头应该在车前方 N 米，现在想知道它画在屏幕哪里”。
    如果投影点在相机后方或超出画面，返回 None。
    """
    k = getattr(args, "camera_k", None)
    camera_mount = getattr(args, "camera_mount_transform", None)
    if k is None or camera_mount is None:
        return None

    vehicle_to_camera = lane.np.array(camera_mount.get_inverse_matrix())
    ground_z = getattr(args, "vehicle_ground_z", 0.0)
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

def project_vehicle_ground_to_pixel(forward_m, right_m, args):
    """投影车辆局部地面点，但不要求点落在屏幕范围内。

    绘制大箭头时，某些顶点可能略微超出屏幕。我们仍然希望得到投影结果，
    再通过 `clamp_projected_pixel()` 限制到一个合理范围，避免 OpenCV 绘制
    极端坐标时出现问题。
    """
    k = getattr(args, "camera_k", None)
    camera_mount = getattr(args, "camera_mount_transform", None)
    if k is None or camera_mount is None:
        return None

    vehicle_to_camera = lane.np.array(camera_mount.get_inverse_matrix())
    ground_z = getattr(args, "vehicle_ground_z", 0.0)
    point_vehicle = lane.np.array([forward_m, right_m, ground_z, 1.0], dtype=float)
    point_ue = lane.np.dot(vehicle_to_camera, point_vehicle)
    point_cv = lane.np.array([point_ue[1], -point_ue[2], point_ue[0]], dtype=float)
    if point_cv[2] <= 0.05:
        return None

    projected = lane.np.dot(k, point_cv)
    u = projected[0] / projected[2]
    v = projected[1] / projected[2]
    if not lane.np.isfinite(u) or not lane.np.isfinite(v):
        return None
    return float(u), float(v)

def clamp_projected_pixel(point, width, height, margin=4000):
    """把投影点限制在屏幕附近，避免特别大的坐标影响绘制。"""
    x, y = point
    x = max(-margin, min(width + margin, float(x)))
    y = max(-margin, min(height + margin, float(y)))
    return int(round(x)), int(round(y))

def project_ground_polygon(points, args, width, height):
    """把车辆局部地面多边形投影成图像多边形。"""
    projected = []
    for forward_m, right_m in points:
        pixel = project_vehicle_ground_to_pixel(forward_m, right_m, args)
        if pixel is None:
            return None
        projected.append(clamp_projected_pixel(pixel, width, height))
    return lane.np.asarray(projected, dtype=lane.np.int32)

def vehicle_ground_to_world_point(forward_m, right_m, vehicle_to_world, args):
    """把车辆局部地面点变成 CARLA 世界坐标点。"""
    ground_z = getattr(args, "vehicle_ground_z", 0.0)
    point_vehicle = lane.np.asarray([forward_m, right_m, ground_z, 1.0], dtype=float)
    point_world = lane.np.dot(vehicle_to_world, point_vehicle)
    return lane.np.asarray(point_world[:3], dtype=lane.np.float32)

def world_point_to_vehicle_local(point_world, vehicle_transform):
    """把 CARLA 世界点转换到当前车辆局部坐标。

    世界锚点是否已经被车辆开过，就是靠这个函数判断的：如果某个世界点
    转到当前车辆坐标后 `x` 已经小于阈值，说明它落到车辆后方了。
    """
    world_to_vehicle = lane.np.asarray(vehicle_transform.get_inverse_matrix(), dtype=float)
    point = lane.np.asarray([point_world[0], point_world[1], point_world[2], 1.0], dtype=float)
    local = lane.np.dot(world_to_vehicle, point)
    return lane.np.asarray(local[:3], dtype=lane.np.float32)

def project_world_point_to_pixel(point_world, camera_transform, args):
    """把 CARLA 世界点投影到当前相机画面。

    世界锚点箭头每一帧都要调用这个逻辑。箭头本身的世界坐标不动，
    但相机 transform 随车移动，所以投影出来的屏幕位置会变化。
    """
    k = getattr(args, "camera_k", None)
    if k is None or camera_transform is None:
        return None

    world_to_camera = lane.np.asarray(camera_transform.get_inverse_matrix(), dtype=float)
    point_h = lane.np.asarray([point_world[0], point_world[1], point_world[2], 1.0], dtype=float)
    point_ue = lane.np.dot(world_to_camera, point_h)
    point_cv = lane.np.asarray([point_ue[1], -point_ue[2], point_ue[0]], dtype=float)
    if point_cv[2] <= 0.05:
        return None

    projected = lane.np.dot(k, point_cv)
    u = projected[0] / projected[2]
    v = projected[1] / projected[2]
    if not lane.np.isfinite(u) or not lane.np.isfinite(v):
        return None
    return float(u), float(v), float(point_cv[2])

def project_world_polygon(points_world, camera_transform, args, width, height):
    projected = []
    for point_world in points_world:
        pixel = project_world_point_to_pixel(point_world, camera_transform, args)
        if pixel is None:
            return None
        projected.append(clamp_projected_pixel((pixel[0], pixel[1]), width, height))
    return lane.np.asarray(projected, dtype=lane.np.int32)

def arrow_start_pixel(width, height, args):
    """为转弯箭头选择屏幕起点。优先使用米制地面起点，失败时回退到比例。"""
    metric_start = vehicle_ground_to_pixel(args.arrow_start_meters, 0.0, args, width, height)
    if metric_start is not None:
        return metric_start
    return (
        int(width * args.vehicle_x_ratio),
        int(height * args.arrow_start_y_ratio),
    )

def straight_right_meters(args):
    """直行箭头的左右偏移。默认沿驾驶员相机方向，而不是车辆几何中心线。"""
    if args.straight_right_meters is not None:
        return float(args.straight_right_meters)

    camera_mount = getattr(args, "camera_mount_transform", None)
    if camera_mount is not None:
        return float(camera_mount.location.y)
    return 0.0

def straight_arrow_start_pixel(width, height, args):
    """为直行箭头选择屏幕起点。直行更强调“沿当前车道往前”。"""
    metric_start = vehicle_ground_to_pixel(
        args.arrow_start_meters,
        straight_right_meters(args),
        args,
        width,
        height,
    )
    if metric_start is not None:
        return metric_start
    return arrow_start_pixel(width, height, args)

def points_with_forward_distance(points, args):
    """给每个像素点补充前向距离，用于筛选合理目标点。"""
    measured = []
    for point in points or []:
        hit = pixel_to_vehicle_ground(point, args)
        if hit is None:
            continue
        forward_m, right_m = hit
        measured.append((forward_m, right_m, point))
    return measured

def valid_target_points(points, args):
    """只保留距离车辆前方一定范围内的候选点。"""
    min_forward = args.turn_target_min_forward_meters
    max_forward = args.max_target_forward_meters
    measured = points_with_forward_distance(points, args)
    return [
        item
        for item in measured
        if min_forward <= item[0] <= max_forward
    ]

def classify_geometry(points, start, width, height, args):
    """粗略判断中心线相对起点是直行、左偏还是右偏。"""
    if not points or start is None:
        return "unknown", 0.0, None

    candidates = valid_target_points(points, args)
    if candidates:
        _, _, target = max(candidates, key=lambda item: item[0])
    else:
        target = closest_point_by_y(points, height * args.turn_target_y_ratio)
        if target is None:
            target = points[-1]

    dx = float(target[0] - start[0])
    shift = abs(dx) / float(max(1, width))
    if shift < args.turn_shift_ratio:
        return NAV_STRAIGHT, shift, target
    if dx < 0:
        return NAV_LEFT, shift, target
    return NAV_RIGHT, shift, target

def choose_straight_target(points, start, width, height, args):
    """选择直行箭头目标点。

    直行导航不直接使用 YOLOP 中心线最远点，因为轻微弯道或检测抖动会让箭头
    看起来左右晃。这里先定义一个稳定的车辆前向目标，再用
    `straight_line_inside_current_lane()` 检查这条线是否仍在当前车道内。
    """
    target = vehicle_ground_to_pixel(
        args.straight_target_forward_meters,
        straight_right_meters(args),
        args,
        width,
        height,
    )
    if target is None:
        return None
    return target

def interpolate_x_at_y(points, y):
    """在一条按像素 y 排布的折线上，估计指定 y 位置的 x。"""
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

def straight_line_inside_current_lane(result, start, target, width, args):
    """验证直行箭头线段是否落在当前车道内部。"""
    if result is None:
        return False

    center_points = result.smooth_center or result.center_points or []
    if len(center_points) < args.min_center_points:
        return False

    sample_count = max(3, int(args.straight_validation_samples))
    sample_ratios = lane.np.linspace(0.0, 1.0, sample_count)
    accepted = 0
    checked = 0

    for ratio in sample_ratios:
        x, y = point_on_line(start, target, ratio)
        left_x = interpolate_x_at_y(result.left_points, y)
        right_x = interpolate_x_at_y(result.right_points, y)

        if left_x is not None and right_x is not None and abs(right_x - left_x) >= args.min_lane_width_px:
            low = min(left_x, right_x) + args.straight_boundary_margin_px
            high = max(left_x, right_x) - args.straight_boundary_margin_px
            if low > high:
                low, high = min(left_x, right_x), max(left_x, right_x)
            checked += 1
            if low <= x <= high:
                accepted += 1
            continue

        center_x = interpolate_x_at_y(center_points, y)
        if center_x is not None:
            checked += 1
            if abs(x - center_x) <= width * args.straight_center_tolerance_ratio:
                accepted += 1

    if checked < args.min_straight_validation_checks:
        return False
    return accepted / float(checked) >= args.straight_validation_ratio

def choose_turn_target(points, start, width, height, nav_mode, args):
    """根据导航意图选择左转或右转目标点。

    目标点必须满足两个条件：
        1. 在车辆前方合理距离范围内。
        2. 相对起点有足够横向偏移，并且方向与 nav_mode 一致。
    """
    if not points:
        return None, "unknown", 0.0

    candidates = []
    for forward_m, right_m, point in valid_target_points(points, args):
        dx = float(point[0] - start[0])
        shift = abs(dx) / float(max(1, width))
        if nav_mode == NAV_LEFT and dx < 0 and shift >= args.turn_min_shift_ratio:
            candidates.append((forward_m, shift, point))
        elif nav_mode == NAV_RIGHT and dx > 0 and shift >= args.turn_min_shift_ratio:
            candidates.append((forward_m, shift, point))

    if candidates:
        forward_m, shift, target = max(candidates, key=lambda item: item[0])
        return target, nav_mode, shift

    direction, shift, target = classify_geometry(points, start, width, height, args)
    if direction != nav_mode:
        return None, direction, shift
    if shift < args.turn_min_shift_ratio:
        return None, direction, shift
    return target, direction, shift
