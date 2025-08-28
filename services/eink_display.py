#!/usr/bin/python

# https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT+
# https://github.com/waveshareteam/e-Paper/tree/master/RaspberryPi_JetsonNano/python
# pillow: https://pillow.readthedocs.io/en/latest/index.html
# pillow text anchors:  https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html

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
import netifaces
import random

# picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'assets')
# libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
picdir = '/home/drux/demandResponse_UX_research/assets'
libdir = '/home/drux/demandResponse_UX_research/lib'

if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in13_V4

#logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.INFO)
logging.basicConfig(filename='/home/drux/demandResponse_UX_research/logs/display.log',format='%(asctime)s - %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',datefmt='%Y-%m-%d %H:%M:%S',level=logging.INFO)

logging.info("DR Display")

epd = epd2in13_V4.EPD()

# flip the screen for landscape mode
screenWidth = epd.height
screenHeight = epd.width
print(f'W={screenWidth}, H={screenHeight}')

try:
    repoRoot = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    with open(os.path.join(repoRoot,'config.json')) as f:
        config = json.load(f)
except Exception as e:
    logging.error(f"Error during reading config file: {e}")

csrpRate = config['csrpRatekW']
dlrpRate = config['dlrpRatekW']

dayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

###############
### Helpers ###
###############

async def send_get_request(ip:str='localhost', port:int=5000,endpoint:str='',type:str='json',timeout=1):
        """Send GET request to the IP."""
        # get own data
        max_tries = 3
        fullURL = f"http://{ip}:{port}/{endpoint}"
        #logging.debug(f'full url: {fullURL}')
        for attempt in range(max_tries):
            try:
                response = requests.get(fullURL, timeout=timeout)
                response.raise_for_status()

                if type == 'json':
                    res= parse_datetimes(convert_bools(response.json()))
                elif type == 'text':
                    res= response.text
                else:
                    res= response.status_code
                break
            except Exception as e:
                logging.error(f'{e}')
                if type == 'code':
                    return None

                if attempt == max_tries-1: # try up to 3 times
                    return None
                else:
                    logging.debug('SLEEEEEEEEEEEEEEEEEPING')
                    await asyncio.sleep(1+attempt)
        return res


def get_wlan0_ip():
    try:
        # Get addresses for the 'wlan0' interface
        addresses = netifaces.ifaddresses('wlan0')

        # Check if IPv4 addresses exist for wlan0
        if netifaces.AF_INET in addresses:
            # Extract the IP address from the list of IPv4 addresses
            ipv4_addresses = addresses[netifaces.AF_INET]
            if ipv4_addresses:
                return ipv4_addresses[0]['addr']
            else:
                return "No IPv4 address found for wlan0."
        else:
            return "wlan0 interface found, but no IPv4 address assigned."
    except ValueError:
        return "wlan0 interface not found or not configured."
    except Exception as e:
        return f"An error occurred: {e}"

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

def timeRemainingStr(endDT):
    tRemain = endDT - datetime.now()
    #tRemainH, remainder = divmod(td.seconds, 3600)
    tRmin = (tRemain.seconds//60)%60
    if tRmin < 10:
        tRminStr = f'0{tRmin}'
    else:
        tRminStr = f'{tRmin}'

    tRemainStr =  f'{tRemain.seconds//3600}:{tRminStr}'

    return tRemainStr


# convert to datetimes from iso formatted strings
def parse_datetimes(obj):
    if isinstance(obj, dict):
        return {k: parse_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [parse_datetimes(i) for i in obj]
    elif isinstance(obj, str):
        try:
            return datetime.fromisoformat(obj)
        except ValueError:
            return obj
    else:
        return obj

# args: old state, new state
def stateUpdate(o, n)-> bool:
    u = False

    if o['csrp']['now'] != n['csrp']['now']:
        return True
    if o['dlrp']['now'] != n['dlrp']['now']:
        return True
    if o['csrp']['upcoming'] != n['csrp']['upcoming']:
        return True
    if o['dlrp']['upcoming'] != n['dlrp']['upcoming']:
        return True
    if o['eventPause']['state'] != n['eventPause']['state']:
        return True
    return u

async def getPerformance():
    # check for today's performance
    todaysPerformance = {"goalAvg":0} # if using other keys in the screen functions, include them here as defaults
    try:
        performance = await send_get_request(endpoint='api/performance')
        for k in performance.keys():
            if datetime.today().strftime("%Y-%m-%d") == k.split('T')[0]:
                todaysPerformance = performance[k]
                break
        return todaysPerformance
    except:
        return todaysPerformance

async def startCheck():
    #stagger the start randomlly
    await asyncio.sleep(random.randint(0,60))

    count = 0
    while True:
        try:
            rCode = await send_get_request(endpoint='api/discover',type='code')
            logging.info(rCode)
            if rCode == 200:
                return None
        except Exception as e:
            logging.error(e)
        logging.info('still waiting!')
        count = count + 1

        await asyncio.sleep(20+(count**2))

###############
### Screens ###
###############

# args: draw object, string to test, initial font size,width of space
# returns font
def checkTextWidth(drawObj,s:str,f:int,w:int):
    fc = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), f)
    if drawObj.textlength(s, fc) > w:
        while True:
            f -= 1
            print(f)
            fc = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), f)
            if drawObj.textlength(s, fc) <= w:
                return fc
                break
    return fc

def upcomingScreen(f,s=None,p=None):
    estPay = s['csrp']['monthlyVal'] + s['dlrp']['monthlyVal']
    estPay = round(estPay,2)

    try:
        perc = 0
        c = 0
        if s['csrp']['count']>0:
            perc = s['csrp']['goalAvg']
            c = c + 1
        if s['dlrp']['count']>0:
            perc = perc + s['dlrp']['goalAvg']
            c = c + 1

        if c == 2:
            perc = perc *.5
        perc = min(1,perc)
    except:
        perc = 0

    try:
        if s['csrp']['upcoming']:
            bMin = min(s['csrp']['baselineW'])
            bMax = max(s['csrp']['baselineW'])
        elif s['dlrp']['upcoming']:
            bMin = min(s['dlrp']['baselineW'])
            bMax = max(s['dlrp']['baselineW'])
    except:
        bMin = 0
        bMax = 0

    if s['csrp']['upcoming']:
        eTime = s['csrp']['upcoming']#.strftime("%I:%M %p")
    elif s['dlrp']['upcoming']:
        eTime = s['dlrp']['upcoming']#.strftime("%I:%M %p")

    soon = False
    if eTime - datetime.now() < timedelta(hours=1):
        soon = True


    eDate = dayNames[eTime.weekday()]

    sImage = Image.new('1', (screenWidth,screenHeight), 255)
    sDraw = ImageDraw.Draw(sImage)
    epd.displayPartBaseImage(epd.getbuffer(sImage))

    ftSize = 17
    ft = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), ftSize)

    sDraw.rectangle((0,0,screenWidth,screenHeight), fill = 255)
    if not soon:
        sDraw.text((screenWidth/2, 3), f'Event upcoming at\n{eTime.strftime("%I:%M %p")} on {eDate}!', align="center",anchor='ma',font = ft, fill = 0)
    else:
        sDraw.text((screenWidth/2, 3), f'Event upcoming at {eTime.strftime("%I:%M %p")}\nPrecool to maximize comfort!', align="center",anchor='ma',font = ft, fill = 0)

    # bottom
    sDraw.rectangle((0,(screenHeight/2)-10,screenWidth,screenHeight), fill = 255)

    if (not s):# or (not p):
        sDraw.text((screenWidth/2, screenHeight/2), f'Data Missing :(', font = f, anchor="ma",fill = 0)
        epd.displayPartial(epd.getbuffer(sImage))
        return None

    hOffset = 2

    # performance
    bottomVtop = (screenHeight/2)-10
    bottomVmid = bottomVtop + ((screenHeight - bottomVtop) * .5)
    fs = checkTextWidth(sDraw,"Your Avg.",ftSize,screenWidth/3)
    sDraw.text((hOffset, bottomVmid), f'Network\nPerf.:\n{round(perc*100,1)}%', font = fs, anchor="lm", fill = 0)

    try:
        maxPay = estPay / perc
    except:
        maxPay = 0

    fs = checkTextWidth(sDraw,f"max: {round(bMax,1)}W",ftSize,screenWidth/3)
    sDraw.text(((2*screenWidth/3)+hOffset, bottomVmid), f'Baseline\nmin: {round(bMin,1)}W\nmax: {round(bMax,1)}W', font = fs, anchor="lm", fill = 0)

    # # baseline
    # sDraw.line([((screenWidth/3),screenHeight/2),((screenWidth/3),screenHeight)], fill=0,width=1, joint=None)
    # avgBase = 378
    # sDraw.text(((screenWidth/3)+hOffset,screenHeight/2), f'Average\nBaseline:\n{avgBase}W', font = f, anchor="la",fill = 0)

    # payment
    fs = checkTextWidth(sDraw,f"Estimated",ftSize,screenWidth/3)
    sDraw.text(((screenWidth/3)+hOffset, bottomVmid), f'Estimated\nPay:\n${round(estPay,2)}/m', font = fs, anchor="lm",fill = 0)

    sDraw.line([(0,bottomVtop),(screenWidth,bottomVtop)], fill=0,width=2, joint=None)
    sDraw.line([((screenWidth/3),bottomVtop),(screenWidth/3,screenHeight)], fill=0,width=1, joint=None)
    sDraw.line([((2*screenWidth/3),bottomVtop),(2*screenWidth/3,screenHeight)], fill=0,width=1, joint=None)

    epd.displayPartial(epd.getbuffer(sImage))

def eventScreen(f,s, p,paused=False):
    try:
        estPay = s['csrp']['monthlyVal'] + s['dlrp']['monthlyVal']
        estPay = round(estPay,2)
    except:
        estPay = 0

    # your performance percentage
    try:
        perc = min(1,p['goalAvg'])
    except:
        perc = 0

    # network performance percentage - MAKE THIS REALTIME!
    try:
        if s['csrp']['now']:
            percN = 0.595 #min(1,perc*1.05) # update this!
        else:
            percN = 0.3375
    except:
        percN = 0

    # elapsed time percentage
    try:
        et = datetime.now() - p['datetime']  #elapsed  time
        percT = min(1,(et.seconds/60)/ (4*60))

        eventEnd = p['datetime']+timedelta(hours=4)
        eventEndStr = eventEnd.strftime("%I:%M %p")

        tRemainStr = timeRemainingStr(eventEnd)
    except:
        percT = 0
        eventEndStr = '???'
        tRemainStr = '???'

    circRad = .9 * screenHeight/3
    centerY = screenHeight - (screenHeight/3)-22

    sImage = Image.new('1', (screenWidth,screenHeight), 255)
    sDraw = ImageDraw.Draw(sImage)
    epd.displayPartBaseImage(epd.getbuffer(sImage))

    if paused:
        logging.debug(type(s['eventPause']['datetime']))
        endPause = s['eventPause']['datetime']+timedelta(hours=1)
        endPauseStr = endPause.strftime("%I:%M %p")

        ft = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 17)
        sDraw.rectangle((0,0, screenWidth,screenHeight), fill = 255)
        #sDraw.text((screenWidth/2, 3), f"EVENT NOW UNTIL {eventEndStr}!", font = ft,anchor="mt",fill = 0)
        sDraw.text((screenWidth/2, 3), f"Event paused until {endPauseStr}!", font = ft,anchor="mt",fill = 0)
    else:
        ft = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 17)
        sDraw.rectangle((0,0, screenWidth,screenHeight), fill = 255)
        sDraw.text((screenWidth/2, 3), f"EVENT NOW UNTIL {eventEndStr}!", font = ft,anchor="mt",fill = 0)

    # money
    centerX = 1
    sDraw.text((centerX,centerY-circRad+3), f"Est. Value\n${round(estPay,2)}/m", font = f,  anchor="la",fill = 0)

    # time remaining
    sDraw.text((centerX,centerY+circRad), f"{tRemainStr}\nTime Left", font = f,  anchor="lm",fill = 0)


    # your goal
    centerX = 2*screenWidth/3  - (screenWidth/6) - 6
    sDraw.circle((centerX,centerY),circRad,fill=255, outline=0,width=1)
    sDraw.pieslice((centerX-circRad,centerY-circRad,centerX+circRad,centerY+circRad), 0-90, int(360*max(perc,0))-90,fill=0)
    sDraw.circle((centerX,centerY),circRad*.5,fill=255, outline=0,width=1)
    sDraw.text((centerX,centerY), f"{int(perc*100)}", font = f,  anchor="mm",fill = 0)
    sDraw.text((centerX,centerY+circRad+2), f"Your Goal", font = f,  anchor="ma",fill = 0)

    # network avg
    centerX = 3*screenWidth/3 - (screenWidth/6) -2
    sDraw.circle((centerX,centerY),circRad,fill=255, outline=0,width=1)
    sDraw.pieslice((centerX-circRad,centerY-circRad,centerX+circRad,centerY+circRad), -90, int(360*max(percN,0))-90,fill=0)
    sDraw.circle((centerX,centerY),circRad*.5,fill=255, outline=0,width=1)
    sDraw.text((centerX-1 ,centerY), f"{int(percN*100)}%", font = f,  anchor="mm",fill = 0)
    sDraw.text((centerX,centerY+circRad+2), f"Network Avg", font = f,  anchor="ma",fill = 0)

    epd.displayPartial(epd.getbuffer(sImage))

def normalScreen(f,w=None,s=None,p=None):
    try:
        estPay = s['csrp']['monthlyVal'] + s['dlrp']['monthlyVal']
        estPay = round(estPay,2)
    except:
        sDraw.text((screenHeight/2, screenHeight/2), f'Data Missing :(', font = f, anchor="ma",fill = 0)
        epd.displayPartial(epd.getbuffer(sImage))
        return None

    try:
        perc = 0
        c = 0
        if s['csrp']['count']>0:
            perc = s['csrp']['goalAvg']
            c = c + 1
        if s['dlrp']['count']>0:
            perc = perc + s['dlrp']['goalAvg']
            c = c + 1

        if c == 2:
            perc = perc *.5
        perc = min(1,perc)
    except:
        perc = 0

    # display IP and hostname on start up
    sImage = Image.new('1', (screenWidth,screenHeight), 255)
    sDraw = ImageDraw.Draw(sImage)
    epd.displayPartBaseImage(epd.getbuffer(sImage))

    # top
    ft = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 17)
    sDraw.rectangle((0,0, screenWidth,screenHeight/2), fill = 255)
    sDraw.text((screenWidth/2,0), f'No upcoming events', anchor='ma',font = ft, fill = 0)

    sDraw.text((screenWidth/2,28), f'AC power draw: {round(w,2)}W', anchor='ma',font = f, fill = 0)

    # bottom
    sDraw.rectangle((0,(screenHeight/2)-10,screenWidth,screenHeight), fill = 255)

    if not w:
        if w != 0:
            sDraw.text((screenHeight/2, screenHeight/2), f'Data Missing :(', font = f, anchor="ma",fill = 0)
            epd.displayPartial(epd.getbuffer(sImage))
            return None

    hOffset = 2
    # performance
    fs = ft #could make f none if not actually using it
    if sDraw.textlength("Performance:", ft) > screenWidth/2:
        fontSize = 17
        while True:
            fontSize -= 1
            print(fontSize)
            fs = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), fontSize)
            if sDraw.textlength("Performance:", fs) <= screenWidth/2:
                break

    bottomVtop = (screenHeight/2)-10
    bottomVmid = bottomVtop + ((screenHeight - bottomVtop) * .5)
    sDraw.text((hOffset, bottomVmid), f'Your Average\nPerformance:\n{round(perc*100,2)}%', font = fs, anchor="lm", fill = 0)

    # # baseline
    # sDraw.line([((screenWidth/3),screenHeight/2),((screenWidth/3),screenHeight)], fill=0,width=1, joint=None)
    # avgBase = 378
    # sDraw.text(((screenWidth/3)+hOffset,screenHeight/2), f'Average\nBaseline:\n{avgBase}W', font = f, anchor="la",fill = 0)

    # payment
    sDraw.text(((screenWidth/2)+hOffset, bottomVmid), f'Estimated\nPayment:\n${round(estPay,2)}/m', font = fs, anchor="lm",fill = 0)

    sDraw.line([(0,bottomVtop),(screenWidth,bottomVtop)], fill=0,width=2, joint=None)
    sDraw.line([((screenWidth/2),bottomVtop),(screenWidth/2,screenHeight)], fill=0,width=1, joint=None)
    epd.displayPartial(epd.getbuffer(sImage))

async def displayIP(f):
    # display IP and hostname on start up
    ip_image = Image.new('1', (screenWidth,screenHeight), 255)
    ip_draw = ImageDraw.Draw(ip_image)
    epd.displayPartBaseImage(epd.getbuffer(ip_image))

    ip_draw.rectangle((10, 20, 220, 105), fill = 255)
    ip_draw.text((5, 5), f'Starting up...\n\nhost: {hostname}\nIP: {IPAddr}', font = f, fill = 0)
    epd.displayPartial(epd.getbuffer(ip_image))

    await asyncio.sleep(5)

    await startCheck() #needs to wait for the API to spin up before moving on

def fullRefresh():
    global epd
    epd = epd2in13_V4.EPD()
    epd.init()
    epd.Clear(0xFF)

async def main():
    global hostname, IPAddr, epd

    # delay start
    await asyncio.sleep(10)

    # either should work, but make sure to comment out the line
    #'127.0.1.1 HOSTNAME' from /etc/hosts
    try:
        hostname = socket.gethostname()
        IPAddr = get_wlan0_ip()
        #IPAddr = socket.gethostbyname(hostname)
        #IPAddr = socket.gethostbyname(socket.getfqdn())
    except Exception as e:
        IPAddr = f'IP unknown: {e}'
    logging.debug(IPAddr)

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

    try:
        power = await send_get_request(endpoint='api/data?date=now&source=plugs')
        state = await send_get_request(endpoint='api/state')
        todaysPerformance = await getPerformance()
    except Exception as e:
        logging.error(f"Can't get data: {e}")

    updateScreen = True

    while True:
        # set frequency based on event status
        if (state['csrp']['now'] or state['dlrp']['now']):
            freqSec = 30
        else:
            freqSec = 60 * 5

        if(datetime.now() - updateState> timedelta(seconds=freqSec)): #check state every 60 seconds
            oldState = state
            state = await send_get_request(endpoint='api/state')
            updateState = datetime.now()
            # update the screen if event status changes
            updateScreen = stateUpdate(oldState,state)

        #  get most recent data
        if(datetime.now() - updateData> timedelta(minutes=5)):
            power = await send_get_request(endpoint='api/data?date=now&source=plugs')
            updateScreen = True
            updateData = datetime.now()
            # state = await send_get_request(endpoint='api/state')
            # updateState = datetime.now()

        # tracks how many partial refreshes have occurred
        if num >= 3:
            num = 0
            fullRefresh()
            updateScreen = True

        try:
            if updateScreen:
                logging.debug('updating screen!')

                # if no event, wake up screen because it has been sleeping
                # this will ensure it is awake for the event
                #if (not state['csrp']['now']) and (not state['dlrp']['now']):
                # epd = epd2in13_V4.EPD()
                # epd.init()
                #fullRefresh()

                if state['eventPause']['state']:
                    if (not state['csrp']['now']) or (not state['dlrp']['now']):
                        # if paused and event is ongoing
                        eventScreen(font15,state,todaysPerformance,True)
                else:
                    if not state['csrp']['now']:
                        if not state['dlrp']['now']:
                            if not state['csrp']['upcoming']:
                                if not state['dlrp']['upcoming']:
                                    normalScreen(font15,w=power['ac-W'],s=state,p=todaysPerformance)
                                else:
                                    upcomingScreen(font15,state,todaysPerformance)
                            else:
                                upcomingScreen(font15,state,todaysPerformance)
                        else:
                            todaysPerformance = await getPerformance() #only bother updating when event is ongoing
                            eventScreen(font15,state,todaysPerformance)
                    else:
                        todaysPerformance = await getPerformance() #only bother updating when event is ongoing
                        eventScreen(font15,state,todaysPerformance)

                updateScreen = False
                num = num + 1
        except Exception as e:
            try:
                # exit loop if state unknown
                if not state:
                    logging.error(f'no state!')
                    normalScreen(font15,w=power['ac-W'],s=state,p=todaysPerformance)
                    num = num + 1
                else:
                    normalScreen(font15,w=power['ac-W'],s=state,p=todaysPerformance)
                    logging.error(e)
            except Exception as e:
                logging.error(e)
                normalScreen(font15,s=state,p=todaysPerformance)

        # full refresh should be greater than 3 minutes or after 3 partial refreshes
        updateScreen = False

        # if no event ongoing or upcoming, go to sleep
        # if (not state['csrp']['now']) and (not state['dlrp']['now']) and (not state['csrp']['upcoming']) and (not state['dlrp']['upcoming']):
        #     epd.sleep() # this seems to break for some reason :(

        await asyncio.sleep(30)

try:
    asyncio.run(main())
except IOError as e:
    logging.info(e)

except KeyboardInterrupt:
    logging.info("ctrl + c:")
    epd.init() # I added this to clear screen - not sure if necessary
    epd.Clear(0xFF) # I added this to clear screen - not sure if necessary
    epd2in13_V4.epdconfig.module_exit(cleanup=True)
    exit()
