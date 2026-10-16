"""Состояние и анимация сцены, не зависящие от графического контекста."""

from dataclasses import dataclass, field
import math


@dataclass
class SceneState:
    grade: int = 10
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    camera_yaw: float = 30.0
    camera_pitch: float = 22.0
    distance: float = field(init=False)
    auto_rotate: bool = field(init=False)
    lighting: bool = field(init=False)
    textured: bool = field(init=False)
    wireframe: bool = field(init=False)
    windmill_running: bool = True
    blade_angle: float = 12.0
    door_open: bool = False
    door_angle: float = 0.0

    def __post_init__(self):
        if self.grade not in range(5, 11):
            raise ValueError("Уровень должен быть от 5 до 10")
        self.distance = 7.8 if self.grade >= 8 else 5.8
        self.auto_rotate = self.grade >= 7
        self.lighting = self.grade >= 9
        self.textured = self.grade >= 10
        self.wireframe = self.grade == 5

    def reset(self):
        self.__dict__.update(SceneState(self.grade).__dict__)

    def rotate(self, x=0.0, y=0.0, z=0.0):
        self.rotation_x = (self.rotation_x + x) % 360
        self.rotation_y = (self.rotation_y + y) % 360
        self.rotation_z = (self.rotation_z + z) % 360

    def orbit_camera(self, dx, dy):
        self.camera_yaw = (self.camera_yaw - dx * 0.35) % 360
        self.camera_pitch = max(-5.0, min(80.0, self.camera_pitch + dy * 0.35))

    def zoom(self, amount):
        self.distance = max(3.8, min(20.0, self.distance + amount))

    def eye(self):
        yaw, pitch = math.radians(self.camera_yaw), math.radians(self.camera_pitch)
        target_y = 0.55 if self.grade >= 8 else 0.0
        return (self.distance * math.cos(pitch) * math.sin(yaw),
                target_y + self.distance * math.sin(pitch),
                self.distance * math.cos(pitch) * math.cos(yaw))

    def update(self, dt):
        if dt < 0 or not math.isfinite(dt):
            raise ValueError("Время кадра должно быть конечным и неотрицательным")
        if self.auto_rotate:
            self.rotate(y=18.0 * dt)
        if self.grade >= 10:
            if self.windmill_running:
                self.blade_angle = (self.blade_angle + 90.0 * dt) % 360
            target = 100.0 if self.door_open else 0.0
            delta = max(-90.0 * dt, min(90.0 * dt, target - self.door_angle))
            self.door_angle += delta
