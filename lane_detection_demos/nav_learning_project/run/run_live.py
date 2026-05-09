from pathlib import Path
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pygame


SUBPROJECT_DIR = Path(__file__).resolve().parents[1]
if str(SUBPROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(SUBPROJECT_DIR))

from nav_learning.arrow_renderer import ArrowRenderer  # noqa: E402
from nav_learning.carla_session import CarlaCameraSession  # noqa: E402
from nav_learning.geometry import fmt_point  # noqa: E402
from nav_learning.models import NAV_NONE  # noqa: E402
from nav_learning.paths import ensure_runtime  # noqa: E402
from nav_learning.pygame_view import PygameWindow, set_nav_from_key  # noqa: E402
from nav_learning.settings import build_parser, config_from_args  # noqa: E402
from nav_learning.tracker import NavigationArrowTracker  # noqa: E402
from nav_learning.yolop_detector import YolopLaneDetector  # noqa: E402


def main():
    parser = build_parser("Realtime CARLA + YOLOP modular learning runner.")
    args = parser.parse_args()
    config = config_from_args(args)
    ensure_runtime()

    window = PygameWindow(config.width, config.height, "modular YOLOP nav hint | 1/2/3 | C clear | ESC quit")
    detector = YolopLaneDetector(config)
    renderer = ArrowRenderer(config)
    tracker = NavigationArrowTracker(config)
    executor = ThreadPoolExecutor(max_workers=1)

    pending_future = None
    next_detection_time = 0.0
    last_packet = None
    last_result = None
    current_steer = 0.0
    show_debug = config.show_debug_geometry or config.show_debug_mask

    print("Modular realtime YOLOP navigation hint demo")
    print("YOLOP:", config.yolop_onnx)
    print("Controls: 1 straight | 2 left | 3 right | C/0 clear | M debug | ESC quit")

    try:
        with CarlaCameraSession(config) as carla_session:
            running = True
            while running:
                window.tick(config.display_fps)
                now = time.time()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_m:
                            show_debug = not show_debug
                            print("Debug overlay:", show_debug)
                        else:
                            set_nav_from_key(event, tracker)

                keys = pygame.key.get_pressed()
                current_steer = carla_session.apply_keyboard_control(pygame, keys, current_steer)

                if pending_future is not None and pending_future.done():
                    last_packet = pending_future.result()
                    pending_future = None
                    if last_packet.error:
                        print("[YOLOP] error:", last_packet.error)
                    else:
                        last_result = last_packet.result
                        tracker.push(last_packet.candidate, now)
                        if last_packet.candidate is not None:
                            print(
                                "[YOLOP] frame={} {:.0f}ms nav={} target={} conf={:.2f} status={}".format(
                                    last_packet.frame_id,
                                    last_packet.inference_ms,
                                    last_packet.candidate.nav_mode,
                                    fmt_point(last_packet.candidate.target),
                                    last_packet.candidate.confidence,
                                    tracker.last_status,
                                )
                            )
                        else:
                            print(
                                "[YOLOP] frame={} {:.0f}ms nav={} no candidate status={}".format(
                                    last_packet.frame_id,
                                    last_packet.inference_ms,
                                    last_packet.nav_mode,
                                    tracker.last_status,
                                )
                            )

                camera = carla_session.camera
                if (
                    camera.latest_rgb is not None
                    and pending_future is None
                    and now >= next_detection_time
                    and tracker.nav_mode != NAV_NONE
                ):
                    frame_id = camera.latest_image.frame if camera.latest_image is not None else "-"
                    rgb_for_detection = camera.latest_rgb.copy()
                    pending_future = executor.submit(
                        detector.detect_rgb,
                        rgb_for_detection,
                        frame_id,
                        tracker.nav_mode,
                    )
                    next_detection_time = now + max(0.2, config.detect_interval)

                if camera.latest_rgb is not None:
                    bgr = camera.latest_rgb[:, :, ::-1].copy()
                    if show_debug:
                        renderer.draw_lane_debug(
                            bgr,
                            last_result,
                            show_geometry=config.show_debug_geometry or show_debug,
                            show_mask=config.show_debug_mask,
                        )
                    renderer.draw_locked_arrow(bgr, tracker.active_arrow(now), now)
                    renderer.draw_detection_status(bgr, last_packet, tracker, pending_future is not None)
                    window.blit_bgr(bgr)
                else:
                    window.fill((10, 10, 10))

                window.draw_text_lines(
                    [
                        "Modular YOLOP nav hint | 1 straight | 2 left | 3 right | C/0 clear | M debug | ESC quit",
                        "Drive: W/A/S/D or arrows | targets filtered to {:.0f}m ahead.".format(config.max_target_forward_meters),
                        "YOLOP every {:.1f}s | lock after {} stable samples | hold {:.1f}s".format(
                            config.detect_interval,
                            config.stability_confirmations,
                            config.arrow_hold_seconds,
                        ),
                        "Current nav: {} | active arrow: {} | debug: {}".format(
                            tracker.nav_mode.upper(),
                            tracker.active_arrow(now) is not None,
                            show_debug,
                        ),
                    ],
                    y=config.height - 104,
                    line_height=22,
                )
                window.flip()

    finally:
        if pending_future is not None:
            pending_future.cancel()
        executor.shutdown(wait=False)
        window.close()


if __name__ == "__main__":
    main()

