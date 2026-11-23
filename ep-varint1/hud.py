"""
hud.py — интерфейс поверх игры (HUD):
  • спидометр справа вверху (зелёная → жёлтая → красная зона, стрелка, цифры);
  • индикаторы слева вверху: ФАРЫ, ТОРМОЗ, ПЕРЕГАЗОВКА;
  • подсказка по кнопкам внизу.
Всё нарисовано примитивами. Цвета и размеры — в config.py (раздел «ИНТЕРФЕЙС»).
Символы вроде стрелок ←/→ НЕ используем: не все шрифты умеют их рисовать.
"""
import math
import pygame

import config as cfg

# Шкала спидометра: от 225° (внизу слева) до -45° (внизу справа), по часовой
GAUGE_START = 225
GAUGE_SWEEP = 270


def zone_color(ratio):
    """Цвет по доле скорости: зелёный / жёлтый / красный."""
    if ratio >= cfg.RED_ZONE:
        return cfg.COLOR_RED
    if ratio >= cfg.YELLOW_ZONE:
        return cfg.COLOR_YELLOW
    return cfg.COLOR_GREEN


def polar(center, radius, angle_deg):
    """Точка на окружности. Угол как в математике (против часовой), Y экрана вниз."""
    a = math.radians(angle_deg)
    return (center[0] + math.cos(a) * radius, center[1] - math.sin(a) * radius)


class Hud:
    def __init__(self):
        self.font_big = pygame.font.SysFont(cfg.FONT_NAMES, 34, bold=True)
        self.font_mid = pygame.font.SysFont(cfg.FONT_NAMES, 16, bold=True)
        self.font_small = pygame.font.SysFont(cfg.FONT_NAMES, 13, bold=True)

    # ------------------------------------------------------------
    def draw(self, screen, car):
        t = pygame.time.get_ticks() / 1000.0      # время — для мигания
        blink = int(t * 4) % 2 == 0               # мигает 2 раза в секунду
        self._draw_speedometer(screen, car, blink)
        self._draw_indicators(screen, car, blink)
        self._draw_controls(screen)

    # ------------------------------------------------------------
    #  Помощники
    # ------------------------------------------------------------
    def _panel(self, screen, rect, border=None):
        """Полупрозрачная панель со скруглёнными углами."""
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, cfg.COLOR_PANEL, surf.get_rect(), border_radius=14)
        pygame.draw.rect(surf, border or cfg.COLOR_PANEL_BORDER, surf.get_rect(),
                         width=2, border_radius=14)
        screen.blit(surf, rect.topleft)

    def _text(self, screen, font, text, color, center):
        """Текст с тенью, выровненный по центру."""
        shadow = font.render(text, True, (0, 0, 0))
        label = font.render(text, True, color)
        rect = label.get_rect(center=center)
        screen.blit(shadow, rect.move(1, 2))
        screen.blit(label, rect)

    # ------------------------------------------------------------
    #  Спидометр
    # ------------------------------------------------------------
    def _draw_speedometer(self, screen, car, blink):
        ratio = car.speed_ratio
        color = zone_color(ratio)
        cx, cy = cfg.GAUGE_CENTER
        r = cfg.GAUGE_RADIUS

        panel = pygame.Rect(0, 0, r * 2 + 40, r * 2 + 64)
        panel.center = (cx, cy + 22)
        border = cfg.COLOR_RED if (car.over_revving and blink) else None
        self._panel(screen, panel, border)

        # Дуга из маленьких сегментов. Горит до текущей скорости, дальше — серая.
        segments = 54
        for i in range(segments):
            t0, t1 = i / segments, (i + 1) / segments
            a0 = GAUGE_START - GAUGE_SWEEP * t0
            a1 = GAUGE_START - GAUGE_SWEEP * t1 + 0.8   # маленький зазор между сегментами
            seg_color = zone_color(t0) if t0 < ratio else cfg.COLOR_GAUGE_OFF
            outer_r, inner_r = r, r - cfg.GAUGE_THICKNESS
            quad = [polar((cx, cy), outer_r, a0), polar((cx, cy), outer_r, a1),
                    polar((cx, cy), inner_r, a1), polar((cx, cy), inner_r, a0)]
            pygame.draw.polygon(screen, seg_color, quad)

        # Риски и цифры шкалы (0, 100, 200, ...)
        steps = 4
        for i in range(steps + 1):
            a = GAUGE_START - GAUGE_SWEEP * i / steps
            p1 = polar((cx, cy), r - cfg.GAUGE_THICKNESS - 2, a)
            p2 = polar((cx, cy), r - cfg.GAUGE_THICKNESS - 9, a)
            pygame.draw.line(screen, cfg.COLOR_TEXT_DIM, p1, p2, 2)
            value = int(cfg.MAX_SPEED * i / steps)
            self._text(screen, self.font_small, str(value), cfg.COLOR_TEXT_DIM,
                       polar((cx, cy), r - cfg.GAUGE_THICKNESS - 20, a))

        # Стрелка
        needle_angle = GAUGE_START - GAUGE_SWEEP * ratio
        tip = polar((cx, cy), r - 6, needle_angle)
        left = polar((cx, cy), 6, needle_angle + 90)
        right = polar((cx, cy), 6, needle_angle - 90)
        pygame.draw.polygon(screen, color, [tip, left, right])
        pygame.draw.circle(screen, (30, 34, 44), (cx, cy), 9)
        pygame.draw.circle(screen, color, (cx, cy), 9, 2)

        # Цифровая скорость
        self._text(screen, self.font_big, f"{abs(car.speed):.0f}", color, (cx, cy + 60))
        self._text(screen, self.font_small, "px/s", cfg.COLOR_TEXT_DIM, (cx, cy + 84))

        # Надпись под спидометром
        if car.over_revving and blink:
            self._text(screen, self.font_mid, "ПЕРЕГАЗОВКА!", cfg.COLOR_RED,
                       (cx, panel.bottom + 16))

    # ------------------------------------------------------------
    #  Индикаторы (как лампочки на приборке)
    # ------------------------------------------------------------
    def _draw_indicators(self, screen, car, blink):
        items = [
            ("ФАРЫ", car.headlights, cfg.COLOR_YELLOW),
            ("ТОРМОЗ", car.braking, cfg.COLOR_RED),
            ("ПЕРЕГАЗОВКА", car.over_revving and blink, cfg.COLOR_RED),
        ]
        panel = pygame.Rect(14, 14, 190, 54 + len(items) * 30)
        self._panel(screen, panel)

        # заголовок — название текущей машины
        title = self.font_mid.render(car.m["name"].upper(), True, car.m["color_shine"])
        screen.blit(title, (panel.left + 16, panel.top + 12))
        pygame.draw.line(screen, cfg.COLOR_GAUGE_OFF, (panel.left + 14, panel.top + 38),
                         (panel.right - 14, panel.top + 38), 1)

        for i, (label, on, color) in enumerate(items):
            y = panel.top + 58 + i * 30
            lamp = (panel.left + 24, y)
            if on:
                # свечение вокруг лампы
                glow = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*color, 70), (20, 20), 16)
                screen.blit(glow, (lamp[0] - 20, lamp[1] - 20))
                pygame.draw.circle(screen, color, lamp, 8)
            else:
                pygame.draw.circle(screen, cfg.COLOR_GAUGE_OFF, lamp, 8)
            pygame.draw.circle(screen, (0, 0, 0), lamp, 8, 1)

            text_color = cfg.COLOR_TEXT if on else cfg.COLOR_TEXT_DIM
            surf = self.font_mid.render(label, True, text_color)
            screen.blit(surf, surf.get_rect(midleft=(lamp[0] + 18, y)))

    # ------------------------------------------------------------
    #  Подсказка по кнопкам (клавиши-«кнопки»)
    # ------------------------------------------------------------
    def _draw_controls(self, screen):
        groups = [(["A", "D"], "ехать"), (["F"], "фары"), (["Esc"], "выход")]

        # сначала считаем общую ширину, чтобы выровнять по центру
        key_h, gap = 26, 8
        parts = []
        total = 0
        for keys, label in groups:
            widths = [max(key_h, self.font_mid.size(k)[0] + 14) for k in keys]
            label_w = self.font_mid.size(label)[0]
            w = sum(widths) + gap * (len(keys) - 1) + 8 + label_w
            parts.append((keys, widths, label, w))
            total += w
        total += 28 * (len(groups) - 1)

        panel = pygame.Rect(0, 0, total + 32, key_h + 16)
        panel.midbottom = (cfg.WIDTH // 2, cfg.HEIGHT - 10)
        self._panel(screen, panel)

        x = panel.left + 16
        y = panel.centery
        for keys, widths, label, w in parts:
            for k, kw in zip(keys, widths):
                key = pygame.Rect(x, y - key_h // 2, kw, key_h)
                pygame.draw.rect(screen, (235, 238, 245), key, border_radius=6)
                pygame.draw.rect(screen, (150, 155, 165), key.move(0, 2), width=2, border_radius=6)
                surf = self.font_mid.render(k, True, (25, 28, 36))
                screen.blit(surf, surf.get_rect(center=key.center))
                x += kw + gap
            x += 8 - gap
            surf = self.font_mid.render(label, True, cfg.COLOR_TEXT)
            screen.blit(surf, surf.get_rect(midleft=(x, y)))
            x += self.font_mid.size(label)[0] + 28
