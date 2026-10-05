import turtle

N = 3
MAX_N = 7

COLORS = ["red", "blue", "green", "orange", "purple", "cyan", "brown", "magenta"]

screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.title("Кривая Коха — Оценка 9")
screen.tracer(0)

t = turtle.Turtle()
t.speed(0)
t.hideturtle()

hud = turtle.Turtle()
hud.hideturtle()
hud.penup()

segment_count = 0

def koch(t, length, n, depth):
    global segment_count
    if n == 0:
        t.pencolor(COLORS[depth % len(COLORS)])
        t.forward(length)
        segment_count += 1
    else:
        koch(t, length / 3, n - 1, depth + 1)
        t.left(60)
        koch(t, length / 3, n - 1, depth + 1)
        t.right(120)
        koch(t, length / 3, n - 1, depth + 1)
        t.left(60)
        koch(t, length / 3, n - 1, depth + 1)

def draw():
    global segment_count
    segment_count = 0
    t.clear()
    hud.clear()
    t.penup()
    t.goto(-300, 0)
    t.pendown()
    koch(t, 600, N, 0)
    hud.goto(0, 260)
    hud.color("darkblue")
    hud.write(f"Глубина N = {N}  |  Сегментов: {segment_count}  |  Клавиши + / -",
              align="center", font=("Arial", 13, "bold"))
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

screen.listen()
screen.onkey(increase, "Up")
screen.onkey(increase, "plus")
screen.onkey(increase, "=")
screen.onkey(decrease, "Down")
screen.onkey(decrease, "minus")
screen.onkey(decrease, "_")

draw()
turtle.mainloop()
