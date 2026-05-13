# -*- coding: utf-8 -*-
"""CARLA 运行模式相关的小工具。"""

def set_world_async(world):
    """把 CARLA 世界切到异步模式，并返回原始设置。

    实时手动驾驶 demo 更适合异步模式：pygame、相机回调、YOLOP 推理各自按
    自己的节奏工作。退出时 `app.py` 会把这里返回的原始设置恢复回去。
    """
    original_settings = world.get_settings()
    if original_settings.synchronous_mode:
        settings = world.get_settings()
        settings.synchronous_mode = False
        settings.fixed_delta_seconds = None
        world.apply_settings(settings)
        print("World was synchronous; switched to asynchronous mode.")
    else:
        print("World is already asynchronous.")
    return original_settings
