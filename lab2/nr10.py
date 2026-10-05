# Кривая Коха — Оценка 10
# Управление: +/- глубина, S — переключить кривая/снежинка

import turtle

N = 3
MAX_N = 8
snowflake_mode = False
COLORS = ["red", "blue", "green", "orange", "purple", "cyan", "brown", "magenta"]

screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.title("Кривая Коха — Оценка 10")
screen.tracer(0)

t = turtle.Turtle()
t.speed(0)
t.hideturtle()

hud = turtle.Turtle()
hud.hideturtle()
hud.penup()

segment_count = 0

# Рекурсивная функция кривой Коха
# n == 0 — рисуем прямую линию (базовый случай, выход из рекурсии)
# n > 0  — делим отрезок на 3 части, среднюю заменяем треугольником
def koch(t, length, n, depth):
    global segment_count
    if n == 0:
        t.pencolor(COLORS[depth % len(COLORS)])
        t.forward(length)
        segment_count += 1
        return
    new_length = length / 3
    koch(t, new_length, n - 1, depth + 1)  # первая треть
    t.left(60)                               # поворот влево
    koch(t, new_length, n - 1, depth + 1)  # левая сторона треугольника
    t.right(120)                             # поворот вправо
    koch(t, new_length, n - 1, depth + 1)  # правая сторона треугольника
    t.left(60)                               # возврат направления
    koch(t, new_length, n - 1, depth + 1)  # последняя треть

def draw():
    global segment_count
    segment_count = 0
    t.clear()
    hud.clear()
    if snowflake_mode:
        t.penup()
        t.goto(-200, 120)
        t.pendown()
        for _ in range(3):
            koch(t, 400, N, 0)
            t.right(120)
    else:
        t.penup()
        t.goto(-300, 0)
        t.pendown()
        koch(t, 600, N, 0) 
    screen.update()

def increase():
    global N
    if N < MAX_N:
        N += 1
        draw()

def decrease():
    global N
    if N > 0:
        N -= 1
        draw()

def toggle_mode():
    global snowflake_mode
    snowflake_mode = not snowflake_mode
    draw()

screen.listen()
screen.onkey(increase, "Up")
screen.onkey(increase, "plus")
screen.onkey(increase, "=")
screen.onkey(decrease, "Down")
screen.onkey(decrease, "minus")
screen.onkey(decrease, "_")
screen.onkey(toggle_mode, "s")
screen.onkey(toggle_mode, "S")

draw()
turtle.mainloop()
