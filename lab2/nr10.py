# ============================================================================
# Лабораторная работа 2: Геометрические фракталы
# Вариант: Кривая Коха (Терентий Юлиан)
#
# Кривая Коха — фрактал, в котором каждый отрезок делится на 3 равные части,
# а средняя часть заменяется двумя сторонами равностороннего треугольника.
#
# Управление:
#   + / Стрелка вверх   — увеличить глубину рекурсии
#   - / Стрелка вниз    — уменьшить глубину рекурсии
#   S                   — переключить режим: кривая / снежинка
# ============================================================================

import turtle

# --- Параметры ---
N = 3                 # Начальная глубина рекурсии
MAX_N = 7             # Максимальная глубина (защита от зависания)
snowflake_mode = False # Режим: False = кривая, True = снежинка Коха

# Цвета для каждого уровня рекурсии (Оценка 9)
COLORS = ["red", "blue", "green", "orange", "purple", "cyan", "brown", "magenta"]

# --- Настройка экрана ---
screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.title("Кривая Коха — Оценка 10")
screen.tracer(0)       # Отключаем анимацию для мгновенной отрисовки

# --- Черепашка для рисования фрактала ---
t = turtle.Turtle()
t.speed(0)
t.hideturtle()

# --- Черепашка для текстовой информации (HUD) ---
hud = turtle.Turtle()
hud.hideturtle()
hud.penup()

# Счетчик нарисованных сегментов (Оценка 9)
segment_count = 0


def koch(t, length, n, depth):
    """
    Рекурсивная функция построения кривой Коха.

    Базовая часть (условие выхода из рекурсии):
        Если n == 0, рисуем прямой отрезок длиной length.

    Рекурсивный вызов:
        Если n > 0, делим отрезок на 3 части и заменяем среднюю
        двумя сторонами равностороннего треугольника:
        1. Рисуем первую треть
        2. Поворачиваем влево на 60°
        3. Рисуем левую сторону треугольника
        4. Поворачиваем вправо на 120°
        5. Рисуем правую сторону треугольника
        6. Поворачиваем влево на 60° (возвращаемся к исходному направлению)
        7. Рисуем последнюю треть

    Параметры:
        t      — черепашка
        length — длина текущего отрезка
        n      — оставшаяся глубина рекурсии
        depth  — текущий уровень глубины (для выбора цвета)
    """
    global segment_count

    # === Базовая часть: условие выхода из рекурсии ===
    if n == 0:
        # Цветовая дифференциация по уровню рекурсии (Оценка 9)
        t.pencolor(COLORS[depth % len(COLORS)])
        t.forward(length)
        segment_count += 1
        return

    # === Рекурсивный вызов ===
    new_length = length / 3

    koch(t, new_length, n - 1, depth + 1)   # Первая треть
    t.left(60)                                # Поворот влево 60°
    koch(t, new_length, n - 1, depth + 1)   # Левая сторона треугольника
    t.right(120)                              # Поворот вправо 120°
    koch(t, new_length, n - 1, depth + 1)   # Правая сторона треугольника
    t.left(60)                                # Возврат к направлению
    koch(t, new_length, n - 1, depth + 1)   # Последняя треть


def draw():
    """Полная перерисовка фрактала и информационной панели."""
    global segment_count
    segment_count = 0

    t.clear()
    hud.clear()

    if snowflake_mode:
        # Снежинка Коха: три кривых Коха, образующие треугольник
        t.penup()
        t.goto(-200, 120)
        t.pendown()
        for _ in range(3):
            koch(t, 400, N, 0)
            t.right(120)
    else:
        # Одиночная кривая Коха
        t.penup()
        t.goto(-300, 0)
        t.pendown()
        koch(t, 600, N, 0)

    # Информационная строка (Оценка 9)
    mode_str = "Снежинка" if snowflake_mode else "Кривая"
    hud.goto(0, 260)
    hud.color("darkblue")
    hud.write(
        f"Режим: {mode_str}  |  Глубина N = {N}  |  Сегментов: {segment_count}"
        f"  |  + / - глубина  |  S — режим",
        align="center", font=("Arial", 12, "bold")
    )
    screen.update()


# --- Обработчики клавиш (Оценка 8) ---
def increase():
    """Увеличить глубину рекурсии (с ограничением MAX_N)."""
    global N
    if N < MAX_N:
        N += 1
        draw()

def decrease():
    """Уменьшить глубину рекурсии (минимум 0)."""
    global N
    if N > 0:
        N -= 1
        draw()

def toggle_mode():
    """Переключить режим: кривая / снежинка (доп. задание)."""
    global snowflake_mode
    snowflake_mode = not snowflake_mode
    draw()

# --- Регистрация клавиш ---
screen.listen()
screen.onkey(increase, "Up")
screen.onkey(increase, "plus")
screen.onkey(increase, "=")
screen.onkey(decrease, "Down")
screen.onkey(decrease, "minus")
screen.onkey(decrease, "_")
screen.onkey(toggle_mode, "s")
screen.onkey(toggle_mode, "S")

# --- Запуск ---
draw()
turtle.mainloop()
