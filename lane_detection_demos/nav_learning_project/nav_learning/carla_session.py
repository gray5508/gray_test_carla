from .paths import lane


# common.py imports CARLA, so this module is only imported by the live runner.
from common import CAMERA_FOV  # noqa: E402
from common import CameraSensor  # noqa: E402
from common import build_camera_intrinsic_k  # noqa: E402
from common import connect_to_carla  # noqa: E402
from common import destroy_actors  # noqa: E402
from common import get_keyboard_vehicle_control  # noqa: E402
from common import spawn_ego_vehicle  # noqa: E402


def set_world_async(world):
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


class CarlaCameraSession(object):
    """Owns CARLA world, ego vehicle, and RGB camera lifetime."""

    def __init__(self, config):
        self.config = config
        self.client = None
        self.world = None
        self.original_settings = None
        self.actors = []
        self.vehicle = None
        self.camera = None

    def __enter__(self):
        self.client, self.world = connect_to_carla()
        self.original_settings = set_world_async(self.world)

        self.vehicle = spawn_ego_vehicle(self.world)
        self.actors.append(self.vehicle)

        sensor_tick = "0.0"
        if self.config.camera_fps > 0:
            sensor_tick = str(1.0 / self.config.camera_fps)
        self.camera = CameraSensor(
            self.world,
            self.vehicle,
            "sensor.camera.rgb",
            width=self.config.width,
            height=self.config.height,
            fov=CAMERA_FOV,
            sensor_tick=sensor_tick,
        )
        self.actors.append(self.camera.actor)

        self.config.camera_k = build_camera_intrinsic_k(
            self.config.width,
            self.config.height,
            CAMERA_FOV,
        )
        self.config.camera_mount_transform = self.camera.transform
        return self

    def apply_keyboard_control(self, pygame_module, keys, current_steer):
        control, current_steer = get_keyboard_vehicle_control(pygame_module, keys, current_steer)
        self.vehicle.apply_control(control)
        return current_steer

    def __exit__(self, exc_type, exc, tb):
        destroy_actors(self.actors)
        if self.world is not None and self.original_settings is not None:
            self.world.apply_settings(self.original_settings)
        print("Restored original world settings.")
        print("Cleaned up.")

