"""
01_world_map_actor.py

本节目标：
  1. 理解 client / world / map / actor / blueprint；
  2. 生成一辆 ego vehicle；
  3. 打印当前世界里的 actor；
  4. 退出时清理自己生成的 actor。

核心概念：
  client:
    Python 脚本和 CARLA server 通信的入口。

  world:
    当前仿真世界。生成 actor、获取地图、debug draw 都从 world 开始。

  map:
    地图对象，能提供出生点、waypoint、道路拓扑等。

  actor:
    仿真世界里的对象。车辆、行人、传感器、交通灯都是 actor。

  blueprint:
    actor 的模板。先选 blueprint，再 spawn_actor 生成真实 actor。
"""

import time

from common import connect_to_carla
from common import destroy_actors
from common import print_world_summary
from common import spawn_ego_vehicle
import carla

def main():
    """
    主函数：演示 CARLA 的核心概念和 actor 管理。
    
    这个脚本展示了 CARLA 编程的基本流程：
      1. 连接到 CARLA server
      2. 获取世界信息（地图、actor 等）
      3. 生成车辆
      4. 观察效果
      5. 清理资源
    
    学习重点：
      - 理解 client/world/map/actor/blueprint 的关系
      - 掌握 actor 的生命周期管理（生成 -> 使用 -> 销毁）
      - 学会使用 try-finally 确保资源清理
    """
    # ========================================================================
    # 第 1 步：连接 CARLA server
    # ========================================================================
    # connect_to_carla() 来自 common.py，它会：
    #   1. 创建 carla.Client("localhost", 2000)
    #   2. 设置超时时间 30 秒
    #   3. 调用 client.get_world() 获取当前世界
    #
    # 返回值：
    #   client: 用于控制 CARLA server（加载地图、重启世界等高级操作）
    #   world:  用于操作当前仿真世界（生成 actor、获取信息等常用操作）
    #
    # 类比：
    #   client 像是“遥控器”，可以换频道（加载不同地图）
    #   world  像是“当前频道”，你可以在上面画画（生成 actor）
    client, world = connect_to_carla()
    
    # 打印世界的基本信息，确认连接成功
    # 会显示：地图名称、actor 数量、同步模式、固定时间步长
    print_world_summary(world)

    # ========================================================================
    # 第 2 步：准备清理列表
    # ========================================================================
    # 用一个列表记录本脚本生成的所有 actor
    # 在 finally 块中统一清理，确保即使出错也能清理
    #
    # 为什么需要这个列表？
    #   - CARLA actor 不会因为 Python 脚本退出而自动消失
    #   - 如果不清理，每次运行都会留下旧车辆
    #   - 多次运行后，出生点会被占满，无法生成新车辆
    actors_to_destroy = []

    try:
        # ====================================================================
        # 第 3 步：获取地图信息
        # ====================================================================
        # world.get_map() 返回当前地图对象
        # 地图对象包含：道路网络、车道信息、航点、出生点等
        carla_map = world.get_map()
        
        # get_spawn_points() 返回地图上预定义的可用出生点列表
        # 这些是 CARLA 官方设计的适合生成车辆的位置
        # 返回的是 carla.Transform 对象列表（包含位置 + 旋转）
        spawn_points = carla_map.get_spawn_points()

        print("\nMap object:")
        # carla_map.name: 地图名称，例如 "Carla/Maps/Town10HD_Opt"
        # 常见地图：Town01, Town02, ..., Town10HD_Opt 等
        print("  name:", carla_map.name)
        # len(spawn_points): 可用出生点数量，不同地图数量不同
        # Town10HD_Opt 通常有几百个出生点
        print("  spawn point count:", len(spawn_points))

        # ====================================================================
        # 第 4 步：查看生成车辆前的世界状态
        # ====================================================================
        print("\nBefore spawning our vehicle:")
        
        # world.get_actors() 返回世界中所有 actor 的集合
        # 这是一个 BlueprintLibrary 类型的对象，支持迭代和过滤
        # 注意：它不是 Python list，不支持切片操作！
        all_actors = world.get_actors()
        
        print("  actor count:", len(all_actors))
        # 只显示前 8 个 actor，避免输出太多
        # ⚠️ 注意：BlueprintLibrary 不支持切片，需要先转成 list
        for actor in list(all_actors)[:8]:
            # actor.id: actor 的唯一 ID（整数），每个 actor 都不同
            # actor.type_id: actor 的类型标识符（字符串）
            #   例如："vehicle.tesla.model3", "sensor.camera.rgb", "traffic.light"
            print("  id={} type_id={}".format(actor.id, actor.type_id))

        # ====================================================================
        # 第 5 步：生成 ego vehicle（主车）
        # ====================================================================
        # spawn_ego_vehicle() 来自 common.py
        # 内部会：
        #   1. 从 blueprint library 找到 vehicle.tesla.model3
        #   2. 设置 role_name="hero"（标记为主车）
        #   3. 使用 START_TRANSFORM 作为出生点
        #   4. 调用 world.try_spawn_actor() 生成车辆
        #   5. 关闭自动驾驶，设置初始姿态
        vehicle = spawn_ego_vehicle(world)
        
        # 把生成的车辆加入清理列表
        # 这样脚本退出时可以自动销毁它
        actors_to_destroy.append(vehicle)

        print("\nSpawned ego vehicle:")
        # vehicle.id: 这辆车的唯一 ID（整数）
        print("  id:", vehicle.id)
        # vehicle.type_id: 车辆的类型，应该是 "vehicle.tesla.model3"
        print("  type_id:", vehicle.type_id)
        # vehicle.get_transform(): 获取车辆当前的位置和旋转
        #   返回 carla.Transform 对象，包含：
        #     - location: carla.Location(x, y, z) 位置
        #     - rotation: carla.Rotation(pitch, yaw, roll) 旋转
        print("  transform:", vehicle.get_transform())

        # ====================================================================
        # 补充，添加个观察者
        # ====================================================================

        # 获取当前的观察者（Spectator）
        spectator = world.get_spectator()
        # 获取车辆的变换信息（位置和旋转）
        transform = vehicle.get_transform()

        # 将观察者的位置和旋转变换到车辆上方
        # 我们把观察者放在车顶上方 5 米处，并稍微低头看车
        spectator.set_transform(carla.Transform(
            transform.location + carla.Location(z=5.0),
            carla.Rotation(pitch=0,yaw=180)
        ))
        print("观察者已移动到车辆上方！")


        # ====================================================================
        # 第 6 步：查看生成车辆后的世界状态
        # ====================================================================
        print("\nAfter spawning our vehicle:")
        
        # 再次获取所有 actor，应该比之前多了一个（我们刚生成的车）
        all_actors = world.get_actors()
        print("  actor count:", len(all_actors))
        
        # 使用 filter() 方法只筛选车辆类型的 actor
        # filter() 支持通配符：
        #   "vehicle.*"     -> 匹配所有车辆
        #   "sensor.*"      -> 匹配所有传感器
        #   "traffic.*"     -> 匹配所有交通设施
        #   "vehicle.tesla.*" -> 匹配所有 Tesla 车辆
        #
        # ⚠️ 注意：filter() 返回的也是 BlueprintLibrary 类型，需要转 list
        for actor in list(all_actors.filter("vehicle.*"))[:10]:
            print("  vehicle id={} type_id={}".format(actor.id, actor.type_id))

        # ====================================================================
        # 第 7 步：等待观察
        # ====================================================================
        # 暂停 8 秒，让你在 CARLA UE4 窗口中看到生成的车辆
        #
        # 在这 8 秒内，你可以：
        #   1. 在 CARLA UE4 窗口中按 F 键跟随车辆
        #   2. 按 WASD 自由移动视角
        #   3. 观察车辆是否出现在正确的位置
        #   4. 检查控制台输出是否有错误
        print("\n观察 8 秒后清理车辆。")
        time.sleep(8.0)

    finally:
        # ====================================================================
        # 第 8 步：清理资源（非常重要！）
        # ====================================================================
        # finally 块保证无论是否发生异常，都会执行清理
        # 
        # 为什么必须清理？
        #   1. CARLA actor 不会因为 Python 脚本退出而自动消失
        #   2. 如果不清理，每次运行都会留下旧车辆，占用资源
        #   3. 多次运行后，出生点会被占满，无法生成新车辆
        #   4. 传感器 actor 如果不先 stop() 就 destroy()，可能导致崩溃
        #
        # destroy_actors() 来自 common.py
        # 内部会：
        #   1. 反向遍历列表（先销毁后创建的 actor）
        #   2. 对每个 actor，如果有 stop() 方法就先调用 stop()
        #   3. 然后调用 actor.destroy() 销毁 actor
        #   4. 用 try-except 捕获异常，避免中断清理流程
        destroy_actors(actors_to_destroy)
        print("Cleaned up actors created by this lesson.")


if __name__ == "__main__":
    main()
