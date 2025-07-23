#!/usr/bin/python
import time

##################
#### METHOD 1B ####
##################

# button between GPIO26 and Gnd
from gpiozero import Button

button = Button(26)

while True:
    button.wait_for_press()
    print('You pushed me')
    time.sleep(1)

##################
#### METHOD 1B ####
##################
# from gpiozero import Button

# button = Button(26)

# butVal = {'s':False}

# def on_press():
#     print("Button pressed!")
#     butVal['s']=True

# button.when_pressed = on_press

# while True:
#     if not butVal['s']:
#         print("Waiting for button press...")
#     time.sleep(1)

##################
#### METHOD 2 ####
##################

# import pigpio

# BUTTON_PIN = 17  # BCM pin

# def button_callback(gpio, level, tick):
#     if level == 0:
#         print("Button pressed!")

# pi = pigpio.pi()
# if not pi.connected:
#     exit(1)

# # Set pin as input with pull-up resistor
# pi.set_mode(BUTTON_PIN, pigpio.INPUT)
# pi.set_pull_up_down(BUTTON_PIN, pigpio.PUD_UP)

# # Register a falling edge callback (button press)
# cb = pi.callback(BUTTON_PIN, pigpio.FALLING_EDGE, button_callback)

# try:
#     print("Waiting for button press. Press CTRL+C to exit.")
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     print("Exiting...")
# finally:
#     cb.cancel()
#     pi.stop()

##################
#### METHOD 3 ####
##################
# RPi.GPIO only works with sudo
# import RPi.GPIO as GPIO

# # Use BCM pin numbering
# GPIO.setmode(GPIO.BCM)

# BUTTON_PIN = 26
# GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# def button_pressed_callback(channel):
#     print("Button was pressed!")

# # Add event listener on falling edge
# GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=button_pressed_callback, bouncetime=200)

# try:
#     print("Waiting for button press. Press CTRL+C to exit.")
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     print("Exiting...")
# finally:
#     GPIO.cleanup()

