#!/usr/bin/python
import time
##################
#### METHOD 1 ####
##################

# button between GPIO26 and Gnd
from gpiozero import Button

button = Button(26)

while True:
    button.wait_for_press()
    print('You pushed me')
    time.sleep(1)

##################
#### METHOD 2 ####
##################
# # 3.3V to 1K resistor to button
# # button to GPIO26
# import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
# def button_callback(channel):
#     print("Button was pushed!")

# GPIO.setwarnings(False) # Ignore warning for now
# GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
# GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
# GPIO.add_event_detect(10,GPIO.RISING,callback=button_callback) # Setup event on pin 10 rising edge

# # while True:
# #     if GPIO.input(10) == GPIO.HIGH:
# #         print("Button was pushed!")
# #     time.sleep(1)

# GPIO.cleanup() # Clean up
