# -*- coding: utf-8 -*-
"""离线查看箭头地面多边形。

这个脚本不启动 CARLA，只构造一个起点和终点，打印 `ground_arrow_polygon()`
生成的七个顶点。建议在阅读 AR 绘制前先运行它，先把“箭头在地面坐标里
长什么样”理解清楚，再去看世界投影。
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nav_demo.runtime_deps import lane
from nav_demo.world_anchor import ground_arrow_polygon


def main():
    """生成一个偏左前方的箭头，并打印每个顶点的米制坐标。"""
    lane.ensure_runtime()
    start = lane.np.asarray([10.0, 0.0], dtype=lane.np.float32)
    target = lane.np.asarray([15.0, -2.2], dtype=lane.np.float32)
    points = ground_arrow_polygon(start, target, body_width=0.62, head_width=1.35, head_length=1.35)
    for idx, point in enumerate(points or []):
        print("{:02d}: forward={:.2f}m right={:.2f}m".format(idx, point[0], point[1]))


if __name__ == "__main__":
    main()
