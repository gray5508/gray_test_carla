"""
14_stable_ar_ground_arrow.py

本节目标：
  完整跑通一个教学版"转弯路口贴地箭头"闭环。

链路：
  RGB camera 图像
    -> 鼠标点击或合成检测点，得到 pixel
    -> pixel ray 与地面平面相交，得到 target_world
    -> 对 target_world 做低通滤波，减少抖动
    -> 车辆前方参考点 ahead_world
    -> ahead_world + target_world 构造地面箭头多边形
    -> 多边形世界点投影回 image pixel
    -> pygame 半透明 AR overlay

操作：
  W/A/S/D 或方向键   手动驾驶
  鼠标左键           模拟模型检测到一个路面点
  C                  清除鼠标目标，回到合成目标
  T                  切换合成目标：左转/右转/直行
  R                  重置滤波器
  ESC                退出

注意：
  这是客户端 overlay，不是 UE 里真正贴了 decal。
  但几何链路是真的：world/camera/pixel 都按相机模型计算。

核心知识点：
  - AR (Augmented Reality) 增强现实：在真实图像上叠加虚拟信息
  - 低通滤波：减少检测结果的抖动，提高稳定性
  - 世界坐标到像素坐标的投影：将 3D 箭头转换为 2D 屏幕显示
  - 完整的感知-决策-显示闭环：从检测到可视化全流程
  
工作流程详解：
  1. 获取目标点（两种方式）：
     A. 鼠标点击：模拟视觉模型检测到的路面关键点
     B. 合成目标：预设的左转/右转/直行的目标点
  2. 像素坐标 -> 世界坐标：使用射线-平面相交算法
  3. 低通滤波：对目标点进行平滑处理，减少抖动
  4. 构造箭头：根据起点（车前）和终点（目标点）生成箭头多边形
  5. 投影显示：将箭头的世界坐标投影回像素坐标，用半透明方式绘制
  
应用场景：
  - 导航指示：在路面上显示转弯箭头、车道指引
  - ADAS 系统：高级驾驶辅助系统的可视化界面
  - 自动驾驶调试：直观显示规划路径和目标点
  - 人机交互：向驾驶员展示车辆的意图和决策
"""

import random

import pygame

from common import CAMERA_FOV
from common import CameraSensor
from common import ExponentialLocationFilter
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import build_camera_intrinsic_k
from common import carla
from common import connect_to_carla
from common import debug_draw_arrow
from common import debug_draw_point
from common import destroy_actors
from common import draw_text_lines
from common import get_ground_z
from common import get_keyboard_vehicle_control
from common import ground_point_in_vehicle_frame
from common import make_ground_arrow_polygon
from common import make_pygame_surface
from common import pixel_to_world_on_ground
from common import project_polygon_to_pixels
from common import spawn_ego_vehicle
from common import world_to_pixel


# 定义三种合成目标模式：
#   (名称, 前方距离米, 右侧偏移米)
#   - 左转：前方 18 米，左侧 5.5 米（right_m 为负数表示左侧）
#   - 右转：前方 18 米，右侧 5.5 米
#   - 直行：前方 24 米，中间 0 米
TARGET_MODES = [
    ("synthetic left turn", 18.0, -5.5),
    ("synthetic right turn", 18.0, 5.5),
    ("synthetic straight", 24.0, 0.0),
]


def draw_transparent_arrow(pygame, display, pixels):
    """
    画半透明箭头。
    
    使用 pygame 的 SRCALPHA surface 实现半透明效果。
    先画填充的多边形（半透明），再画边框（不透明）。
    
    Args:
        pygame: pygame 模块
        display: 显示窗口 surface
        pixels: 箭头多边形的像素坐标列表 [(u1,v1), (u2,v2), ...]
    """
    if not pixels:
        return
    
    # 创建一个支持透明度的 surface，大小与窗口相同
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    
    # 绘制填充的箭头多边形
    # 颜色：(R=255, G=170, B=20, A=115)，橙色半透明
    pygame.draw.polygon(overlay, (255, 170, 20, 115), pixels)
    
    # 绘制箭头边框
    # 颜色：(R=255, G=245, B=180, A=220)，浅黄色较不透明
    # True 表示闭合多边形（最后一个点连回第一个点）
    pygame.draw.lines(overlay, (255, 245, 180, 220), True, pixels, 2)
    
    # 将 overlay 叠加到主显示窗口上
    display.blit(overlay, (0, 0))


def draw_cross(pygame, display, pixel, color):
    """
    画检测点十字标记。
    
    用于标记检测到的关键点位置，例如鼠标点击点或模型输出点。
    
    Args:
        pygame: pygame 模块
        display: 显示窗口 surface
        pixel: 像素坐标 (u, v)
        color: 颜色 (R, G, B)
    """
    x, y = int(pixel[0]), int(pixel[1])
    # 画水平线
    pygame.draw.line(display, color, (x - 8, y), (x + 8, y), 2)
    # 画垂直线
    pygame.draw.line(display, color, (x, y - 8), (x, y + 8), 2)


def main():
    """
    主函数：实现稳定的 AR 地面箭头显示
    
    工作流程：
      1. 初始化 pygame 显示窗口
      2. 连接 CARLA 并生成车辆和 RGB 相机
      3. 监听用户输入（鼠标点击、按键）
      4. 根据输入确定目标点（鼠标点击或合成目标）
      5. 将像素坐标转换到世界坐标
      6. 对目标点进行低通滤波
      7. 构造箭头多边形并投影到像素坐标
      8. 在屏幕上绘制半透明箭头和调试信息
      
    关键技术：
      - 射线-平面相交：像素 -> 世界坐标
      - 指数滑动平均：减少检测抖动
      - 世界坐标到像素坐标投影：3D -> 2D
      - 半透明渲染：AR overlay 视觉效果
    """
    # 初始化 pygame 和字体系统
    pygame.init()
    pygame.font.init()

    # 创建显示窗口
    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("14 stable AR ground arrow")
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    # 构建相机内参矩阵 K
    k = build_camera_intrinsic_k(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)
    
    # 连接到 CARLA server
    client, world = connect_to_carla()

    actors = []
    current_steer = 0.0  # 当前方向盘转角
    target_mode_index = 0  # 当前合成目标模式的索引（0=左转, 1=右转, 2=直行）
    manual_pixel = None  # 用户手动点击的像素坐标
    manual_target_world = None  # 手动点击对应的世界坐标
    target_filter = ExponentialLocationFilter(alpha=0.25)  # 目标点滤波器，alpha=0.25

    try:
        # 生成自车
        vehicle = spawn_ego_vehicle(world)
        actors.append(vehicle)
        
        # 创建 RGB 相机
        camera = CameraSensor(world, vehicle, "sensor.camera.rgb")
        actors.append(camera.actor)

        running = True
        while running:
            # 限制循环频率为 30 FPS
            clock.tick(30)

            # 处理 pygame 事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:  # 窗口关闭
                    running = False
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_ESCAPE:  # ESC 退出
                        running = False
                    elif event.key == pygame.K_c:  # C 键清除手动目标
                        manual_pixel = None
                        manual_target_world = None
                        target_filter.reset()  # 重置滤波器
                    elif event.key == pygame.K_t:  # T 键切换目标模式
                        target_mode_index = (target_mode_index + 1) % len(TARGET_MODES)
                        manual_pixel = None
                        manual_target_world = None
                        target_filter.reset()  # 重置滤波器
                    elif event.key == pygame.K_r:  # R 键重置滤波器
                        target_filter.reset()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # 鼠标左键点击
                    manual_pixel = event.pos  # 记录点击位置

            # 读取键盘状态，控制车辆
            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            # 渲染 RGB 相机图像
            if camera.latest_rgb is not None:
                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))
            else:
                display.fill((10, 10, 10))

            # 获取相机的位姿（外参）
            camera_tf = camera.get_transform()

            # === 步骤 1：确定箭头起点（车辆前方 9 米的地面点）===
            ahead_world = ground_point_in_vehicle_frame(world, vehicle, 9.0, 0.0)

            # === 步骤 2：确定目标点（两种来源）===
            
            # 目标点来源 A：鼠标点击像素，模拟模型检测到路面点
            if manual_pixel is not None:
                # 获取地面高度
                ground_z = get_ground_z(world, ahead_world) + 0.04
                
                # 像素坐标 -> 世界坐标（射线-平面相交）
                manual_target_world = pixel_to_world_on_ground(
                    manual_pixel[0],  # u 坐标
                    manual_pixel[1],  # v 坐标
                    camera_tf,  # 相机外参
                    k,  # 相机内参
                    ground_z,  # 地面高度
                )
                raw_target_world = manual_target_world
                target_source = "mouse pixel {}".format(manual_pixel)
                
                # 在点击位置绘制红色十字标记
                draw_cross(pygame, display, manual_pixel, (255, 60, 60))

            # 目标点来源 B：合成一个目标点，方便不用模型也能观察左转/右转/直行
            else:
                mode_name, forward_m, right_m = TARGET_MODES[target_mode_index]
                
                # 生成合成目标的世界坐标
                synthetic_world = ground_point_in_vehicle_frame(world, vehicle, forward_m, right_m)

                # 故意走一遍 world->pixel->ground 的链路，并加一点像素噪声
                # 这样更像真实模型输出：模型通常给你的是像素点，不是世界点
                synthetic_pixel = world_to_pixel(synthetic_world, camera_tf, k, WINDOW_WIDTH, WINDOW_HEIGHT, margin=100.0)
                raw_target_world = None
                
                if synthetic_pixel is not None:
                    # 添加像素噪声，模拟真实检测的不确定性
                    u = synthetic_pixel[0] + random.uniform(-3.0, 3.0)
                    v = synthetic_pixel[1] + random.uniform(-2.0, 2.0)
                    
                    # 绘制带噪声的检测点
                    draw_cross(pygame, display, (u, v), (255, 60, 60))
                    
                    # 像素坐标 -> 世界坐标
                    ground_z = get_ground_z(world, synthetic_world) + 0.04
                    raw_target_world = pixel_to_world_on_ground(u, v, camera_tf, k, ground_z)
                
                target_source = mode_name

            # === 步骤 3：对目标点进行低通滤波 ===
            filtered_target = target_filter.update(raw_target_world)

            # === 步骤 4：调试绘制（在 CARLA 世界中）===
            debug_draw_point(world, ahead_world, carla.Color(0, 255, 0), "ahead")  # 绿色：箭头起点

            if raw_target_world is not None:
                debug_draw_point(world, raw_target_world, carla.Color(255, 80, 80), "raw")  # 红色：原始检测点

            if filtered_target is not None:
                debug_draw_point(world, filtered_target, carla.Color(30, 220, 255), "filtered")  # 青色：滤波后的目标点
                debug_draw_arrow(world, ahead_world, filtered_target)  # 在 CARLA 中绘制调试箭头

                # === 步骤 5：构造箭头多边形并投影到像素坐标 ===
                arrow_world = make_ground_arrow_polygon(ahead_world, filtered_target, width=1.25)
                arrow_pixels = project_polygon_to_pixels(
                    arrow_world,
                    camera_tf,
                    k,
                    WINDOW_WIDTH,
                    WINDOW_HEIGHT,
                    margin=180.0,  # 允许超出屏幕 180 像素
                )
                
                # 如果所有顶点都在可视范围内，绘制半透明箭头
                if arrow_pixels is not None:
                    draw_transparent_arrow(pygame, display, arrow_pixels)

                # 绘制滤波后目标点的像素位置（青色圆点）
                filtered_pixel = world_to_pixel(filtered_target, camera_tf, k, WINDOW_WIDTH, WINDOW_HEIGHT, margin=80.0)
                if filtered_pixel is not None:
                    pygame.draw.circle(display, (30, 220, 255), (int(filtered_pixel[0]), int(filtered_pixel[1])), 8, 0)

            # === 步骤 6：更新 HUD 显示 ===
            lines = [
                "Lesson 14 | stable AR ground arrow | ESC quit",
                "Left click road pixel | C clear | T target mode | R reset filter",
                "Target source: {}".format(target_source),
                "red = raw detection pixel/world | cyan = filtered target | orange = AR arrow",
            ]
            draw_text_lines(pygame, display, font, lines)
            
            # 更新屏幕显示
            pygame.display.flip()

    finally:
        destroy_actors(actors)
        pygame.quit()
        print("Cleaned up.")


if __name__ == "__main__":
    main()
