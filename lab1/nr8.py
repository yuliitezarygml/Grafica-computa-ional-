import turtle
import math

screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.title("Лабораторная работа 1")

t = turtle.Turtle()
t.shape("turtle")
t.color("red")
t.pensize(3)
t.penup()

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

def clear_screen():
    t.clear()

def set_red():
    t.pencolor("red")

def set_blue():
    t.pencolor("blue")

def set_green():
    t.pencolor("green")

def set_yellow():
    t.pencolor("gold")

def set_black():
    t.pencolor("black")

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

screen.onkey(set_red, "1")
screen.onkey(set_blue, "2")
screen.onkey(set_green, "3")
screen.onkey(set_yellow, "4")
screen.onkey(set_black, "5")

screen.onkey(increase_width, "plus")
screen.onkey(increase_width, "=")
screen.onkey(decrease_width, "minus")
screen.onkey(decrease_width, "_")

turtle.mainloop()
