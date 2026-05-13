# -*- coding: utf-8 -*-
"""实时应用编排层。

这个文件应该像一张接线图：它负责把 pygame、CARLA、YOLOP、导航状态机、
世界锚点和 AR 绘制串起来。具体算法细节不放在这里，而是分散在相邻模块中。

阅读时可以抓住主循环的顺序：
    1. 处理退出、debug、导航意图按键。
    2. 读取驾驶按键并控制车辆。
    3. 收取后台 YOLOP 推理结果。
    4. 必要时提交下一次 YOLOP 推理。
    5. 在最新相机帧上绘制 debug、箭头和 HUD。
"""

import time
from concurrent.futures import ThreadPoolExecutor

from .runtime_deps import lane
from .settings import parse_args


def run():
    """启动实时 demo。

    注意：pygame、CARLA helper、UI 模块都在 parse_args() 之后延迟导入。
    这样 `python main.py --help` 不需要安装/加载所有实时依赖，也不会连接 CARLA。
    """
    args = parse_args()
    import pygame

    from . import ar_renderer
    from .carla_deps import (
        CAMERA_FOV,
        CameraSensor,
        build_camera_intrinsic_k,
        connect_to_carla,
        destroy_actors,
        draw_text_lines,
        get_keyboard_vehicle_control,
        make_pygame_surface,
        spawn_ego_vehicle,
    )
    from .geometry import fmt_point
    from .models import NAV_NONE
    from .navigation import NavigationArrowTracker
    from .runtime import set_world_async
    from .ui import draw_detection_status, set_nav_from_key
    from .world_anchor import WorldArrowAnchorTracker, world_anchor_relative_text
    from .yolop_pipeline import run_detection

    args.height = int(args.height)
    args.width = int(args.width)
    lane.ensure_runtime()

    # pygame 负责窗口、键盘事件和最终显示。CARLA 相机画面会先经过 OpenCV
    # 画箭头，再转换成 pygame surface。
    pygame.init()
    pygame.font.init()
    display = pygame.display.set_mode((args.width, args.height))
    pygame.display.set_caption("CARLA YOLOP world-anchor AR arrow | 1/2/3 | C clear | ESC quit")
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    # 相机内参 K 是所有投影/反投影函数的基础。宽高或 FOV 改变时，K 也要重建。
    camera_k = build_camera_intrinsic_k(args.width, args.height, CAMERA_FOV)
    client, world = connect_to_carla()
    original_settings = set_world_async(world)
    actors = []
    current_steer = 0.0

    # YOLOPAdapter 只创建一次。每次推理复用同一个 ONNX Runtime session。
    adapter = lane.YOLOPAdapter(
        args.yolop_onnx,
        input_width=args.yolop_width,
        input_height=args.yolop_height,
        threshold=args.yolop_threshold,
        normalize=args.normalize,
    )
    tracker = NavigationArrowTracker(args)
    world_anchor_tracker = WorldArrowAnchorTracker(args)
    # 只开一个后台推理线程：保证不会堆积多帧旧图像，也避免多个 ONNX 推理抢资源。
    executor = ThreadPoolExecutor(max_workers=1)
    pending_future = None
    next_detection_time = 0.0
    last_packet = None
    last_result = None
    show_debug = args.show_debug_geometry or args.show_debug_mask

    print("Realtime YOLOP world-anchored navigation hint demo")
    print("YOLOP:", args.yolop_onnx)
    print("Controls: 1 straight | 2 left | 3 right | C/0 clear | M debug | ESC quit")

    try:
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        # sensor_tick=0.0 表示 CARLA 每次相机 tick 都回调；如果传入 --camera-fps，
        # 就按指定频率产生相机帧。
        sensor_tick = "0.0"
        if args.camera_fps > 0:
            sensor_tick = str(1.0 / args.camera_fps)
        camera = CameraSensor(
            world,
            vehicle,
            "sensor.camera.rgb",
            width=args.width,
            height=args.height,
            fov=CAMERA_FOV,
            sensor_tick=sensor_tick,
        )
        actors.append(camera.actor)
        args.camera_k = camera_k
        args.camera_mount_transform = camera.transform

        running = True
        while running:
            # 这一行限制的是 pygame 显示循环，不等于 YOLOP 推理频率，也不等于 CARLA
            # 相机传感器频率。三个频率在实时系统里可以不同。
            clock.tick(max(1, args.display_fps))
            now = time.time()

            # 离散事件：按下 1/2/3/C/M/ESC 的那一刻才触发。
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_m:
                        show_debug = not show_debug
                        print("Debug overlay:", show_debug)
                    elif set_nav_from_key(event, tracker):
                        world_anchor_tracker.clear()

            # 持续按键：W/A/S/D 或方向键只要按住，就持续影响车辆控制。
            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            # 后台 YOLOP 线程完成后，在主线程更新导航状态机。pygame/OpenCV 绘制也留在主线程。
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

            # 到达检测时间、没有正在进行的推理、且用户已经选择导航意图时，才提交下一次 YOLOP。
            if (
                camera.latest_rgb is not None
                and pending_future is None
                and now >= next_detection_time
                and tracker.nav_mode != NAV_NONE
            ):
                frame_id = camera.latest_image.frame if camera.latest_image is not None else "-"
                rgb_for_detection = camera.latest_rgb.copy()
                pending_future = executor.submit(
                    run_detection,
                    adapter,
                    rgb_for_detection,
                    args,
                    frame_id,
                    tracker.nav_mode,
                )
                next_detection_time = now + max(0.2, args.detect_interval)

            # 绘制阶段：永远使用最新相机帧；如果 YOLOP 还没回来，就沿用上一帧结果或只显示 HUD。
            if camera.latest_rgb is not None:
                bgr = camera.latest_rgb[:, :, ::-1].copy()
                if show_debug:
                    bgr = ar_renderer.draw_debug_geometry(bgr, last_result, args)
                locked_arrow = tracker.active_arrow(now)
                world_anchor = None
                if args.arrow_projection == "world":
                    # world 模式：锁定箭头先转成世界锚点，再按当前相机位置重新投影。
                    world_anchor = world_anchor_tracker.update(locked_arrow, vehicle.get_transform(), now)
                    if world_anchor is not None:
                        camera_transform = camera.actor.get_transform()
                        drew_world = ar_renderer.draw_world_anchored_arrow(bgr, world_anchor, camera_transform, now, args)
                        if not drew_world and args.world_anchor_fallback_screen:
                            ar_renderer.draw_locked_arrow(bgr, locked_arrow, now, args)
                    elif args.world_anchor_fallback_screen:
                        ar_renderer.draw_locked_arrow(bgr, locked_arrow, now, args)
                else:
                    # ground/screen 模式不需要世界锚点，旧锚点要清掉，避免 HUD 状态误导。
                    world_anchor_tracker.clear()
                    ar_renderer.draw_locked_arrow(bgr, locked_arrow, now, args)
                draw_detection_status(bgr, last_packet, tracker, pending_future is not None)
                display.blit(make_pygame_surface(pygame, bgr[:, :, ::-1]), (0, 0))
            else:
                display.fill((10, 10, 10))

            active_world_anchor = world_anchor_tracker.anchor if args.arrow_projection == "world" else None
            hud = [
                "YOLOP world-anchor nav hint | 1 straight | 2 left | 3 right | C/0 clear | M debug | ESC quit",
                "Drive: W/A/S/D or arrows | targets are filtered to {:.0f}m ahead.".format(
                    args.max_target_forward_meters
                ),
                "YOLOP every {:.1f}s | lock after {} stable samples | hold {:.1f}s".format(
                    args.detect_interval,
                    args.stability_confirmations,
                    args.arrow_hold_seconds,
                ),
                "Arrow projection: {} | expire: {} | pass point: {}".format(
                    args.arrow_projection,
                    args.world_anchor_expire_mode,
                    args.world_anchor_pass_point,
                ),
                world_anchor_relative_text(active_world_anchor, vehicle.get_transform())
                if active_world_anchor is not None
                else "World anchor: {}".format(world_anchor_tracker.last_status),
                "Current nav: {} | active arrow: {} | debug: {}".format(
                    tracker.nav_mode.upper(),
                    tracker.active_arrow(now) is not None,
                    show_debug,
                ),
            ]
            draw_text_lines(pygame, display, font, hud, y=args.height - 148, line_height=22)
            pygame.display.flip()

    finally:
        # 退出清理很重要：取消后台任务、销毁 CARLA actor、恢复 world 设置、关闭 pygame。
        if pending_future is not None:
            pending_future.cancel()
        executor.shutdown(wait=False)
        destroy_actors(actors)
        world.apply_settings(original_settings)
        pygame.quit()
        print("Restored original world settings.")
        print("Cleaned up.")
