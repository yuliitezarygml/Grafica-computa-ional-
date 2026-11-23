"""
main.py — запуск программы: окно, главный цикл, ввод, HUD.

Управление:
  A / ←   — ехать влево
  D / →   — ехать вправо
  F       — включить / выключить фары
  Esc     — выход
"""
import sys
import pygame

import config as cfg
from car import Car


def get_move_input(keys):
    """Переводит нажатые клавиши в -1 / 0 / +1."""
    move = 0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        move -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        move += 1
    return move


def draw_background(screen):
    screen.fill(cfg.COLOR_SKY)
    ground = pygame.Rect(0, cfg.GROUND_Y, cfg.WIDTH, cfg.HEIGHT - cfg.GROUND_Y)
    pygame.draw.rect(screen, cfg.COLOR_GROUND, ground)


def draw_hud(screen, font, car):
    """Текст на экране: скорость и подсказки."""
    lines = [
        f"Скорость: {abs(car.speed):.0f} px/s",
        f"Фары (F): {'ВКЛ' if car.headlights else 'выкл'}",
        "A/D или ←/→ — ехать",
    ]
    for i, text in enumerate(lines):
        surface = font.render(text, True, cfg.COLOR_TEXT)
        screen.blit(surface, (15, 15 + i * 28))


def main():
    pygame.init()
    screen = pygame.display.set_mode((cfg.WIDTH, cfg.HEIGHT))
    pygame.display.set_caption(cfg.TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 28)

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
        draw_background(screen)
        car.draw(screen)
        draw_hud(screen, font, car)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
