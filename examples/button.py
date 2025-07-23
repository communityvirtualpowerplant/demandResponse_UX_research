#!/usr/bin/python

# no 1KR

# button between GPIO2 and Vcc
 from gpiozero import Button

button = Button(2)

button.wait_for_press()

print('You pushed me')
