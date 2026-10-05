import turtle

screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.title("Лабораторная работа 1")

screen.register_shape("portrait_animated.gif")     # 1. register the image file
t = turtle.Turtle()
t.shape("portrait_animated.gif")                   # 2. use it as the turtle's shape

def move_forward():
    t.forward(30)

def move_backward():
    t.backward(30)

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

screen.listen()
screen.onkey(move_forward, "Up")
screen.onkey(move_backward, "Down")
screen.onkey(turn_left, "Left")
screen.onkey(turn_right, "Right")
screen.onkey(toggle_pen, "space")
screen.onkey(clear_screen, "c")
screen.onkey(clear_screen, "C")

turtle.mainloop()
