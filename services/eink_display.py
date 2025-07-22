#!/usr/bin/python

# https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT+
# https://github.com/waveshareteam/e-Paper/tree/master/RaspberryPi_JetsonNano/python

import sys
import os
# picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'assets')
# libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
picdir = '/home/drux/demandResponse_UX_research/assets'
libdir = '/home/drux/demandResponse_UX_research/lib'

if os.path.exists(libdir):
    sys.path.append(libdir)

import logging
from waveshare_epd import epd2in13_V4
from datetime import datetime, timedelta
from PIL import Image,ImageDraw,ImageFont
import traceback
import socket
import time

logging.basicConfig(level=logging.DEBUG)

logging.info("DR Display")

epd = epd2in13_V4.EPD()

# flip the screen for landscape mode
screenWidth = epd.height
screenHeight = epd.width
print(f'W={screenWidth}, H={screenHeight}')

hostname = socket.gethostname()
#IPAddr = socket.gethostbyname(hostname)
IPAddr = socket.gethostbyname(socket.getfqdn())
print(IPAddr)

def upcomingScreen(font24):
    eTime = '4pm'
    eDate = 'August 1'

    # display IP and hostname on start up
    sImage = Image.new('1', (screenWidth,screenHeight), 255)
    sDraw = ImageDraw.Draw(sImage)
    epd.displayPartBaseImage(epd.getbuffer(sImage))

    sDraw.rectangle((50, 40, 220, 105), fill = 255)
    sDraw.text((50, 40), f'Event upcoming at {eTime} on {eDate}!', font = font24, fill = 0)
    epd.displayPartial(epd.getbuffer(sImage))

def eventScreen(f):

    # display IP and hostname on start up
    sImage = Image.new('1', (screenWidth,screenHeight), 255)
    sDraw = ImageDraw.Draw(sImage)
    epd.displayPartBaseImage(epd.getbuffer(sImage))

    sDraw.rectangle((0,0, screenWidth,screenHeight), fill = 255)
    sDraw.text((screenWidth, 10), f'Event now!!!', font = f,  anchor="mt",fill = 0)

    sDraw.rectangle((50,80), (screenWidth-50,screenHeight-80), fill = 255, outline=0)
    sDraw.rectangle((50,80), (screenWidth-50,screenHeight-100), fill = 0)
    epd.displayPartial(epd.getbuffer(sImage))

def normalScreen(f):

    # display IP and hostname on start up
    sImage = Image.new('1', (screenWidth,screenHeight), 255)
    sDraw = ImageDraw.Draw(sImage)
    epd.displayPartBaseImage(epd.getbuffer(sImage))

    # top
    sDraw.rectangle((0,0, screenWidth,screenHeight/2), fill = 255)
    sDraw.text((screenWidth/2,0), f'No event upcoming!', anchor='ma',font = f, fill = 0)

    # center of fan
    rad = 10
    fCenterX = (2*screenWidth/3)+rad
    fCenterY = (screenHeight/6)+rad
    sDraw.ellipse((fCenterX-rad,fCenterY-rad,fCenterX+rad,fCenterY+rad),fill=None, outline=0, width=3)

    # bottom
    sDraw.rectangle((0,screenHeight/2,screenWidth,screenHeight), fill = 255)

    hOffset = 2
    # performance
    avgPerf = 76
    fs = f
    if sDraw.textlength("Performance:", f) > screenWidth/3:
        fontSize = 15
        while True:
            fontSize -= 1
            print(fontSize)
            fs = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), fontSize)
            if sDraw.textlength("Performance:", fs) <= screenWidth/3:
                break

    sDraw.text((hOffset, screenHeight/2), f'Average\nPerformance:\n{avgPerf}%', font = fs, anchor="la", fill = 0)

    # baseline
    sDraw.line([((screenWidth/3),screenHeight/2),((screenWidth/3),screenHeight)], fill=0,width=1, joint=None)
    avgBase = 378
    sDraw.text(((screenWidth/3)+hOffset,screenHeight/2), f'Average\nBaseline:\n{avgBase}W', font = f, anchor="la",fill = 0)

    # payment
    sDraw.line([((2*screenWidth/3),screenHeight/2),((2*screenWidth/3),screenHeight)], fill=0,width=1, joint=None)
    estPay = 4.5
    sDraw.text(((2*screenWidth/3)+hOffset, screenHeight/2), f'Estimated\nPayment:\n${estPay}/m', font = f, anchor="la",fill = 0)

    sDraw.line([(0,screenHeight/2),(screenWidth,screenHeight/2)], fill=0,width=2, joint=None)
    epd.displayPartial(epd.getbuffer(sImage))

def displayIP(font24):
    # display IP and hostname on start up
    ip_image = Image.new('1', (screenWidth,screenHeight), 255)
    ip_draw = ImageDraw.Draw(ip_image)
    epd.displayPartBaseImage(epd.getbuffer(ip_image))

    ip_draw.rectangle((50, 40, 220, 105), fill = 255)
    ip_draw.text((50, 40), f'{hostname}\n{IPAddr}', font = font24, fill = 0)
    epd.displayPartial(epd.getbuffer(ip_image))
    time.sleep(15)

def main():

    logging.info("init and Clear")
    epd.init()
    epd.Clear(0xFF)

    # Drawing on the image - any TTF font should work
    font15 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15)
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)

    displayIP(font24)

    screenState = 0

    # full refresh loop (roughly every 180 minutes)
    while True:

        epd.init()
        epd.Clear(0xFF)

        logging.info("4.show time...")
        time_image = Image.new('1', (epd.height, epd.width), 255)
        time_draw = ImageDraw.Draw(time_image)
        epd.displayPartBaseImage(epd.getbuffer(time_image))
        num = 0 # partial refresh counter (should full refresh after every 3 partials)
        lastRefresh = datetime.now()

        #partical refresh loop
        updateScreen = True
        while True:
            myTime = datetime.now()
            if updateScreen:
                normalScreen(font15)
                updateScreen = False
                num = num + 1
            # full refresh should be greater than 3 minutes or after 3 partial refreshes
            time.sleep(1)
            if(myTime - lastRefresh> timedelta(minutes=5)) | (num>=3):
                break

try:
    main()
# except KeyboardInterrupt:
#     epd.init()
#     epd.Clear(0xFF)
#     epd.sleep()
# except:
#     epd.init()
#     epd.Clear(0xFF)
#     epd.sleep()
except IOError as e:
    logging.info(e)

except KeyboardInterrupt:
    logging.info("ctrl + c:")
    epd.init() # I added this to clear screen - not sure if necessary
    epd.Clear(0xFF) # I added this to clear screen - not sure if necessary
    epd2in13_V4.epdconfig.module_exit(cleanup=True)
    exit()
