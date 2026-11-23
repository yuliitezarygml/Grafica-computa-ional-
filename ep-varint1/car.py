"""
car.py — классы Wheel (колесо), Smoke (дым) и Car (машина).

Идея «родитель — потомок»:
  Car (родитель) знает свою позицию (x, y) и направление (direction).
  Wheel / окно / фары (потомки) хранят только СМЕЩЕНИЕ от центра корпуса.
  Реальные координаты на экране считает один метод Car.to_screen().
"""
import math
import pygame

import config as cfg


class Wheel:
    """Колесо: круг + спица, которая вращается вокруг центра колеса."""

    def __init__(self, offset):
        self.offset = offset   # смещение центра колеса от центра корпуса
        self.angle = 0.0       # текущий угол спицы (радианы)

    def update(self, dx):
        """dx — на сколько пикселей проехала машина за кадр.
        Колесо катится без проскальзывания: угол = путь / радиус.
        Поэтому скорость вращения прямо пропорциональна скорости машины."""
        self.angle += dx / cfg.WHEEL_RADIUS

    def reset(self):
        self.angle = 0.0

    def draw(self, screen, center):
        """center — центр колеса в экранных координатах."""
        # круг (шина)
        pygame.draw.circle(screen, cfg.COLOR_WHEEL, center, cfg.WHEEL_RADIUS)
        # спица: линия из центра в точку на окружности под углом self.angle
        end = (
            center[0] + math.cos(self.angle) * (cfg.WHEEL_RADIUS - 3),
            center[1] + math.sin(self.angle) * (cfg.WHEEL_RADIUS - 3),
        )
        pygame.draw.line(screen, cfg.COLOR_SPOKE, center, end, cfg.SPOKE_WIDTH)
        # вторая спица напротив — чтобы вращение было лучше видно
        end2 = (
            center[0] - math.cos(self.angle) * (cfg.WHEEL_RADIUS - 3),
            center[1] - math.sin(self.angle) * (cfg.WHEEL_RADIUS - 3),
        )
        pygame.draw.line(screen, cfg.COLOR_SPOKE, center, end2, cfg.SPOKE_WIDTH)


class Smoke:
    """Одна частица дыма (доп. задание). Живёт в мировых координатах."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.age = 0.0

    def update(self, dt):
        self.age += dt
        self.y -= cfg.SMOKE_RISE_SPEED * dt   # плывёт вверх

    @property
    def alive(self):
        return self.age < cfg.SMOKE_LIFETIME

    def draw(self, overlay):
        t = self.age / cfg.SMOKE_LIFETIME                 # 0 → 1 за время жизни
        radius = cfg.SMOKE_START_RADIUS + cfg.SMOKE_GROWTH * self.age
        alpha = int(150 * (1 - t))                        # постепенно исчезает
        pygame.draw.circle(overlay, (*cfg.COLOR_SMOKE, alpha),
                           (int(self.x), int(self.y)), int(radius))


class Car:
    """Машина: корпус + колёса + фары + дым."""

    def __init__(self):
        self.x = cfg.START_X                      # центр корпуса по X
        # центр корпуса по Y: колёса (низ = смещение + радиус) должны стоять на дороге
        wheel_bottom = cfg.WHEEL_OFFSETS[0][1] + cfg.WHEEL_RADIUS
        self.y = cfg.GROUND_Y - wheel_bottom

        self.speed = 0.0          # текущая скорость (px/с), знак = направление
        self.direction = 1        # 1 = смотрит вправо, -1 = влево (зеркало)
        self.headlights = False   # включены ли фары

        self.wheels = [Wheel(off) for off in cfg.WHEEL_OFFSETS]
        self.smoke = []
        self._smoke_timer = 0.0

    # ------------------------------------------------------------
    # Относительные координаты → экранные (ГЛАВНЫЙ метод иерархии)
    # ------------------------------------------------------------
    def to_screen(self, rel):
        """Берёт точку относительно центра корпуса и даёт точку на экране.
        Здесь же делается зеркальное отражение: X умножается на direction."""
        return (self.x + rel[0] * self.direction, self.y + rel[1])

    # ------------------------------------------------------------
    # Логика
    # ------------------------------------------------------------
    def toggle_headlights(self):
        self.headlights = not self.headlights

    def update(self, dt, move_input):
        """move_input: -1 (влево), 0 (ничего), +1 (вправо)."""
        self._update_speed(dt, move_input)
        self._move(dt)
        self._update_wheels(dt)
        self._update_smoke(dt)

    def _update_speed(self, dt, move_input):
        if move_input != 0:
            # Разгон: скорость растёт постепенно, а не мгновенно
            self.speed += move_input * cfg.ACCELERATION * dt
            self.speed = max(-cfg.MAX_SPEED, min(cfg.MAX_SPEED, self.speed))
            self.direction = move_input        # разворот по направлению
        else:
            # Торможение: скорость плавно падает к нулю
            brake = cfg.BRAKE_FRICTION * dt
            if abs(self.speed) <= brake:
                self.speed = 0.0
            else:
                self.speed -= math.copysign(brake, self.speed)

    def _move(self, dt):
        self.x += self.speed * dt
        # Границы экрана: машина целиком остаётся в окне
        left = cfg.BODY_HALF_WIDTH
        right = cfg.WIDTH - cfg.BODY_HALF_WIDTH
        if self.x < left:
            self.x = left
            self.speed = 0.0
        elif self.x > right:
            self.x = right
            self.speed = 0.0

    def _update_wheels(self, dt):
        dx = self.speed * dt
        for wheel in self.wheels:
            wheel.update(dx)
            # Стоим — спица возвращается в исходное положение
            if cfg.RESET_WHEELS_ON_STOP and self.speed == 0.0:
                wheel.reset()

    def _update_smoke(self, dt):
        # новый дымок, пока машина едет
        if abs(self.speed) > 10:
            self._smoke_timer += dt
            if self._smoke_timer >= cfg.SMOKE_INTERVAL:
                self._smoke_timer = 0.0
                pos = self.to_screen(cfg.EXHAUST_OFFSET)
                self.smoke.append(Smoke(*pos))
        # обновляем и удаляем «умершие»
        for puff in self.smoke:
            puff.update(dt)
        self.smoke = [p for p in self.smoke if p.alive]

    # ------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------
    def draw(self, screen):
        # Полупрозрачные эффекты (дым и свет фар) рисуем на отдельном слое
        overlay = pygame.Surface((cfg.WIDTH, cfg.HEIGHT), pygame.SRCALPHA)
        for puff in self.smoke:
            puff.draw(overlay)
        if self.headlights:
            self._draw_headlights(overlay)
        screen.blit(overlay, (0, 0))

        self._draw_body(screen)
        self._draw_window(screen)
        for wheel in self.wheels:
            wheel.draw(screen, self.to_screen(wheel.offset))

    def _draw_body(self, screen):
        points = [self.to_screen(p) for p in cfg.BODY_POINTS]
        pygame.draw.polygon(screen, cfg.COLOR_BODY, points)

    def _draw_window(self, screen):
        points = [self.to_screen(p) for p in cfg.WINDOW_POINTS]
        pygame.draw.polygon(screen, cfg.COLOR_WINDOW, points)

    def _draw_headlights(self, overlay):
        """Жёлтый треугольник перед машиной (с учётом разворота)."""
        triangle = [
            self.to_screen(cfg.HEADLIGHT_START),
            self.to_screen(cfg.HEADLIGHT_FAR_TOP),
            self.to_screen(cfg.HEADLIGHT_FAR_BOTTOM),
        ]
        pygame.draw.polygon(overlay, (*cfg.COLOR_HEADLIGHT, cfg.HEADLIGHT_ALPHA), triangle)
