import turtle

N = 2
MAX_N = 7

screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.title("Кривая Коха — Оценка 8")
screen.tracer(0)

t = turtle.Turtle()
t.speed(0)
t.hideturtle()

hud = turtle.Turtle()
hud.hideturtle()
hud.penup()

def koch(t, length, n):
    if n == 0:
        t.forward(length)
    else:
        koch(t, length / 3, n - 1)
        t.left(60)
        koch(t, length / 3, n - 1)
        t.right(120)
        koch(t, length / 3, n - 1)
        t.left(60)
        koch(t, length / 3, n - 1)

def draw():
    t.clear()
    hud.clear()
    t.penup()
    t.goto(-300, 0)
    t.pendown()
    koch(t, 600, N)
    hud.goto(0, 260)
    hud.color("darkblue")
    hud.write(f"Глубина N = {N}   (Клавиши + / - для изменения, макс = {MAX_N})",
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
