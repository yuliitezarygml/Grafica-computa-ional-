"""
main.py — запуск программы: окно, фон, главный цикл, ввод, HUD.

Управление:
  A или стрелка влево    — ехать влево
  D или стрелка вправо   — ехать вправо
  F                      — включить / выключить фары
  Esc                    — выход
"""
import os
import sys
import pygame

import config as cfg
from car import Car

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
#  ВВОД
# ============================================================
def get_move_input(keys):
    """Переводит нажатые клавиши в -1 / 0 / +1."""
    move = 0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        move -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        move += 1
    return move


# ============================================================
#  ФОН (создаётся один раз, потом просто выводится каждый кадр)
# ============================================================
def make_background():
    bg = pygame.Surface((cfg.WIDTH, cfg.HEIGHT))
    if not _draw_photo_sky(bg):
        _draw_procedural_sky(bg)
    _draw_road(bg)
    return bg


def _draw_photo_sky(bg):
    """Рисует картинку из cfg.BACKGROUND_IMAGE сверху до дороги.
    Картинка масштабируется так, чтобы закрыть всю область, и обрезается по центру.
    Возвращает False, если картинки нет."""
    path = os.path.join(BASE_DIR, cfg.BACKGROUND_IMAGE) if cfg.BACKGROUND_IMAGE else ""
    if not path or not os.path.exists(path):
        return False
    try:
        image = pygame.image.load(path).convert()
    except pygame.error:
        return False

    area_w, area_h = cfg.WIDTH, cfg.GROUND_Y + cfg.CURB_HEIGHT
    scale = max(area_w / image.get_width(), area_h / image.get_height())
    new_size = (round(image.get_width() * scale), round(image.get_height() * scale))
    image = pygame.transform.smoothscale(image, new_size)
    # обрезка по центру
    left = (new_size[0] - area_w) // 2
    top = (new_size[1] - area_h) // 2
    bg.blit(image, (0, 0), pygame.Rect(left, top, area_w, area_h))
    return True


def _draw_procedural_sky(bg):
    """Запасной фон из примитивов (если нет картинки): небо, солнце, облака, холмы."""
    top, bottom = cfg.COLOR_SKY_TOP, cfg.COLOR_SKY_BOTTOM
    for y in range(cfg.GROUND_Y):
        t = y / cfg.GROUND_Y
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        pygame.draw.line(bg, color, (0, y), (cfg.WIDTH, y))

    pygame.draw.circle(bg, cfg.COLOR_SUN, cfg.SUN_POS, cfg.SUN_RADIUS)

    for x, y, s in cfg.CLOUDS:
        for dx, dy, r in [(-28, 6, 20), (0, 0, 28), (30, 6, 22), (10, 12, 22)]:
            pygame.draw.circle(bg, cfg.COLOR_CLOUD, (int(x + dx * s), int(y + dy * s)), int(r * s))

    hill_y = cfg.GROUND_Y + 50
    for x, r in cfg.HILLS_FAR:
        pygame.draw.circle(bg, cfg.COLOR_HILL_FAR, (x, hill_y), r)
    for x, r in cfg.HILLS_NEAR:
        pygame.draw.circle(bg, cfg.COLOR_HILL_NEAR, (x, hill_y), r)


def _draw_road(bg):
    """Дорога, бордюр и пунктирная разметка — поверх фона."""
    road = pygame.Rect(0, cfg.GROUND_Y, cfg.WIDTH, cfg.HEIGHT - cfg.GROUND_Y)
    pygame.draw.rect(bg, cfg.COLOR_ROAD, road)
    curb = pygame.Rect(0, cfg.GROUND_Y, cfg.WIDTH, cfg.CURB_HEIGHT)
    pygame.draw.rect(bg, cfg.COLOR_CURB, curb)
    x = 0
    while x < cfg.WIDTH:
        pygame.draw.rect(bg, cfg.COLOR_LANE, (x, cfg.LANE_Y, cfg.LANE_DASH, 6))
        x += cfg.LANE_DASH + cfg.LANE_GAP


# ============================================================
#  HUD (текст на экране)
# ============================================================
def make_font(size):
    """Берём первый найденный шрифт из списка (все поддерживают кириллицу)."""
    return pygame.font.SysFont("helveticaneue,arial,dejavusans,verdana", size, bold=True)


def draw_hud(screen, font, car):
    """Панель в левом верхнем углу: скорость, шкала скорости, состояние фар, подсказка.
    Нарочно без символов вроде стрелок — не все шрифты умеют их рисовать."""
    panel = pygame.Surface((340, 124), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 120), panel.get_rect(), border_radius=10)
    screen.blit(panel, (12, 12))

    speed = abs(car.speed)
    lines = [
        f"Скорость: {speed:.0f} px/s",
        f"Фары (F): {'ВКЛ' if car.headlights else 'выкл'}",
        "Ехать: A / D или стрелки",
    ]
    for i, text in enumerate(lines):
        surface = font.render(text, True, cfg.COLOR_TEXT)
        screen.blit(surface, (26, 22 + i * 26))

    # шкала скорости (прямоугольники)
    bar = pygame.Rect(26, 106, 312, 10)
    pygame.draw.rect(screen, (200, 200, 200), bar, border_radius=5, width=1)
    fill = bar.copy()
    fill.width = int(bar.width * min(1.0, speed / cfg.MAX_SPEED))
    if fill.width > 0:
        pygame.draw.rect(screen, (90, 220, 120), fill, border_radius=5)


# ============================================================
#  ГЛАВНЫЙ ЦИКЛ
# ============================================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((cfg.WIDTH, cfg.HEIGHT))
    pygame.display.set_caption(cfg.TITLE)
    clock = pygame.time.Clock()
    font = make_font(22)

    background = make_background()
    car = Car()

    running = True
    while running:
        dt = clock.tick(cfg.FPS) / 1000.0   # секунды с прошлого кадра

        # 1) События (одноразовые нажатия)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_f:
                    car.toggle_headlights()

        # 2) Обновление логики (зажатые клавиши)
        move = get_move_input(pygame.key.get_pressed())
        car.update(dt, move)

        # 3) Отрисовка
        screen.blit(background, (0, 0))
        car.draw(screen)
        draw_hud(screen, font, car)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
