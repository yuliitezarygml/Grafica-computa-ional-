"""
car.py — классы Wheel (колесо), Smoke (дым) и Car (машина).

Идея «родитель — потомок»:
  Car (родитель) знает свою позицию (x, y) и направление (direction).
  Колёса, стёкла, фары, спойлер (потомки) хранят только СМЕЩЕНИЕ от центра корпуса.
  Реальные координаты на экране считает один метод Car.to_screen().
"""
import math
import random
import pygame

import config as cfg


class Wheel:
    """Колесо: шина + диск + вращающиеся спицы + суппорт + ступица."""

    def __init__(self, offset):
        self.offset = offset   # смещение центра колеса от центра корпуса
        self.angle = 0.0       # текущий угол спиц (радианы)

    def update(self, dx):
        """dx — на сколько пикселей проехала машина за кадр.
        Колесо катится без проскальзывания: угол = путь / радиус.
        Поэтому скорость вращения прямо пропорциональна скорости машины."""
        self.angle += dx / cfg.WHEEL_RADIUS

    def reset(self):
        self.angle = 0.0

    def draw(self, screen, center):
        """center — центр колеса в экранных координатах."""
        cx, cy = center
        pygame.draw.circle(screen, cfg.COLOR_TIRE, center, cfg.WHEEL_RADIUS)   # шина
        pygame.draw.circle(screen, cfg.COLOR_RIM, center, cfg.RIM_RADIUS)      # диск

        # Суппорт — НЕ вращается (закреплён на машине), виден между спицами
        caliper = pygame.Rect(0, 0, cfg.RIM_RADIUS * 2 - 6, cfg.RIM_RADIUS * 2 - 6)
        caliper.center = center
        pygame.draw.arc(screen, cfg.COLOR_CALIPER, caliper, math.radians(40), math.radians(140), 4)

        # Спицы: SPOKES_COUNT линий из центра, равномерно по кругу.
        # self.angle — общий поворот, он и создаёт вращение.
        for i in range(cfg.SPOKES_COUNT):
            a = self.angle + i * 2 * math.pi / cfg.SPOKES_COUNT
            end = (cx + math.cos(a) * (cfg.RIM_RADIUS - 1),
                   cy + math.sin(a) * (cfg.RIM_RADIUS - 1))
            pygame.draw.line(screen, cfg.COLOR_SPOKE, center, end, cfg.SPOKE_WIDTH)

        pygame.draw.circle(screen, cfg.COLOR_SPOKE, center, cfg.RIM_RADIUS, 1)  # ободок диска
        pygame.draw.circle(screen, cfg.COLOR_HUB, center, cfg.HUB_RADIUS)       # ступица


class Smoke:
    """Одна частица дыма. Живёт в мировых координатах (не привязана к машине)."""

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
    """Спорткар: корпус + кабина + детали + колёса + фары + дым/пламя."""

    def __init__(self):
        self.x = cfg.START_X                      # центр корпуса по X
        # центр корпуса по Y: колёса (низ = смещение + радиус) должны стоять на дороге
        wheel_bottom = cfg.WHEEL_OFFSETS[0][1] + cfg.WHEEL_RADIUS
        self.y = cfg.GROUND_Y - wheel_bottom

        self.speed = 0.0          # текущая скорость (px/с), знак = направление
        self.direction = 1        # 1 = смотрит вправо, -1 = влево (зеркало)
        self.headlights = False   # включены ли фары
        self.braking = False      # тормозим ли сейчас (для стоп-сигнала)

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

    def _screen_points(self, points):
        return [self.to_screen(p) for p in points]

    # ------------------------------------------------------------
    # Состояние
    # ------------------------------------------------------------
    @property
    def speed_ratio(self):
        """Скорость в долях от максимума: 0.0 … 1.0."""
        return min(1.0, abs(self.speed) / cfg.MAX_SPEED)

    @property
    def over_revving(self):
        """«Перегазовка» — скорость в красной зоне."""
        return self.speed_ratio >= cfg.RED_ZONE

    def toggle_headlights(self):
        self.headlights = not self.headlights

    # ------------------------------------------------------------
    # Логика
    # ------------------------------------------------------------
    def update(self, dt, move_input):
        """move_input: -1 (влево), 0 (ничего), +1 (вправо)."""
        self._update_speed(dt, move_input)
        self._move(dt)
        self._update_wheels(dt)
        self._update_smoke(dt)

    def _update_speed(self, dt, move_input):
        # Тормозим, если кнопку отпустили на ходу или жмём в обратную сторону
        self.braking = self.speed != 0 and (move_input == 0 or move_input * self.speed < 0)

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
            # Стоим — спицы возвращаются в исходное положение
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
    # Отрисовка (порядок важен: что рисуется позже — лежит сверху)
    # ------------------------------------------------------------
    def draw(self, screen):
        # 1) Полупрозрачные эффекты ПОД машиной: тень, дым, свет фар
        overlay = pygame.Surface((cfg.WIDTH, cfg.HEIGHT), pygame.SRCALPHA)
        self._draw_shadow(overlay)
        for puff in self.smoke:
            puff.draw(overlay)
        if self.headlights:
            self._draw_headlight_beam(overlay)
        screen.blit(overlay, (0, 0))

        # 2) Сама машина
        if self.over_revving:
            self._draw_flame(screen)
        self._poly(screen, cfg.COLOR_EXHAUST, cfg.EXHAUST_POINTS)
        self._poly(screen, cfg.COLOR_BODY, cfg.CABIN_POINTS, outline=True)
        self._poly(screen, cfg.COLOR_BODY, cfg.BODY_POINTS, outline=True)
        self._poly(screen, cfg.COLOR_BODY_DARK, cfg.SKIRT_POINTS)
        self._poly(screen, cfg.COLOR_STRIPE, cfg.STRIPE_POINTS)
        self._line(screen, cfg.COLOR_BODY_SHINE, *cfg.BODY_SHINE, 2)
        self._draw_windows(screen)
        self._draw_door(screen)
        self._poly(screen, cfg.COLOR_SPOILER, cfg.SPOILER_POINTS)
        self._poly(screen, cfg.COLOR_MIRROR, cfg.MIRROR_POINTS)
        self._draw_lights(screen)
        self._draw_wheels(screen)

        # 3) Свечение стоп-сигнала — поверх машины
        if self.braking:
            self._draw_brake_glow(screen)

    # --- маленькие помощники ---
    def _poly(self, screen, color, points, outline=False):
        pts = self._screen_points(points)
        pygame.draw.polygon(screen, color, pts)
        if outline:
            pygame.draw.polygon(screen, cfg.COLOR_OUTLINE, pts, 2)

    def _line(self, screen, color, start, end, width):
        pygame.draw.line(screen, color, self.to_screen(start), self.to_screen(end), width)

    # --- детали ---
    def _draw_shadow(self, overlay):
        w, h = cfg.SHADOW_SIZE
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (self.x, cfg.GROUND_Y + 2)
        pygame.draw.ellipse(overlay, (*cfg.COLOR_SHADOW, cfg.SHADOW_ALPHA), rect)

    def _draw_windows(self, screen):
        for window in cfg.WINDOWS:
            self._poly(screen, cfg.COLOR_WINDOW, window)
        for start, end in cfg.WINDOW_SHINES:
            self._line(screen, cfg.COLOR_WINDOW_SHINE, start, end, 3)

    def _draw_door(self, screen):
        for start, end in cfg.DOOR_LINES:
            self._line(screen, cfg.COLOR_DOOR_LINE, start, end, 2)
        self._poly(screen, cfg.COLOR_HANDLE, cfg.HANDLE_POINTS)

    def _draw_lights(self, screen):
        color = cfg.COLOR_HEADLIGHT_ON if self.headlights else cfg.COLOR_HEADLIGHT_OFF
        self._poly(screen, color, cfg.HEADLIGHT_POINTS, outline=True)
        tail = cfg.COLOR_BRAKE_GLOW if self.braking else cfg.COLOR_TAILLIGHT
        self._poly(screen, tail, cfg.TAILLIGHT_POINTS)

    def _draw_wheels(self, screen):
        for wheel in self.wheels:
            center = self.to_screen(wheel.offset)
            # арка: верхняя половина тёмного круга чуть больше колеса
            pygame.draw.circle(screen, cfg.COLOR_ARCH, center,
                               cfg.WHEEL_RADIUS + cfg.ARCH_PADDING,
                               draw_top_left=True, draw_top_right=True)
            wheel.draw(screen, center)

    def _draw_headlight_beam(self, overlay):
        """Жёлтый треугольник перед машиной (с учётом разворота)."""
        triangle = self._screen_points([
            cfg.HEADLIGHT_START, cfg.HEADLIGHT_FAR_TOP, cfg.HEADLIGHT_FAR_BOTTOM,
        ])
        pygame.draw.polygon(overlay, (*cfg.COLOR_HEADLIGHT_ON, cfg.HEADLIGHT_ALPHA), triangle)

    def _draw_brake_glow(self, screen):
        """Красный ореол вокруг заднего фонаря при торможении."""
        glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        for r, a in [(26, 40), (18, 70), (10, 110)]:
            pygame.draw.circle(glow, (*cfg.COLOR_BRAKE_GLOW, a), (30, 30), r)
        cx, cy = self.to_screen(cfg.TAILLIGHT_CENTER)
        screen.blit(glow, (cx - 30, cy - 30))

    def _draw_flame(self, screen):
        """Пламя из выхлопа при перегазовке: свечение + три треугольника, длина дрожит."""
        ex, ey = cfg.EXHAUST_OFFSET
        length = random.uniform(35, 60)          # каждый кадр разная длина → «дрожит»

        # оранжевое свечение вокруг пламени
        gx, gy = self.to_screen((ex - length * 0.4, ey))
        glow = pygame.Surface((90, 50), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*cfg.COLOR_FLAME_OUTER, 70), glow.get_rect())
        screen.blit(glow, (gx - 45, gy - 25))

        outer = [(ex, ey - 8), (ex - length, ey), (ex, ey + 8)]
        middle = [(ex, ey - 5), (ex - length * 0.7, ey), (ex, ey + 5)]
        core = [(ex, ey - 3), (ex - length * 0.4, ey), (ex, ey + 3)]
        pygame.draw.polygon(screen, cfg.COLOR_FLAME_OUTER, self._screen_points(outer))
        pygame.draw.polygon(screen, cfg.COLOR_FLAME_INNER, self._screen_points(middle))
        pygame.draw.polygon(screen, (255, 255, 255), self._screen_points(core))
