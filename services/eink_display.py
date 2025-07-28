#!/usr/bin/python

# https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT+
# https://github.com/waveshareteam/e-Paper/tree/master/RaspberryPi_JetsonNano/python

import sys
import os
import logging
import traceback
import socket
import time
import requests
from datetime import datetime, timedelta
from PIL import Image,ImageDraw,ImageFont
import asyncio
import json

# picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'assets')
# libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
picdir = '/home/drux/demandResponse_UX_research/assets'
libdir = '/home/drux/demandResponse_UX_research/lib'

if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in13_V4

logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.DEBUG)

logging.info("DR Display")

epd = epd2in13_V4.EPD()

# flip the screen for landscape mode
screenWidth = epd.height
screenHeight = epd.width
print(f'W={screenWidth}, H={screenHeight}')

# either should work, but make sure to comment out the line
#'127.0.1.1 HOSTNAME' from /etc/hosts
hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)
#IPAddr = socket.gethostbyname(socket.getfqdn())
logging.debug(IPAddr)

try:
    repoRoot = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    with open(os.path.join(repoRoot,'config.json')) as f:
        config = json.load(f)
except Exception as e:
    logging.error(f"Error during reading config file: {e}")

csrpRate = config['csrpRatekW']
dlrpRate = config['dlrpRatekW']

async def send_get_request(ip:str='localhost', port:int=5000,endpoint:str='',type:str='json',timeout=1):
        """Send GET request to the IP."""
        # get own data
        max_tries = 3
        for attempt in range(max_tries):
            try:
                response = requests.get(f"http://{ip}:{port}/{endpoint}", timeout=timeout)
                response.raise_for_status()
                if type == 'json':
                    res= convert_bools(response.json())
                elif type == 'text':
                    res= response.text
                else:
                    res= response.status_code
                break
            except Exception as e:
                logging.error(f'{e}')
                if attempt == max_tries-1: # try up to 3 times
                    return None
                else:
                    logging.debug('SLEEEEEEEEEEEEEEEEEPING')
                    await asyncio.sleep(1+attempt)
        return res

# Function to recursively convert "true"/"false" strings to Booleans
def convert_bools(obj):
    if isinstance(obj, dict):
        return {k: convert_bools(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_bools(elem) for elem in obj]
    elif obj == "true":
        return True
    elif obj == "false":
        return False
    else:
        return obj

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

def eventScreen(f,s, p):

    # display IP and hostname on start up
    sImage = Image.new('1', (screenWidth,screenHeight), 255)
    sDraw = ImageDraw.Draw(sImage)
    epd.displayPartBaseImage(epd.getbuffer(sImage))

    sDraw.rectangle((0,0, screenWidth,screenHeight), fill = 255)
    sDraw.text((screenWidth, 10), f'Event now!!!', font = f,  anchor="mt",fill = 0)

    # money bar
    rStartX = 10
    rStartY = screenHeight/2
    rMargin = 3
    if p:
        perc = p['performancePerc']
    else:
        perc = 0

    rWidth = (screenWidth - 2 * rStartX) * perc
    rHeight = 20
    sDraw.text((rStartX+ rWidth+3, rStartY), f'Perf %', font = f,  anchor="lt",fill = 0)
    sDraw.rectangle((rStartX,rStartY,rStartX+ rWidth,rStartY+rHeight), fill = 255, outline=0)
    sDraw.rectangle((rStartX+rMargin,rStartY+rMargin,rStartX+(rWidth-2*rMargin),rStartY+(rHeight-2*rMargin)), fill = 0)

    # time bar
    rStartX = 10
    rMargin = 3
    if p:
        perc = p['performancePerc']
    else:
        perc = 0

    rWidthBorder = screenWidth - 2 * margin #* rStartX) * perc
    rWidthProgress = (rWidthBorder - 2 * margin) * perc
    rHeight = 20
    rStartY = (screenHeight/2) +(2* rMargin) + rHeight
    sDraw.text((rStartX+ rWidth+3, rStartY), f'Time', font = f,  anchor="lt",fill = 0)
    sDraw.rectangle((rStartX,rStartY,rStartX+ rWidthBorder,rStartY+rHeight), fill = 255, outline=0)
    sDraw.rectangle((rStartX+rMargin,rStartY+rMargin,rStartX+rWidthProgress,rStartY+rHeight-(2*rMargin)), fill = 0)

    epd.displayPartial(epd.getbuffer(sImage))

def eventPausedScreen(f,s,p):
    # display IP and hostname on start up
    sImage = Image.new('1', (screenWidth,screenHeight), 255)
    sDraw = ImageDraw.Draw(sImage)
    epd.displayPartBaseImage(epd.getbuffer(sImage))

    sDraw.rectangle((0,0, screenWidth,screenHeight), fill = 255)
    sDraw.text((screenWidth, 10), f'Event paused until...!!!', font = f,  anchor="mt",fill = 0)

    # money bar
    rStartX = 10
    rStartY = screenHeight/2
    rMargin = 3
    rWidth = screenWidth - 2 * rStartX
    rHeight = 20
    sDraw.rectangle((rStartX,rStartY,rStartX+ rWidth,rStartY+rHeight), fill = 255, outline=0)
    sDraw.rectangle((rStartX+rMargin,rStartY+rMargin,(rStartX+rWidth)-2*rMargin,(rStartY+rHeight)-2*rMargin), fill = 0)

    # time bar

    epd.displayPartial(epd.getbuffer(sImage))

def normalScreen(f,w=None):

    # display IP and hostname on start up
    sImage = Image.new('1', (screenWidth,screenHeight), 255)
    sDraw = ImageDraw.Draw(sImage)
    epd.displayPartBaseImage(epd.getbuffer(sImage))

    # top
    sDraw.rectangle((0,0, screenWidth,screenHeight/2), fill = 255)
    sDraw.text((screenWidth/2,0), f'No event upcoming!', anchor='ma',font = f, fill = 0)
    sDraw.text((screenWidth/2,screenHeight/4), f'AC power draw: {w}W', anchor='ma',font = f, fill = 0)

    # center of fan
    rad = 10
    fCenterX = (2*screenWidth/3)+rad
    fCenterY = (screenHeight/6)+rad
    sDraw.ellipse((fCenterX-rad,fCenterY-rad,fCenterX+rad,fCenterY+rad),fill=None, outline=0, width=3)

    # bottom
    sDraw.rectangle((0,screenHeight/2,screenWidth,screenHeight), fill = 255)

    if w:
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
    else:
        sDraw.text((10, screenHeight/2), f'data missing', font = f, anchor="ma",fill = 0)
    epd.displayPartial(epd.getbuffer(sImage))

async def displayIP(font24):
    # display IP and hostname on start up
    ip_image = Image.new('1', (screenWidth,screenHeight), 255)
    ip_draw = ImageDraw.Draw(ip_image)
    epd.displayPartBaseImage(epd.getbuffer(ip_image))

    ip_draw.rectangle((50, 40, 220, 105), fill = 255)
    ip_draw.text((50, 40), f'{hostname}\n{IPAddr}', font = font24, fill = 0)
    epd.displayPartial(epd.getbuffer(ip_image))
    asyncio.sleep(15) #needs to wait for the API to spin up before moving on

def fullRefresh():
    epd.init()
    epd.Clear(0xFF)

async def main():

    logging.info("init and Clear")
    fullRefresh()

    # Drawing on the image - any TTF font should work
    font15 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 15)
    font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)

    await displayIP(font24)

    num = 0 # partial refresh counter (should full refresh after every 3 partials)
    lastRefresh = datetime.now()
    updateData = datetime.now() # will get updated every 5 minutes
    updateState = datetime.now() # will get updated every 30 seconds

    power = await send_get_request(endpoint='api/data?date=now&source=plugs')
    battery = await send_get_request(endpoint='api/data?date=now&source=powerstation')
    state = await send_get_request(endpoint='api/state')

    # if (state['csrp']['now']) or (state['csrp']['now']):
    #     logging.debug('event is ongoing!')
    performance = await send_get_request(endpoint='api/performance')

    # check for today's performance
    todaysPerformance = None
    for k in performance.keys():
        if datetime.today().strftime("%Y-%m-%d") in k:
            todaysPerformance = performance[k]

    updateScreen = True

    while True:
        #  get most recent data
        if(datetime.now() - updateData> timedelta(minutes=5)):
            power = await send_get_request(endpoint='api/data?date=now&source=plugs')
            battery = await send_get_request(endpoint='api/data?date=now&source=powerstation')
            updateScreen = True
            updateData = datetime.now()
        if(datetime.now() - updateState> timedelta(seconds=10)):
            oldState = state
            state = await send_get_request(endpoint='api/state')
            updateState = datetime.now()
            if oldState != state:
                updateScreen = True

        if num >= 3:
            num = 0
            fullrefresh()

        try:
            if updateScreen:
                if state['eventPause']['state']:
                    if (not state['csrp']['now']) or (not state['dlrp']['now']):
                        # if paused and event is ongoing
                        eventPausedScreen(font15)
                else:
                    if not state['csrp']['now']:
                        if not state['dlrp']['now']:
                            if not state['csrp']['upcoming']:
                                if not state['dlrp']['upcoming']:
                                    normalScreen(font15,power['ac-W'])
                                else:
                                    upcomingScreen(font15)
                            else:
                                upcomingScreen(font15)
                        else:
                            eventScreen(font15,state,todaysPerformance)
                    else:
                        eventScreen(font15,state,todaysPerformance)

                updateScreen = False
                num = num + 1
        except Exception as e:
            try:
                # exit loop if state unknown
                if not state:
                    logging.error(f'no state!')
                    normalScreen(font15)
                    num = num + 1
                else:
                    logging.error(e)
            except Exception as e:
                logging.error(e)

        # full refresh should be greater than 3 minutes or after 3 partial refreshes
        updateScreen = False
        asyncio.sleep(1)

try:
    #main()
    asyncio.run(main())
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
