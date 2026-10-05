import turtle
import math

screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.title("Лабораторная работа 1")

current_color = "red"

t = turtle.Turtle()
t.shape("turtle")
t.color("gray")
t.pensize(3)
t.penup()

def update_turtle_color():
    if t.isdown():
        t.color(current_color)
    else:
        t.color("gray")

def move_forward():
    angle = math.radians(t.heading())
    new_x = t.xcor() + 30 * math.cos(angle)
    new_y = t.ycor() + 30 * math.sin(angle)
    if -380 <= new_x <= 380 and -280 <= new_y <= 280:
        t.goto(new_x, new_y)

def move_backward():
    angle = math.radians(t.heading())
    new_x = t.xcor() - 30 * math.cos(angle)
    new_y = t.ycor() - 30 * math.sin(angle)
    if -380 <= new_x <= 380 and -280 <= new_y <= 280:
        t.goto(new_x, new_y)

def turn_left():
    t.left(30)

def turn_right():
    t.right(30)

def toggle_pen():
    if t.isdown():
        t.penup()
    else:
        t.pendown()
        t.pencolor(current_color)
    update_turtle_color()

def clear_screen():
    t.clear()

def set_color(new_c):
    global current_color
    current_color = new_c
    if t.isdown():
        t.pencolor(current_color)
    update_turtle_color()

def increase_width():
    w = t.pensize() + 2
    if w <= 30:
        t.pensize(w)

def decrease_width():
    w = t.pensize() - 2
    if w >= 1:
        t.pensize(w)

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

turtle.mainloop()
