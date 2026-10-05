import turtle

t = turtle.Turtle()
t.speed(0)

screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.title("Кривая Коха — Оценка 5")

t.penup()
t.goto(-300, 0)
t.pendown()

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

koch(t, 600, 1)

turtle.mainloop()
