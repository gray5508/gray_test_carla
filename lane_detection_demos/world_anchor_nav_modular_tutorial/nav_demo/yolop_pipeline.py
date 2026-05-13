# -*- coding: utf-8 -*-
"""YOLOP 推理流水线。

实时 app 会把 `run_detection()` 提交到后台线程。这样 ONNX Runtime 推理时，
pygame 主循环仍然可以继续响应键盘和刷新画面。

本模块不关心 CARLA 车辆如何驾驶，也不直接画箭头；它只负责把最新 RGB 图像
变成 `DetectionPacket`。
"""

import time

from .runtime_deps import estimate_current_lane, lane
from .models import DetectionPacket, EmptyResult
from .navigation import make_nav_candidate

def make_turn_args(args):
    """把主程序参数裁剪成 `estimate_current_lane()` 需要的参数对象。"""
    class TurnArgs(object):
        pass

    turn_args = TurnArgs()
    turn_args.roi_top_ratio = args.roi_top_ratio
    turn_args.scan_top_ratio = args.scan_top_ratio
    turn_args.scan_bottom_ratio = args.scan_bottom_ratio
    turn_args.scan_rows = args.scan_rows
    turn_args.scan_band = args.scan_band
    turn_args.min_segment_width = args.min_segment_width
    turn_args.max_segment_width_ratio = args.max_segment_width_ratio
    turn_args.vehicle_x_ratio = args.vehicle_x_ratio
    turn_args.initial_half_lane_width_ratio = args.initial_half_lane_width_ratio
    turn_args.max_jump_ratio = args.max_jump_ratio
    turn_args.smooth_samples = args.smooth_samples
    turn_args.arrow_start_y_ratio = args.arrow_start_y_ratio
    turn_args.turn_shift_ratio = args.turn_shift_ratio
    turn_args.target_average_points = args.target_average_points
    turn_args.min_center_points = args.min_center_points
    turn_args.min_confidence = args.min_confidence
    turn_args.draw_raw_mask = False
    return turn_args

def predict_yolop_mask(adapter, bgr):
    """调用 YOLOPAdapter，返回布尔 lane mask 和调试文本。"""
    obs = adapter.predict(bgr)
    if obs.lane_mask is None:
        return None, obs.debug_lines or []
    return obs.lane_mask.astype(bool), obs.debug_lines or []

def run_detection(adapter, rgb, args, frame_id, nav_mode):
    """后台线程执行的一次完整检测。

    输入是 RGB 相机帧，内部转成 BGR 给 YOLOPAdapter。函数会捕获异常并把错误
    写入 DetectionPacket，避免后台线程异常直接打断 pygame 主循环。
    """
    started = time.time()
    try:
        bgr = rgb[:, :, ::-1].copy()
        mask, model_debug = predict_yolop_mask(adapter, bgr)
        if mask is None:
            result = EmptyResult(["YOLOP lane mask missing"] + model_debug[:2])
            candidate = None
        else:
            result = estimate_current_lane(mask, make_turn_args(args))
            candidate = make_nav_candidate(result, nav_mode, args, rgb.shape[1], rgb.shape[0], time.time())
        inference_ms = (time.time() - started) * 1000.0
        return DetectionPacket(result, candidate, inference_ms, frame_id, nav_mode)
    except Exception as exc:
        inference_ms = (time.time() - started) * 1000.0
        return DetectionPacket(None, None, inference_ms, frame_id, nav_mode, "{}: {}".format(type(exc).__name__, exc))
