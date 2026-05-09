import time

from .lane_interpreter import LaneInterpreter, make_turn_args
from .models import DetectionPacket, EmptyResult
from .paths import ensure_runtime, lane

from offline_yolop_turn_experiment import estimate_current_lane  # noqa: E402


class YolopLaneDetector(object):
    """Small wrapper around the existing YOLOPAdapter.

    Responsibilities:
      1. Run YOLOP and get a lane mask.
      2. Convert the mask into current-lane geometry.
      3. Optionally turn that geometry into a nav candidate.
    """

    def __init__(self, config):
        ensure_runtime()
        self.config = config
        self.adapter = lane.YOLOPAdapter(
            config.yolop_onnx,
            input_width=config.yolop_width,
            input_height=config.yolop_height,
            threshold=config.yolop_threshold,
            normalize=config.normalize,
        )
        self.interpreter = LaneInterpreter(config)

    def predict_mask(self, bgr):
        obs = self.adapter.predict(bgr)
        if obs.lane_mask is None:
            return None, obs.debug_lines or []
        return obs.lane_mask.astype(bool), obs.debug_lines or []

    def analyze_bgr(self, bgr):
        started = time.time()
        mask, model_debug = self.predict_mask(bgr)
        if mask is None:
            result = EmptyResult(["YOLOP lane mask missing"] + model_debug[:2])
        else:
            result = estimate_current_lane(mask, make_turn_args(self.config))
        inference_ms = (time.time() - started) * 1000.0
        return result, model_debug, inference_ms

    def detect_rgb(self, rgb, frame_id, nav_mode):
        started = time.time()
        try:
            bgr = rgb[:, :, ::-1].copy()
            result, model_debug, inference_ms = self.analyze_bgr(bgr)
            candidate = self.interpreter.make_candidate(
                result,
                nav_mode,
                self.config.width,
                self.config.height,
                time.time(),
            )
            return DetectionPacket(result, candidate, inference_ms, frame_id, nav_mode)
        except Exception as exc:
            inference_ms = (time.time() - started) * 1000.0
            return DetectionPacket(
                None,
                None,
                inference_ms,
                frame_id,
                nav_mode,
                "{}: {}".format(type(exc).__name__, exc),
            )
