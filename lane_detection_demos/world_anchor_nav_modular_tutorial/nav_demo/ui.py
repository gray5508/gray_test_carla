# -*- coding: utf-8 -*-
"""pygame 键盘导航意图和 HUD 文本绘制。"""

import pygame

from .geometry import fmt_point
from .models import NAV_LEFT, NAV_RIGHT, NAV_STRAIGHT
from .runtime_deps import lane

def draw_detection_status(bgr, packet, tracker, detecting):
    """在 OpenCV 图像左上角绘制 YOLOP 和导航状态。"""
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

def set_nav_from_key(event, tracker):
    """把数字键映射成导航意图。

    这里故意只处理“导航相关按键”。车辆驾驶按键 W/A/S/D 在 app.py 中通过
    `get_keyboard_vehicle_control()` 单独处理。
    """
    if event.key == pygame.K_1:
        tracker.set_nav_mode(NAV_STRAIGHT)
        print("Navigation intent: STRAIGHT")
        return True
    if event.key == pygame.K_2:
        tracker.set_nav_mode(NAV_LEFT)
        print("Navigation intent: LEFT")
        return True
    if event.key == pygame.K_3:
        tracker.set_nav_mode(NAV_RIGHT)
        print("Navigation intent: RIGHT")
        return True
    if event.key in (pygame.K_c, pygame.K_0):
        tracker.clear()
        print("Navigation intent cleared.")
        return True
    return False
