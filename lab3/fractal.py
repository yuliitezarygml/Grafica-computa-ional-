"""Математика и раскраска фрактала Симонброт без зависимости от окна.

Используется SimonBrot 4th из руководства Kalles Fraktaler:
https://mathr.co.uk/kf/manual.html#simonbrot-4th

    z[0] = 0
    z[n + 1] = z[n]² · (|Re z[n]| + i · |Im z[n]|)² + c

Модуль комплексного числа и покоординатный модуль здесь различаются.
Второй множитель содержит именно покоординатный модуль.
"""

from dataclasses import dataclass
import math
from typing import Protocol

import numpy as np


MIN_ITERATIONS = 25
MAX_ITERATIONS = 2000
DEFAULT_ITERATIONS = 200


class Cancellation(Protocol):
    """Интерфейс флага остановки, совместимый с threading.Event."""

    def is_set(self) -> bool: ...


def _check_dimensions(width: int, height: int) -> None:
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValueError("Размеры изображения должны быть целыми числами.")
    if width <= 0 or height <= 0:
        raise ValueError("Размеры изображения должны быть положительными.")


def _check_iterations(max_iter: int) -> None:
    if not isinstance(max_iter, int) or max_iter <= 0:
        raise ValueError("Количество итераций должно быть положительным целым числом.")


@dataclass(frozen=True)
class View:
    """Область комплексной плоскости; span задаёт её высоту.

    Одинаковый масштаб обеих осей сохраняет пропорции при любых
    размерах изображения. Положительная мнимая ось направлена вверх.
    """

    center_x: float = -0.3
    center_y: float = 0.0
    span: float = 3.0

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (self.center_x, self.center_y, self.span)):
            raise ValueError("Координаты и размер области должны быть конечными.")
        if self.span <= 0:
            raise ValueError("Высота области должна быть положительной.")

    def point(self, px: float, py: float, width: int, height: int) -> complex:
        """Перевести экранные координаты в комплексную плоскость."""
        _check_dimensions(width, height)
        scale = self.span / height
        return complex(
            self.center_x + (px - width / 2) * scale,
            self.center_y + (height / 2 - py) * scale,
        )

    def zoom_at(
        self, px: float, py: float, width: int, height: int, factor: float
    ) -> "View":
        """Приблизить при factor > 1, сохранив точку под курсором.

        Значение 0 < factor < 1 отдаляет область с той же привязкой.
        """
        if not math.isfinite(factor) or factor <= 0:
            raise ValueError("Коэффициент масштаба должен быть положительным.")
        anchor = self.point(px, py, width, height)
        return View(
            anchor.real + (self.center_x - anchor.real) / factor,
            anchor.imag + (self.center_y - anchor.imag) / factor,
            self.span / factor,
        )

    def pan(self, dx: float, dy: float) -> "View":
        """Сдвинуть центр на dx + i·dy в комплексной плоскости."""
        return View(self.center_x + dx, self.center_y + dy, self.span)


DEFAULT_VIEW = View()


def simonbrot_step(z: complex, c: complex) -> complex:
    """Выполнить одну итерацию канонического SimonBrot 4th."""
    folded = complex(abs(z.real), abs(z.imag))
    return z * z * folded * folded + c


def orbit(c: complex, max_iter: int) -> list[complex]:
    """Вернуть орбиту вместе с z[0] и первым вышедшим за радиус 2 z."""
    _check_iterations(max_iter)
    result = [0j]
    z = 0j
    for _ in range(max_iter):
        z = simonbrot_step(z, c)
        result.append(z)
        if z.real * z.real + z.imag * z.imag > 4:
            break
    return result


def compute_escape(
    view: View,
    width: int,
    height: int,
    max_iter: int,
    cancel: Cancellation | None = None,
    *,
    row_start: int = 0,
    total_height: int | None = None,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Вычислить номер выхода и плавный номер для каждого пикселя.

    Возвращаются массивы (height, width): counts типа int32 и smooth
    типа float64. Ноль означает, что выхода за радиус 2 не было.
    Вышедшие точки получают номер 1..max_iter, включая последний шаг.
    Вычисляются центры пикселей, то есть экранные координаты x+0.5,y+0.5.

    Для полосы полного изображения передайте её row_start и высоту
    полного изображения total_height. Сам View менять не требуется.
    При установленном флаге cancel возвращается None.
    """
    _check_dimensions(width, height)
    _check_iterations(max_iter)
    if total_height is None:
        total_height = height
    _check_dimensions(width, total_height)
    if not isinstance(row_start, int) or row_start < 0:
        raise ValueError("Начальная строка должна быть неотрицательным целым числом.")
    if row_start + height > total_height:
        raise ValueError("Полоса выходит за границы полного изображения.")
    if cancel is not None and cancel.is_set():
        return None

    scale = view.span / total_height
    real_axis = view.center_x + (np.arange(width) + 0.5 - width / 2) * scale
    imag_axis = view.center_y + (
        total_height / 2 - (np.arange(row_start, row_start + height) + 0.5)
    ) * scale
    # В каждом проходе остаются только точки, которые ещё не вышли.
    cr = np.broadcast_to(real_axis, (height, width)).ravel().copy()
    ci = np.broadcast_to(imag_axis[:, None], (height, width)).ravel().copy()
    active = np.arange(width * height)
    x = np.zeros(width * height, dtype=np.float64)
    y = np.zeros_like(x)
    counts = np.zeros(width * height, dtype=np.int32)
    smooth = np.zeros(width * height, dtype=np.float64)

    for iteration in range(1, max_iter + 1):
        if cancel is not None and cancel.is_set():
            return None
        # (a + ib)(a + id), где d содержит покоординатный модуль.
        a = x * x - y * y
        b = 2 * x * y
        d = np.abs(b)
        x = a * a - b * d + cr
        y = a * (b + d) + ci
        with np.errstate(over="ignore"):
            escaped = x * x + y * y > 4
        if np.any(escaped):
            indices = active[escaped]
            counts[indices] = iteration
            radius = np.hypot(x[escaped], y[escaped])
            # Стандартная поправка для отображения четвёртой степени.
            values = iteration + 1 - np.log(np.log(radius)) / math.log(4)
            smooth[indices] = np.maximum(
                0, np.nan_to_num(values, nan=float(iteration), neginf=0)
            )
            keep = ~escaped
            active, cr, ci = active[keep], cr[keep], ci[keep]
            x, y = x[keep], y[keep]
        if active.size == 0:
            break

    if cancel is not None and cancel.is_set():
        return None
    return counts.reshape(height, width), smooth.reshape(height, width)


# Четыре опорных оттенка: тёмно-синий, бирюзовый, кремовый и коралловый.
_GRADIENT = np.array(
    [[10, 23, 48], [28, 182, 194], [248, 235, 187], [239, 111, 91]],
    dtype=np.float64,
)
_STOPS = np.linspace(0, 1, len(_GRADIENT))


def colorize(counts: np.ndarray, smooth: np.ndarray, mode: str = "smooth") -> np.ndarray:
    """Раскрасить результат в чёрно-белом, ступенчатом или плавном режиме."""
    if mode not in {"bw", "discrete", "smooth"}:
        raise ValueError("Неизвестный режим раскраски.")
    if counts.ndim != 2 or smooth.shape != counts.shape:
        raise ValueError("Массивы раскраски должны иметь одинаковую двумерную форму.")
    escaped = counts > 0
    rgb = np.zeros((*counts.shape, 3), dtype=np.uint8)
    if mode == "bw":
        rgb[escaped] = 255
        return rgb
    if not np.any(escaped):
        return rgb
    if mode == "discrete":
        # Конечная палитра подчёркивает зависимость от целого номера шага.
        phase = ((counts[escaped] - 1) % 12) / 11
    else:
        phase = np.mod(smooth[escaped], 40.0) / 40.0
    colors = np.column_stack(
        [np.interp(phase, _STOPS, _GRADIENT[:, channel]) for channel in range(3)]
    )
    rgb[escaped] = np.rint(colors).astype(np.uint8)
    return rgb
