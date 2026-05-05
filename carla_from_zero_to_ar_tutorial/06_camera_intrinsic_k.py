"""
06_camera_intrinsic_k.py

本节目标：
  1. 理解相机内参 K；
  2. 理解 fx/fy/cx/cy；
  3. 用纯数学例子把 camera coordinate 投影到 pixel。

这一节不连接 CARLA server。
它只讲相机几何里最基础的 pinhole model。
"""

import numpy as np

from common import CAMERA_FOV
from common import WINDOW_HEIGHT
from common import WINDOW_WIDTH
from common import build_camera_intrinsic_k
from common import camera_cv_to_pixel


def main():
    """
    主函数：演示相机内参矩阵 K 和针孔相机模型。
    
    学习重点：
      1. 理解相机内参 K 的四个参数：fx, fy, cx, cy
      2. 理解焦距和 FOV 的关系
      3. 掌握 OpenCV 相机坐标系（x右，y下，z前）
      4. 学会把相机坐标点投影到像素坐标
    
    重要概念：
      - 这一节不连接 CARLA server，纯数学计算
      - 针孔相机模型（pinhole model）是计算机视觉的基础
      - 理解这个对后续的 AR、3D 重建、目标检测都很重要
    
    实验流程：
      1. 构建相机内参矩阵 K
      2. 打印 K 矩阵和各个参数的含义
      3. 用几个示例点演示相机坐标 -> 像素坐标的投影
      4. 观察距离对投影的影响
    """
    # ========================================================================
    # 第 1 步：构建相机内参矩阵 K
    # ========================================================================
    # build_camera_intrinsic_k() 来自 common.py
    # 根据图像尺寸和 FOV 计算内参矩阵
    k = build_camera_intrinsic_k(WINDOW_WIDTH, WINDOW_HEIGHT, CAMERA_FOV)

    # ========================================================================
    # 第 2 步：打印相机参数
    # ========================================================================
    print("Image size:")
    print("  width  =", WINDOW_WIDTH)
    print("  height =", WINDOW_HEIGHT)
    print("FOV:")
    print("  {} degrees".format(CAMERA_FOV))

    print("\nIntrinsic matrix K:")
    # 打印完整的 3x3 内参矩阵
    print(k)

    print("\nMeaning:")
    # fx: x 方向的焦距（像素单位）
    print("  fx = {:.3f}".format(k[0, 0]))
    # fy: y 方向的焦距（像素单位）
    print("  fy = {:.3f}".format(k[1, 1]))
    # cx: 主点 x 坐标（通常是图像中心）
    print("  cx = {:.3f}".format(k[0, 2]))
    # cy: 主点 y 坐标（通常是图像中心）
    print("  cy = {:.3f}".format(k[1, 2]))

    # ========================================================================
    # 第 3 步：解释 OpenCV 相机坐标系
    # ========================================================================
    print("\nOpenCV camera coordinate convention:")
    print("  x: right")   # x 轴指向右侧
    print("  y: down")    # y 轴指向下方
    print("  z: forward") # z 轴指向前方（光轴方向）
    print("\n注意：这和 CARLA 的相机坐标系不同！")
    print("  CARLA: x前，y右，z上")
    print("  OpenCV: x右，y下，z前")
    print("  所以需要 camera_ue_to_camera_cv() 进行转换")

    # ========================================================================
    # 第 4 步：定义测试点并投影
    # ========================================================================
    # 定义几个典型的相机坐标点（OpenCV 坐标系）
    # 格式：(名称, [x, y, z])
    #   x: 左右偏移（正=右，负=左）
    #   y: 上下偏移（正=下，负=上）
    #   z: 深度/距离（正=前方）
    sample_points = [
        ("center 10m", np.array([0.0, 0.0, 10.0])),      # 正前方 10 米
        ("right 1m at 10m", np.array([1.0, 0.0, 10.0])), # 前方 10 米、右侧 1 米
        ("left 1m at 10m", np.array([-1.0, 0.0, 10.0])), # 前方 10 米、左侧 1 米
        ("down 1m at 10m", np.array([0.0, 1.0, 10.0])),  # 前方 10 米、下方 1 米
        ("up 1m at 10m", np.array([0.0, -1.0, 10.0])),   # 前方 10 米、上方 1 米
        ("center 20m", np.array([0.0, 0.0, 20.0])),      # 正前方 20 米
        ("right 1m at 20m", np.array([1.0, 0.0, 20.0])),  # 前方 10 米、右侧 1 米
        ("left 1m at 20m", np.array([-1.0, 0.0, 20.0])),  # 前方 10 米、左侧 1 米
        ("down 1m at 20m", np.array([0.0, 1.0, 20.0])),  # 前方 10 米、下方 1 米
        ("up 1m at 20m", np.array([0.0, -1.0, 20.0])),  # 前方 10 米、上方 1 米
    ]

    print("\nCamera coordinate -> pixel:")
    # 遍历每个测试点，进行投影计算
    for name, point_cv in sample_points:
        # camera_cv_to_pixel() 来自 common.py
        # 它会：
        #   1. 检查 z > 0（点在相机前方）
        #   2. 应用针孔模型：u = fx*x/z + cx, v = fy*y/z + cy
        #   3. 返回 (u, v, depth)
        pixel = camera_cv_to_pixel(point_cv, k)
        print("  {:16s} camera {} -> pixel {}".format(name, point_cv, pixel))

    # ========================================================================
    # 第 5 步：总结观察结果
    # ========================================================================
    print("\n观察：")
    print("  1. z 越大（越远），同样 1 米横向偏移对应的像素偏移越小。")
    print("     例如：10m 处右侧 1m vs 20m 处右侧 1m，前者像素偏移更大")
    print("  2. 这就是远处检测点更容易因为几个像素误差导致世界坐标误差放大的原因。")
    print("     远处的物体，像素位置的微小误差会导致世界坐标的巨大误差")
    print("  3. 中心点 (0,0,z) 总是投影到 (cx, cy)，即图像中心")


if __name__ == "__main__":
    main()
