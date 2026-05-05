"""
11_mouse_and_opencv_detection.py

本节目标：
  1. 鼠标点击获取像素点；
  2. 演示 OpenCV 如何处理当前 RGB 图像；
  3. 做一个很简单的颜色阈值检测，把检测点画回 pygame。

这不是车道线算法，只是告诉你：
  camera.latest_rgb 是普通 numpy 图像，可以直接交给 OpenCV / 深度学习模型。

如果环境没有 opencv-python：
  鼠标点击功能仍然可用；
  OpenCV 检测部分会在 HUD 上提示 cv2 不可用。

核心知识点：
  - CARLA 相机输出的图像是标准的 numpy 数组，可以直接用于计算机视觉处理
  - OpenCV 可以方便地进行图像处理、特征提取、目标检测等任务
  - 可以将检测结果可视化回 pygame 窗口，实现实时反馈
  
应用场景：
  - 车道线检测：使用 Canny 边缘检测、霍夫变换等
  - 交通标志识别：使用颜色分割、形状检测
  - 障碍物检测：使用语义分割模型
  - 任何基于图像的自动驾驶感知任务
  
工作流程：
  1. 从 CARLA 相机获取 RGB 图像（numpy 数组）
  2. 将图像传递给 OpenCV 进行处理
  3. 得到检测结果（例如关键点、边界框等）
  4. 将结果绘制到 pygame 窗口中显示
"""

import pygame
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from common import CameraSensor
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import connect_to_carla
from common import destroy_actors
from common import draw_text_lines
from common import get_keyboard_vehicle_control
from common import make_pygame_surface
from common import spawn_ego_vehicle


def detect_bright_yellow_points(rgb_image):
    """
    一个玩具检测器：找画面中偏黄色且较亮的区域中心。

    真实项目里，你会把这里替换成：
      lane detection model（车道线检测模型）
      intersection detection model（路口检测模型）
      segmentation model（语义分割模型）
      keypoint model（关键点检测模型）
    
    Args:
        rgb_image: numpy 数组，shape=(height, width, 3)，RGB 格式
        
    Returns:
        points: 列表，每个元素是 (u, v, area) 三元组
                u, v 是检测点的像素坐标
                area 是该区域的面积（用于排序）
    """
    # 检查 OpenCV 是否可用
    if cv2 is None:
        return []

    # OpenCV 很多函数默认使用 BGR/HSV，所以需要转换
    # COLOR_RGB2HSV 将 RGB 图像转换为 HSV（色相、饱和度、明度）空间
    hsv = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2HSV)

    # 黄色的一个粗略 HSV 范围。这个范围只是演示，不保证适合所有天气/地图。
    # H (Hue): 色相，黄色大约在 15-40 度
    # S (Saturation): 饱和度，80-255 表示颜色比较鲜艳
    # V (Value): 明度，120-255 表示比较亮
    lower = np.array([15, 80, 120], dtype=np.uint8)
    upper = np.array([40, 255, 255], dtype=np.uint8)
    
    # inRange 创建二值掩码：在范围内的像素为 255（白色），其他为 0（黑色）
    mask = cv2.inRange(hsv, lower, upper)

    # 找轮廓，取面积比较大的区域中心
    # RETR_EXTERNAL: 只检测最外层轮廓
    # CHAIN_APPROX_SIMPLE: 压缩水平、垂直和对角线段，只保留端点
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    points = []
    for contour in contours:
        # 计算轮廓的面积
        area = cv2.contourArea(contour)
        
        # 过滤掉太小的区域（可能是噪声）
        if area < 25:
            continue
        
        # 计算轮廓的矩（moments），用于找到质心
        m = cv2.moments(contour)
        
        # m["m00"] 是零阶矩，表示区域的面积
        # 如果面积接近 0，说明轮廓无效，跳过
        if m["m00"] <= 1e-6:
            continue
        
        # 计算质心坐标
        # m["m10"]/m["m00"] 得到 x 坐标
        # m["m01"]/m["m00"] 得到 y 坐标
        u = int(m["m10"] / m["m00"])
        v = int(m["m01"] / m["m00"])
        points.append((u, v, area))

    # 面积大的排前面，只返回前 20 个最大的区域
    points.sort(key=lambda item: item[2], reverse=True)
    return points[:20]


def main():
    """
    主函数：演示如何使用 OpenCV 处理 CARLA 相机图像并显示检测结果
    
    工作流程：
      1. 初始化 pygame 显示窗口
      2. 连接 CARLA 并生成车辆和 RGB 相机
      3. 监听鼠标点击事件，记录用户点击的位置
      4. 每帧使用 OpenCV 检测黄色区域
      5. 在屏幕上显示：
         - RGB 相机图像
         - 鼠标点击的红色圆圈
         - OpenCV 检测到的黄色区域的黄色圆圈
      6. 实时更新 HUD 信息
      
    按键说明：
      - ESC: 退出程序
      - C: 清除所有鼠标点击的点
      - 鼠标左键: 添加一个新的点击点
    """
    # 初始化 pygame 和字体系统
    pygame.init()
    pygame.font.init()

    # 创建显示窗口
    display = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("11 mouse and OpenCV detection")
    font = pygame.font.SysFont("Arial", 18)
    clock = pygame.time.Clock()

    # 连接到 CARLA server
    client, world = connect_to_carla()
    
    actors = []
    current_steer = 0.0  # 当前方向盘转角
    clicked_points = []  # 存储用户点击的像素坐标列表
    detected_points = []  # 存储 OpenCV 检测到的点列表

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
                    elif event.key == pygame.K_c:  # C 键清除点击点
                        clicked_points = []
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # 鼠标左键点击
                    clicked_points.append(event.pos)  # 记录点击位置

            # 读取键盘状态，控制车辆
            keys = pygame.key.get_pressed()
            control, current_steer = get_keyboard_vehicle_control(pygame, keys, current_steer)
            vehicle.apply_control(control)

            # 渲染相机图像并进行检测
            if camera.latest_rgb is not None:
                # 显示 RGB 图像
                display.blit(make_pygame_surface(pygame, camera.latest_rgb), (0, 0))
                
                # 使用 OpenCV 检测黄色区域
                # camera.latest_rgb 是 numpy 数组，可以直接传给 OpenCV
                detected_points = detect_bright_yellow_points(camera.latest_rgb)
            else:
                display.fill((10, 10, 10))
                detected_points = []

            # 绘制用户点击的点（红色圆圈）
            for point in clicked_points:
                pygame.draw.circle(display, (255, 60, 60), point, 7, 2)

            # 绘制 OpenCV 检测到的点（黄色实心圆）
            # 每个点是 (u, v, area) 三元组，我们只用前两个坐标
            for u, v, area in detected_points:
                pygame.draw.circle(display, (0, 255, 255), (u, v), 5, 0)  # 0 表示填充

            # 准备 HUD 显示的文字
            lines = [
                "Lesson 11 | mouse pixels + optional OpenCV toy detector | ESC quit | C clear clicks",
                "Clicked points: {}".format(clicked_points[-5:]),  # 只显示最后 5 个点击点
                "cv2: {} | yellow detections: {}".format("available" if cv2 else "not installed", len(detected_points)),
                "Replace toy detector with your lane/intersection model later.",  # 后续可以替换为真实的检测模型
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
