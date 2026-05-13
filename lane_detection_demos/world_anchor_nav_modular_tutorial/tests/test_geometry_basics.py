# -*- coding: utf-8 -*-
"""不依赖 CARLA 的基础几何测试。

这些测试不是为了覆盖所有算法，而是作为教学入口：你可以先用小函数理解
点的平均、平滑、插值，再去读完整的坐标投影代码。
"""

import unittest

from nav_demo.geometry import blend_points, interpolate_x_at_y, mean_point, point_distance


class GeometryBasicsTest(unittest.TestCase):
    def test_mean_and_blend(self):
        self.assertEqual(mean_point([(0, 0), (10, 20)]), (5, 10))
        self.assertEqual(blend_points((0, 0), (10, 20), 0.25), (2, 5))

    def test_distance(self):
        self.assertAlmostEqual(point_distance((0, 0), (3, 4)), 5.0)

    def test_interpolate_x_at_y(self):
        points = [(0, 0), (10, 10), (20, 20)]
        self.assertAlmostEqual(interpolate_x_at_y(points, 5), 5.0)
        self.assertIsNone(interpolate_x_at_y(points, 25))


if __name__ == "__main__":
    unittest.main()
