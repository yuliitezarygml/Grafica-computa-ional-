import turtle

screen = turtle.Screen()
screen.setup(width=800, height=600)
screen.title("Лабораторная работа 1")

t = turtle.Turtle()
t.color("red")
t.shape("square")
t.penup()

def move_forward():
    t.forward(30)

def move_backward():
    t.backward(30)

def pen_down():
    t.pendown()

screen.listen()
screen.onkey(move_forward, "Up")
screen.onkey(move_backward, "Down")
screen.onkey(pen_down, "space")

turtle.mainloop()