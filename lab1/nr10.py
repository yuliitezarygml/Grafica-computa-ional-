import turtle
import math

screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.title("Лабораторная работа 1")
screen.tracer(0)

wall = turtle.Turtle()
wall.hideturtle()
wall.penup()
wall.goto(-100, -100)
wall.pendown()
wall.color("blue", "#ffcccc")
wall.begin_fill()
for _ in range(2):
    wall.forward(200)
    wall.left(90)
    wall.forward(150)
    wall.left(90)
wall.end_fill()
wall.penup()
wall.goto(0, -35)
wall.color("darkred")
wall.write("ПРЕПЯТСТВИЕ\n(нельзя с хвостом)", align="center", font=("Arial", 11, "bold"))

hud = turtle.Turtle()
hud.hideturtle()
hud.penup()

errors = 0
msg = "Управление: Стрелки, Пробел, 1-5, +/-, C"

def update_hud():
    hud.clear()
    hud.goto(0, 260)
    hud.color("darkblue")
    hud.write(f"Ошибки: {errors} | {msg}", align="center", font=("Arial", 12, "bold"))
    screen.update()

current_color = "red"

t = turtle.Turtle()
t.shape("turtle")
t.turtlesize(2, 2)
t.color("gray")
t.pensize(3)
t.penup()

def update_turtle_color():
    if t.isdown():
        t.color(current_color)
    else:
        t.color("gray")

def in_obstacle(x, y):
    return -100 <= x <= 100 and -100 <= y <= 50

def move_forward():
    global errors, msg
    angle = math.radians(t.heading())
    new_x = t.xcor() + 30 * math.cos(angle)
    new_y = t.ycor() + 30 * math.sin(angle)
    if -380 <= new_x <= 380 and -280 <= new_y <= 240:
        if in_obstacle(new_x, new_y) and t.isdown():
            errors += 1
            msg = "ОШИБКА: Нельзя наезжать хвостом!"
            update_hud()
            return
        t.goto(new_x, new_y)
        msg = "Движение"
        update_hud()

def move_backward():
    global errors, msg
    angle = math.radians(t.heading())
    new_x = t.xcor() - 30 * math.cos(angle)
    new_y = t.ycor() - 30 * math.sin(angle)
    if -380 <= new_x <= 380 and -280 <= new_y <= 240:
        if in_obstacle(new_x, new_y) and t.isdown():
            errors += 1
            msg = "ОШИБКА: Нельзя наезжать хвостом!"
            update_hud()
            return
        t.goto(new_x, new_y)
        msg = "Движение"
        update_hud()

def turn_left():
    t.left(30)
    screen.update()

def turn_right():
    t.right(30)
    screen.update()

def toggle_pen():
    global errors, msg
    if t.isdown():
        t.penup()
        msg = "Хвост поднят"
    else:
        if in_obstacle(t.xcor(), t.ycor()):
            errors += 1
            msg = "ОШИБКА: Нельзя опускать хвост внутри препятствия!"
            update_hud()
            return
        t.pendown()
        t.pencolor(current_color)
        msg = "Хвост опущен"
    update_turtle_color()
    update_hud()

def clear_screen():
    global msg
    t.clear()
    msg = "Экран очищен"
    update_hud()

def set_color(new_c):
    global current_color, msg
    current_color = new_c
    if t.isdown():
        t.pencolor(current_color)
    update_turtle_color()
    msg = f"Цвет: {new_c}"
    update_hud()

def increase_width():
    w = t.pensize() + 2
    if w <= 30:
        t.pensize(w)
    update_hud()

def decrease_width():
    w = t.pensize() - 2
    if w >= 1:
        t.pensize(w)
    update_hud()

screen.listen()

screen.onkey(move_forward, "Up")
screen.onkey(move_backward, "Down")
screen.onkey(turn_left, "Left")
screen.onkey(turn_right, "Right")
screen.onkey(toggle_pen, "space")
screen.onkey(clear_screen, "c")
screen.onkey(clear_screen, "C")

screen.onkey(lambda: set_color("red"), "1")
screen.onkey(lambda: set_color("blue"), "2")
screen.onkey(lambda: set_color("green"), "3")
screen.onkey(lambda: set_color("gold"), "4")
screen.onkey(lambda: set_color("black"), "5")

screen.onkey(increase_width, "plus")
screen.onkey(increase_width, "=")
screen.onkey(decrease_width, "minus")
screen.onkey(decrease_width, "_")

update_turtle_color()
update_hud()

turtle.mainloop()
