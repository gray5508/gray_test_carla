"""
lesson_00_connect.py

目标：
1. 连接 CARLA server
2. 获取 world
3. 打印当前地图名字
4. 打印当前世界里 actor 数量

运行前：
先启动 CARLA server，例如：

D:\\HST_WORK\\carla\\WindowsNoEditor\\CarlaUE4.exe -carla-rpc-port=2000
"""

import carla


HOST = "localhost"
PORT = 2000
TIMEOUT = 30.0


def main():
    # 1. 创建 client
    # client 是 Python 脚本和 CARLA server 通信的入口。
    client = carla.Client(HOST, PORT)

    # 2. 设置超时时间
    # 如果 server 没启动或地图没加载完，get_world() 可能会超时。
    client.set_timeout(TIMEOUT)

    # 3. 获取当前仿真世界 world
    world = client.get_world()

    # 4. 获取地图
    carla_map = world.get_map()

    # 5. 获取所有 actor
    # actor 包括车辆、行人、传感器、交通灯等。
    actors = world.get_actors()

    print("Connected to CARLA server.")
    print("Map name:", carla_map.name)
    print("Actor count:", len(actors))

    # 6. 打印前几个 actor 看看
    print("\nFirst few actors:")
    for actor in actors[:10]:
        print("  id={}, type_id={}".format(actor.id, actor.type_id))


if __name__ == "__main__":
    main()