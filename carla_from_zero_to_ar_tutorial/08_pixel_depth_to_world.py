"""
08_pixel_depth_to_world.py

本节目标：
  1. 鼠标点击 RGB 图像得到 pixel；
  2. 从 Depth 图读取同一 pixel 的 depth；
  3. pixel + depth -> camera coordinate（相机坐标系）；
  4. camera coordinate -> world coordinate（世界坐标系）；
  5. debug draw 反算出的世界点。

这条链适合"我有深度图"的情况。

核心知识点：
  - 像素坐标 (u, v) + 深度值 depth -> 相机坐标系下的 3D 点
  - 相机坐标系 -> 世界坐标系需要用到相机的外参（位置和姿态）
  - 这是完整的"像素到世界"的反投影链路
  
应用场景：
  - 当你有 RGB-D 相机（同时输出彩色图和深度图）时
  - 可以从图像中检测物体，并通过深度信息还原其真实世界位置
  - 适用于障碍物检测、距离测量等任务
"""

import pygame

from common import CAMERA_FOV
from common import CameraSensor
from common import build_camera_intrinsic_k
from common import connect_to_carla
from common import camera_cv_to_camera_ue
from common import debug_draw_point
from common import destroy_actors
from common import draw_text_lines
from common import get_keyboard_vehicle_control
from common import make_pygame_surface
from common import pixel_depth_to_camera_cv
from common import pixel_depth_to_world
from common import spawn_ego_vehicle


# Lesson 08 使用一个比 1920x1080 小的普通窗口。
# 如果窗口刚好顶满屏幕，Windows 上标题栏可能会跑到屏幕外，看起来像“全屏”，不方便拖动。
# RGB/Depth 相机也使用同样尺寸，这样点击像素、深度图索引和相机内参 K 仍然一一对应。
PYGAME_WINDOW_WIDTH = 1280
PYGAME_WINDOW_HEIGHT = 720


def fmt3(value):
    """把数字格式化成 3 位小数，方便 HUD 和日志阅读。"""
    return "{:.3f}".format(float(value))


def frame_of(image):
    """返回 CARLA sensor image 的 frame；如果还没收到图像，返回 '-'。"""
    return image.frame if image is not None else "-"


def print_click_debug_flow(
    u,
    v,
    depth,
    k,
    point_cv,
    point_ue,
    clicked_world,
    camera_transform,
    rgb_image,
    depth_image,
):
    """
    每次鼠标点击后，在控制台打印一整套 pixel + depth -> world 的计算流程。

    这份输出故意写得比较“教学”：不只是打印结果，也打印坐标系含义和公式。
    """
    fx = k[0, 0]
    fy = k[1, 1]
    cx = k[0, 2]
    cy = k[1, 2]

    loc = camera_transform.location
    rot = camera_transform.rotation

    print("\n" + "=" * 88)
    print("08 点击调试：pixel + depth -> camera_cv -> camera_ue -> world")
    print("=" * 88)

    print("\n[0] 本次使用的数据帧")
    print("    RGB image frame   : {}".format(frame_of(rgb_image)))
    print("    Depth image frame : {}".format(frame_of(depth_image)))
    print("    提示：当前 lesson 仍是异步 latest 数据；严肃采集时建议用 synchronous mode 对齐 frame。")

    print("\n[1] pygame / 图像像素坐标")
    print("    点击得到 event.pos = (u, v) = ({}, {})".format(u, v))
    print("    坐标系提示：pygame 图像左上角是 (0, 0)，u 向右增大，v 向下增大。")
    print("    numpy 取图像数组时使用 [行, 列]，所以同一个点要写成 [v, u]。")

    print("\n[2] 从 Depth 图读取深度")
    print("    公式：depth = depth_camera.latest_depth_m[v, u]")
    print("    代入：depth = latest_depth_m[{}, {}] = {} m".format(v, u, fmt3(depth)))
    print("    含义：这个像素对应的点，距离相机前方约 {} 米。".format(fmt3(depth)))

    print("\n[3] 相机内参 K")
    print("    K =")
    print("      [{:>10.3f} {:>10.3f} {:>10.3f}]".format(k[0, 0], k[0, 1], k[0, 2]))
    print("      [{:>10.3f} {:>10.3f} {:>10.3f}]".format(k[1, 0], k[1, 1], k[1, 2]))
    print("      [{:>10.3f} {:>10.3f} {:>10.3f}]".format(k[2, 0], k[2, 1], k[2, 2]))
    print("    fx={}, fy={}, cx={}, cy={}".format(
        fmt3(fx), fmt3(fy), fmt3(cx), fmt3(cy)
    ))
    print("    提示：cx/cy 是图像中心；u-cx 和 v-cy 表示点击点相对图像中心偏了多少像素。")

    print("\n[4] 反投影到 OpenCV 相机坐标 point_cv")
    print("    OpenCV camera 坐标系：x 向右，y 向下，z 向前。")
    print("    公式：x_cv = (u - cx) / fx * depth")
    print("    代入：x_cv = ({} - {}) / {} * {} = {} m".format(
        fmt3(u), fmt3(cx), fmt3(fx), fmt3(depth), fmt3(point_cv[0])
    ))
    print("    公式：y_cv = (v - cy) / fy * depth")
    print("    代入：y_cv = ({} - {}) / {} * {} = {} m".format(
        fmt3(v), fmt3(cy), fmt3(fy), fmt3(depth), fmt3(point_cv[1])
    ))
    print("    公式：z_cv = depth = {} m".format(fmt3(point_cv[2])))
    print("    结果：point_cv = ({}, {}, {})".format(
        fmt3(point_cv[0]), fmt3(point_cv[1]), fmt3(point_cv[2])
    ))

    print("\n[5] OpenCV 相机坐标 -> CARLA/UE 相机坐标 point_ue")
    print("    CARLA/UE camera 坐标系：x 向前，y 向右，z 向上。")
    print("    换轴公式：x_ue = z_cv, y_ue = x_cv, z_ue = -y_cv")
    print("    代入：x_ue = {}, y_ue = {}, z_ue = -{} = {}".format(
        fmt3(point_cv[2]), fmt3(point_cv[0]), fmt3(point_cv[1]), fmt3(point_ue[2])
    ))
    print("    结果：point_ue = ({}, {}, {})".format(
        fmt3(point_ue[0]), fmt3(point_ue[1]), fmt3(point_ue[2])
    ))

    print("\n[6] 相机外参 camera_transform")
    print("    camera world location = ({}, {}, {})".format(
        fmt3(loc.x), fmt3(loc.y), fmt3(loc.z)
    ))
    print("    camera world rotation = pitch {}, yaw {}, roll {}".format(
        fmt3(rot.pitch), fmt3(rot.yaw), fmt3(rot.roll)
    ))
    print("    提示：外参负责把“相机局部坐标里的点”旋转和平移到 CARLA 世界坐标。")

    print("\n[7] CARLA 世界坐标 clicked_world")
    print("    计算：clicked_world = camera_transform * point_ue")
    print("    结果：world = ({}, {}, {})".format(
        fmt3(clicked_world.x), fmt3(clicked_world.y), fmt3(clicked_world.z)
    ))
    print("    这个点会被 debug_draw_point() 画到 CARLA 世界中。")

    print("\n[8] 一句话总结")
    print("    (u, v) + depth + K + camera_transform => CARLA world point")
    print("=" * 88)


def make_click_hud_lines(u, v, depth, k, point_cv, point_ue, clicked_world, rgb_image, depth_image):
    """生成 pygame 左上角显示的简短调试结果。"""
    return [
        "Click pixel: ({}, {})".format(u, v),
        "Depth[v,u]: {} m".format(fmt3(depth)),
        "K: fx={} fy={} cx={} cy={}".format(
            fmt3(k[0, 0]), fmt3(k[1, 1]), fmt3(k[0, 2]), fmt3(k[1, 2])
        ),
        "Camera CV: x={} y={} z={}".format(
            fmt3(point_cv[0]), fmt3(point_cv[1]), fmt3(point_cv[2])
        ),
        "Camera UE: x={} y={} z={}".format(
            fmt3(point_ue[0]), fmt3(point_ue[1]), fmt3(point_ue[2])
        ),
        "World: x={} y={} z={}".format(
            fmt3(clicked_world.x), fmt3(clicked_world.y), fmt3(clicked_world.z)
        ),
        "Frames: rgb={} depth={}".format(frame_of(rgb_image), frame_of(depth_image)),
    ]


def main():
    """
    主函数：演示如何从像素坐标和深度值反算出世界坐标
    
    工作流程：
      1. 初始化 pygame 显示窗口
      2. 连接 CARLA 并生成车辆和相机
      3. 监听鼠标点击事件
      4. 点击时获取该像素的深度值
      5. 通过内参矩阵 K 将像素+深度转换为相机坐标
      6. 通过相机外参将相机坐标转换为世界坐标
      7. 在屏幕上绘制标记点并在 CARLA 中 debug draw
    """
    # 初始化 pygame 和字体系统
    pygame.init()
    pygame.font.init()

    # 创建普通可移动窗口，尺寸小于常见 1920x1080 屏幕，标题栏会留在屏幕内。
    display = pygame.display.set_mode((PYGAME_WINDOW_WIDTH, PYGAME_WINDOW_HEIGHT))
    pygame.display.set_caption("08 pixel + depth to world - movable window")
    font = pygame.font.SysFont("Arial", 18)  # 用于 HUD 显示的字体
    clock = pygame.time.Clock()  # 控制帧率的时钟

    # 构建相机内参矩阵 K
    # K 包含焦距 fx/fy 和主点 cx/cy，用于像素坐标和相机坐标的转换
    k = build_camera_intrinsic_k(PYGAME_WINDOW_WIDTH, PYGAME_WINDOW_HEIGHT, CAMERA_FOV)
    
    # 连接到 CARLA server
    client, world = connect_to_carla()

    # actors 列表用于跟踪所有生成的 actor，方便最后清理
    actors = []
    current_steer = 0.0  # 当前方向盘转角，用于平滑转向
    last_info = "Click a road pixel."  # 最后一条信息显示
    debug_hud_lines = [
        "Click a road pixel to print the full calculation flow.",
    ]
    clicked_pixel = None  # 用户点击的像素坐标 (u, v)
    clicked_world = None  # 反算出的世界坐标

    try:
        # 生成自车（ego vehicle）
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)

        # 创建两个相机传感器：RGB 相机和深度相机
        # 两者安装在相同位置，保证像素一一对应
        rgb_camera = CameraSensor(
            world,
            vehicle,
            "sensor.camera.rgb",
            width=PYGAME_WINDOW_WIDTH,
            height=PYGAME_WINDOW_HEIGHT,
        )
        depth_camera = CameraSensor(
            world,
            vehicle,
            "sensor.camera.depth",
            width=PYGAME_WINDOW_WIDTH,
            height=PYGAME_WINDOW_HEIGHT,
        )
        actors.extend([rgb_camera.actor, depth_camera.actor])

        running = True
        while running:
            # 限制循环频率为 30 FPS
            clock.tick(30)

            # 处理 pygame 事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:  # 窗口关闭按钮
                    running = False
                elif event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:  # ESC 键退出
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # 鼠标左键点击
                    # 记录点击的像素坐标
                    clicked_pixel = event.pos
                    
                    # 只有当深度图可用时才进行计算
                    if depth_camera.latest_depth_m is not None:
                        u, v = clicked_pixel
                        
                        # 从深度图中读取该像素的深度值（单位：米）
                        # latest_depth_m 是一个 numpy 数组，shape=(height, width)
                        depth = float(depth_camera.latest_depth_m[v, u])
                        
                        # 步骤 1：像素坐标 + 深度 -> 相机坐标系（OpenCV 风格）
                        # 使用内参矩阵 K 进行反投影
                        # 返回的是 [x, y, z]，表示点在相机坐标系中的位置
                        point_cv = pixel_depth_to_camera_cv(u, v, depth, k)
                        point_ue = camera_cv_to_camera_ue(point_cv)
                        
                        # 步骤 2：相机坐标 -> 世界坐标
                        # 需要相机的外参（位置和姿态），通过 get_transform() 获取
                        # 这个函数内部会：camera CV -> camera UE -> world
                        camera_transform = rgb_camera.get_transform()
                        clicked_world = pixel_depth_to_world(u, v, depth, camera_transform, k)
                        
                        # 格式化显示信息
                        last_info = (
                            "pixel=({}, {}) depth={:.2f}m camera_cv=({:.2f},{:.2f},{:.2f}) "
                            "world=({:.2f},{:.2f},{:.2f})"
                        ).format(
                            u, v, depth,
                            point_cv[0], point_cv[1], point_cv[2],  # 相机坐标系
                            clicked_world.x, clicked_world.y, clicked_world.z,  # 世界坐标系
                        )
                        debug_hud_lines = make_click_hud_lines(
                            u,
                            v,
                            depth,
                            k,
                            point_cv,
                            point_ue,
                            clicked_world,
                            rgb_camera.latest_image,
                            depth_camera.latest_image,
                        )
                        print_click_debug_flow(
                            u,
                            v,
                            depth,
                            k,
                            point_cv,
                            point_ue,
                            clicked_world,
                            camera_transform,
                            rgb_camera.latest_image,
                            depth_camera.latest_image,
                        )
                    else:
                        last_info = "Depth image is not ready yet. Please click again."
                        debug_hud_lines = [last_info]
                        print("\n[08 点击调试] Depth image is not ready yet. Please click again.")

            # 读取键盘状态，生成车辆控制指令
            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            # 渲染 RGB 相机图像到屏幕
            if rgb_camera.latest_rgb is not None:
                # make_pygame_surface 将 numpy RGB 数组转换为 pygame surface
                display.blit(make_pygame_surface(pygame, rgb_camera.latest_rgb), (0, 0))
            else:
                display.fill((10, 10, 10))  # 如果还没有图像，显示深色背景

            # 如果用户点击过，在点击位置绘制红色圆圈标记
            if clicked_pixel is not None:
                pygame.draw.circle(display, (255, 60, 60), clicked_pixel, 8, 2)

            # 如果已经计算出世界坐标，在 CARLA 世界中绘制调试点
            if clicked_world is not None:
                debug_draw_point(world, clicked_world, text="pixel+depth")

            # 准备 HUD 显示的文字信息
            lines = [
                "Lesson 08 | pixel + depth -> camera -> world | ESC quit",
                last_info,  # 显示最后一次点击的简短摘要
            ] + debug_hud_lines
            draw_text_lines(pygame, display, font, lines)
            
            # 更新屏幕显示
            pygame.display.flip()

    finally:
        destroy_actors(actors)
        pygame.quit()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
