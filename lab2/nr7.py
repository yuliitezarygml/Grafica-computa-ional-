import turtle

N = int(input("Введите глубину рекурсии N (0-7): "))

t = turtle.Turtle()
t.speed(0)

screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.title(f"Кривая Коха — N={N}")
screen.tracer(0)

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

koch(t, 600, N)

screen.update()
turtle.mainloop()
