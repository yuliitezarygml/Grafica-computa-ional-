"""Окно pygame и фоновое построение Симонброта. Запуск: python main.py."""

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import math
from pathlib import Path
import queue
import threading
import time

import pygame as pg

from fractal import (
    DEFAULT_ITERATIONS, DEFAULT_VIEW, MAX_ITERATIONS, MIN_ITERATIONS,
    View, colorize, compute_escape, orbit,
)


WIDTH = 900
HEIGHT = 560
HEADER = 104
FOOTER = 76
ITERATION_STEP = 50
MAX_ZOOM = 1e12
FORMULA = "z(n+1) = z(n)^2 * (abs(Re z(n)) + i*abs(Im z(n)))^2 + c; z(0) = 0"
BACKGROUND = (12, 18, 30)
FOREGROUND = (226, 234, 245)
MUTED = (157, 174, 196)
ACCENT = (80, 216, 208)


@dataclass(frozen=True)
class RenderRequest:
    view: View
    iterations: int
    mode: str
    width: int = WIDTH
    height: int = HEIGHT


@dataclass
class RenderMessage:
    generation: int
    kind: str
    y: int = 0
    pixels: object = None
    progress: float = 0.0
    elapsed: float = 0.0
    error: str = ""


class RenderWorker:
    """Один поток: новый запрос отменяет старый, pygame остаётся в главном."""

    def __init__(self):
        self.results = queue.Queue()
        self._condition = threading.Condition()
        self._pending = None
        self._cancel = threading.Event()
        self._generation = 0
        self._closed = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def request(self, request):
        with self._condition:
            self._cancel.set()
            self._cancel = threading.Event()
            self._generation += 1
            self._pending = (self._generation, request, self._cancel)
            self._condition.notify()
            return self._generation

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._closed or self._pending is not None)
                if self._closed:
                    return
                generation, request, cancel = self._pending
                self._pending = None
            started = time.perf_counter()
            try:
                # Быстрый предварительный вид, затем полосы полного разрешения.
                preview = compute_escape(
                    request.view, max(1, request.width // 4),
                    max(1, request.height // 4), request.iterations, cancel,
                )
                if preview is None or cancel.is_set():
                    continue
                self.results.put(RenderMessage(
                    generation, "preview", pixels=colorize(*preview, mode=request.mode),
                ))
                for y in range(0, request.height, 40):
                    rows = min(40, request.height - y)
                    result = compute_escape(
                        request.view, request.width, rows, request.iterations, cancel,
                        row_start=y, total_height=request.height,
                    )
                    if result is None or cancel.is_set():
                        break
                    self.results.put(RenderMessage(
                        generation, "tile", y=y,
                        pixels=colorize(*result, mode=request.mode),
                        progress=(y + rows) / request.height,
                    ))
                else:
                    if not cancel.is_set():
                        self.results.put(RenderMessage(
                            generation, "done", progress=1.0,
                            elapsed=time.perf_counter() - started,
                        ))
            except Exception as error:
                self.results.put(RenderMessage(generation, "error", error=str(error)))

    def close(self):
        with self._condition:
            self._closed = True
            self._cancel.set()
            self._condition.notify()
        self._thread.join(timeout=1)


def clip_segment(start, end, rect):
    """Отсечь отрезок в вещественных координатах даже при большом масштабе."""
    x1, y1 = start
    x2, y2 = end
    if not all(math.isfinite(value) for value in (x1, y1, x2, y2)):
        return None

    def region(x, y):
        return ((1 if x < rect.left else 2 if x > rect.right - 1 else 0)
                | (4 if y < rect.top else 8 if y > rect.bottom - 1 else 0))

    # Коэн - Сазерленд: координату границы задаём точно, чтобы избежать
    # потери младших разрядов при вычислении x + t * dx на глубоком зуме.
    while True:
        first, second = region(x1, y1), region(x2, y2)
        if not (first | second):
            return ((round(x1), round(y1)), (round(x2), round(y2)))
        if first & second:
            return None
        outside = first or second
        if outside & 8:
            y = rect.bottom - 1
            x = x1 + (x2 - x1) * ((y - y1) / (y2 - y1))
        elif outside & 4:
            y = rect.top
            x = x1 + (x2 - x1) * ((y - y1) / (y2 - y1))
        elif outside & 2:
            x = rect.right - 1
            y = y1 + (y2 - y1) * ((x - x1) / (x2 - x1))
        else:
            x = rect.left
            y = y1 + (y2 - y1) * ((x - x1) / (x2 - x1))
        if outside == first:
            x1, y1 = x, y
        else:
            x2, y2 = x, y


class FractalApp:
    def __init__(self, grade=10, iterations=DEFAULT_ITERATIONS):
        self.grade = grade
        self.iterations = iterations
        self.view = DEFAULT_VIEW
        self.mode = "bw" if grade <= 6 else ("discrete" if grade == 7 else "smooth")
        pg.display.init()
        pg.font.init()
        self.screen = pg.display.set_mode((WIDTH, HEADER + HEIGHT + FOOTER))
        pg.display.set_caption(f"Симонброт - лабораторная 3 - уровень {grade}")
        self.font = pg.font.SysFont("Arial", 16)
        self.small = pg.font.SysFont("Arial", 14)
        self.title_font = pg.font.SysFont("Arial", 26, bold=True)
        self.canvas_rect = pg.Rect(0, HEADER, WIDTH, HEIGHT)
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.worker = RenderWorker()
        self.running = True
        self.show_orbit = False
        self.selected_c = None
        self.orbit_points = []
        self.notice = ""
        self.notice_until = 0.0
        self.error = ""
        self.elapsed = 0.0
        self.request_render()

    @property
    def zoom(self):
        return DEFAULT_VIEW.span / self.view.span

    def request_render(self):
        self.generation = self.worker.request(RenderRequest(
            self.view, self.iterations, self.mode,
        ))
        self.image.fill((0, 0, 0))
        self.rendering = True
        self.progress = 0.0
        self.error = ""
        self.update_orbit()

    def update_orbit(self):
        if self.show_orbit and self.selected_c is not None:
            self.orbit_points = orbit(self.selected_c, self.iterations)

    def set_notice(self, text):
        self.notice = text
        self.notice_until = time.monotonic() + 5

    def poll_render(self):
        while True:
            try:
                result = self.worker.results.get_nowait()
            except queue.Empty:
                break
            # Отменённые изображения не могут перекрыть более новый вид.
            if result.generation != self.generation:
                continue
            if result.kind in ("preview", "tile"):
                surface = pg.surfarray.make_surface(result.pixels.swapaxes(0, 1))
                if result.kind == "preview":
                    surface = pg.transform.scale(surface, (WIDTH, HEIGHT))
                self.image.blit(surface, (0, result.y))
                self.progress = result.progress
            elif result.kind == "done":
                self.rendering = False
                self.elapsed = result.elapsed
                self.progress = 1.0
            elif result.kind == "error":
                self.rendering = False
                self.error = result.error

    def change_iterations(self, amount):
        value = max(MIN_ITERATIONS, min(MAX_ITERATIONS, self.iterations + amount))
        if value != self.iterations:
            self.iterations = value
            self.request_render()
        else:
            self.set_notice(f"Диапазон итераций: от {MIN_ITERATIONS} до {MAX_ITERATIONS}")

    def zoom_at(self, position, factor):
        if not self.canvas_rect.collidepoint(position):
            return
        target = max(1.0, min(MAX_ZOOM, self.zoom * factor))
        if target == self.zoom:
            self.set_notice("Достигнут предел масштаба")
            return
        x, y = position[0], position[1] - HEADER
        self.view = self.view.zoom_at(x, y, WIDTH, HEIGHT, target / self.zoom)
        self.request_render()

    def select_orbit(self, position):
        x, y = position[0], position[1] - HEADER
        self.selected_c = self.view.point(x, y, WIDTH, HEIGHT)
        self.show_orbit = True
        self.update_orbit()

    def handle_event(self, event):
        if event.type == pg.QUIT:
            self.running = False
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                self.running = False
            elif self.grade >= 7 and event.key == pg.K_r:
                self.view = DEFAULT_VIEW
                self.request_render()
            elif self.grade >= 7 and event.key == pg.K_b:
                color_mode = "discrete" if self.grade == 7 else "smooth"
                self.mode = color_mode if self.mode == "bw" else "bw"
                self.request_render()
            elif self.grade >= 8 and event.key in (pg.K_PLUS, pg.K_EQUALS, pg.K_KP_PLUS, pg.K_UP):
                self.change_iterations(ITERATION_STEP)
            elif self.grade >= 8 and event.key in (pg.K_MINUS, pg.K_UNDERSCORE, pg.K_KP_MINUS, pg.K_DOWN):
                self.change_iterations(-ITERATION_STEP)
            elif self.grade >= 10 and event.key == pg.K_o:
                self.show_orbit = not self.show_orbit
                if self.selected_c is None:
                    self.selected_c = complex(self.view.center_x, self.view.center_y)
                self.update_orbit()
            elif self.grade >= 10 and event.key == pg.K_s:
                self.save_snapshot()
        elif event.type == pg.MOUSEBUTTONDOWN and self.canvas_rect.collidepoint(event.pos):
            if self.grade >= 10 and event.button == 2:
                self.select_orbit(event.pos)
            elif self.grade >= 9 and event.button in (1, 3):
                self.zoom_at(event.pos, 2.0 if event.button == 1 else 0.5)
        elif self.grade >= 9 and event.type == pg.MOUSEWHEEL and event.y:
            self.zoom_at(pg.mouse.get_pos(), 2.0 if event.y > 0 else 0.5)

    def text(self, value, position, color=FOREGROUND, font=None):
        self.screen.blit((font or self.font).render(value, True, color), position)

    def project(self, z):
        scale = HEIGHT / self.view.span
        return (WIDTH / 2 + (z.real - self.view.center_x) * scale,
                HEADER + HEIGHT / 2 - (z.imag - self.view.center_y) * scale)

    def draw_orbit(self):
        if not self.show_orbit or not self.orbit_points:
            return
        self.screen.set_clip(self.canvas_rect)
        points = [self.project(z) for z in self.orbit_points]
        for start, end in zip(points, points[1:]):
            segment = clip_segment(start, end, self.canvas_rect)
            if segment is not None:
                pg.draw.line(self.screen, (255, 204, 94), *segment, width=2)
        for x, y in points:
            if self.canvas_rect.collidepoint(x, y):
                pg.draw.circle(self.screen, (255, 244, 207), (round(x), round(y)), 3)
        x, y = self.project(self.selected_c)
        if self.canvas_rect.collidepoint(x, y):
            pg.draw.circle(self.screen, ACCENT, (round(x), round(y)), 8, width=2)
        self.screen.set_clip(None)

    def draw(self):
        self.screen.fill(BACKGROUND)
        self.text("СИМОНБРОТ", (20, 10), font=self.title_font)
        self.text(f"ЛАБОРАТОРНАЯ 03  /  ВАРИАНТ 13  /  УРОВЕНЬ {self.grade}",
                  (475, 22), MUTED, self.small)
        self.text("Комплексная плоскость. Начальное значение: 0. Радиус выхода: 2.",
                  (20, 47), MUTED)
        mode_label = {"bw": "чёрно-белая", "discrete": "по итерациям", "smooth": "плавная"}[self.mode]
        self.text(f"Итерации: {self.iterations}   |   Палитра: {mode_label}", (20, 77), ACCENT)
        if self.grade >= 10:
            self.text(f"Масштаб: {self.zoom:.4g}   Центр: ({self.view.center_x:.11g}; {self.view.center_y:.11g})",
                      (440, 77), FOREGROUND, self.small)
        self.screen.blit(self.image, self.canvas_rect)
        self.draw_orbit()
        top = HEADER + HEIGHT + 9
        controls = ["Esc: выход"]
        if self.grade >= 7:
            controls += ["R: сброс", "B: палитра"]
        if self.grade >= 8:
            controls += ["Вверх / Вниз: итерации"]
        self.text("    |    ".join(controls), (20, top), FOREGROUND, self.small)
        second = []
        if self.grade >= 9:
            second += ["ЛКМ: увеличить", "ПКМ: уменьшить"]
        if self.grade >= 10:
            second += ["СКМ: выбрать орбиту", "O: орбита", "S: сохранить"]
        if second:
            self.text("    |    ".join(second), (20, top + 22), MUTED, self.small)
        status = f"Построение: {self.progress:.0%}" if self.rendering else f"Готово за {self.elapsed:.2f} с"
        if self.show_orbit and self.orbit_points:
            last = self.orbit_points[-1]
            outcome = "выход" if last.real**2 + last.imag**2 > 4 else "лимит итераций"
            status += (f"  |  c = {self.selected_c.real:.6g} {self.selected_c.imag:+.6g}i"
                       f"  |  {len(self.orbit_points) - 1} шагов, {outcome}")
        if self.error:
            status = f"Ошибка построения: {self.error}"
        if time.monotonic() < self.notice_until:
            status = self.notice
        self.text(status, (20, top + 44), ACCENT, self.small)
        if self.rendering:
            pg.draw.rect(self.screen, ACCENT, (0, HEADER + HEIGHT - 3, int(WIDTH * self.progress), 3))

    def save_snapshot(self, directory=None):
        if self.rendering or self.error:
            self.set_notice("Сохранение доступно после успешного завершения построения")
            return None
        directory = Path(directory) if directory else Path(__file__).resolve().parent / "screenshots"
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
        path = directory / f"simonbrot_{stamp}.png"
        metadata = {
            "formula": FORMULA, "grade": self.grade,
            "center": {"real": self.view.center_x, "imag": self.view.center_y},
            "vertical_span": self.view.span, "zoom": self.zoom,
            "iterations": self.iterations, "palette": self.mode,
            "escape_radius": 2, "canvas_size": [WIDTH, HEIGHT],
            "orbit_visible": self.show_orbit,
            "orbit_c": None if self.selected_c is None else {
                "real": self.selected_c.real, "imag": self.selected_c.imag,
            },
        }
        try:
            directory.mkdir(parents=True, exist_ok=True)
            self.draw()
            pg.image.save(self.screen, str(path))
            path.with_suffix(".json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
            )
        except (OSError, pg.error) as error:
            self.set_notice(f"Не удалось сохранить: {error}")
            return None
        self.set_notice(f"Сохранено: {path.name} + JSON")
        return path

    def run(self):
        clock = pg.time.Clock()
        try:
            while self.running:
                for event in pg.event.get():
                    self.handle_event(event)
                self.poll_render()
                self.draw()
                pg.display.flip()
                clock.tick(60)
        finally:
            self.close()

    def close(self):
        self.worker.close()
        pg.quit()


def iteration_value(text):
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Введите целое число итераций") from error
    if not MIN_ITERATIONS <= value <= MAX_ITERATIONS:
        raise argparse.ArgumentTypeError(f"Итерации должны быть от {MIN_ITERATIONS} до {MAX_ITERATIONS}")
    return value


def main(grade=None):
    parser = argparse.ArgumentParser(description="Лабораторная №3: фрактал Симонброт")
    if grade is None:
        parser.add_argument("--grade", type=int, choices=range(5, 11), default=10,
                            help="уровень реализации, по умолчанию 10")
    parser.add_argument("--iterations", type=iteration_value, help="число итераций (25–2000)")
    args = parser.parse_args()
    chosen_grade = grade if grade is not None else args.grade
    iterations = args.iterations
    if chosen_grade == 5:
        if iterations is not None:
            parser.error("для уровня 5 число итераций задано константой DEFAULT_ITERATIONS в fractal.py")
        iterations = DEFAULT_ITERATIONS
    elif iterations is None:
        while True:
            try:
                answer = input(f"Количество итераций ({MIN_ITERATIONS}–{MAX_ITERATIONS}, Enter = {DEFAULT_ITERATIONS}): ")
                iterations = iteration_value(answer.strip()) if answer.strip() else DEFAULT_ITERATIONS
                break
            except argparse.ArgumentTypeError as error:
                print(error)
            except EOFError:
                iterations = DEFAULT_ITERATIONS
                break
            except KeyboardInterrupt:
                return
    FractalApp(chosen_grade, iterations).run()
