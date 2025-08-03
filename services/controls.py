from dotenv import load_dotenv
import asyncio
import os
import sys
import logging
import time
from datetime import datetime, timedelta
import pandas as pd
import json
from gpiozero import Button
from gpiozero.pins.pigpio import PiGPIOFactory
import requests
from scipy.integrate import trapezoid
from io import StringIO
import math
from statistics import mean

logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.INFO)

libdir = '/home/drux/demandResponse_UX_research/lib/helper_classes'
if os.path.exists(libdir):
    sys.path.append(libdir)

from KasaDRUX import KasaDRUX
from Airtable import Airtable
from DRUX import DRUX_Baseline, Helpers

load_dotenv()
un = os.getenv('KASA_UN')
pw = os.getenv('KASA_PW')
atKey = os.getenv('AIRTABLE')

if not un or not pw:
    logger.error("Missing KASA_UN or KASA_PW in environment.")
    raise EnvironmentError("Missing Kasa credentials")
if not atKey:
    logger.error("Missing Airtable key in environment.")
    raise EnvironmentError("Missing Airtable credentials")

kD = KasaDRUX(un,pw)
atEvents = Airtable(atKey,'apptjKq3GAr5CVOQT','events')
baseline = DRUX_Baseline()

try:
    repoRoot = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    with open(os.path.join(repoRoot,'config.json')) as f:
        config = json.load(f)
except Exception as e:
    logging.error(f"Error during reading config file: {e}")

csrpTime = int(config["csrp"])
logging.debug(f'CSRP start time is {csrpTime}')

# this should be initialized with all the state data!
buttonState = {}
held_triggered = False

#################
#### Helpers ####
#################

# returns a dictionary with either False or datetime values
def isCSRPEventUpcoming(df,t)-> dict:
    cState = {'now':False,'upcoming':False}

    csrpDF = df[df['type']=='csrp']
    for index, row in csrpDF.iterrows():
        csrpStartTime = row['date'].replace(hour=t)
        logging.debug(datetime.now()-csrpStartTime)
        if (datetime.now()-csrpStartTime < timedelta(hours=0)) and (datetime.now()-csrpStartTime >= timedelta(hours=-21)):
            logging.debug('CSRP event upcoming within 21 hours')
            cState['upcoming'] = csrpStartTime
        elif (datetime.now()-csrpStartTime > timedelta(hours=0)) and (datetime.now()-csrpStartTime <= timedelta(hours=4)):
            logging.debug('CSRP event ongoing!')
            cState['now'] = csrpStartTime

    return cState

# returns a dictionary with either False or datetime values
def isDLRPEventUpcoming(df)-> dict:
    dState = {'now':False,'upcoming':False}
    dlrpDF = df[df['type']=='dlrp']
    for index, row in dlrpDF.iterrows():
        dlrpStartTime = row['date'].replace(hour=int(row['time']))
        logging.debug(datetime.now()-dlrpStartTime)
        if (datetime.now()-dlrpStartTime < timedelta(hours=0)) and (datetime.now()-dlrpStartTime >= timedelta(hours=-2)):
            logging.debug('event upcoming within 2 hours')
            dState['upcoming'] = dlrpStartTime
        elif (datetime.now()-dlrpStartTime > timedelta(hours=0)) and (datetime.now()-dlrpStartTime <= timedelta(hours=4)):
            logging.debug('event ongoing')
            dState['now'] = dlrpStartTime

    return dState

async def saveState(d:dict):
    try:
        with open(os.path.join(repoRoot,'data/state.json'), "w") as json_file:
            json.dump(baseline.convert_datetimes(d), json_file, indent=4)
            logging.debug(f'State written to file. :)')
    except Exception as e:
        logging.error(f'Exception writing state to file: {e}')

async def sleeper(sec):
    logging.debug(f"Sleeping until button press or until {sec} seconds")

    try:
        #clear past presses
        button_event.is_set()
        #logging.debug("Already pressed")

        # await button_event.wait()
        button_event.clear()

        await asyncio.wait_for(button_event.wait(), timeout=sec)
        logging.debug("Woken up by button!")
    except asyncio.TimeoutError:
        logging.debug("Timed out — no button press.")
    except Exception as e:
        logging.debug(f'sleeper error: {e}')

async def send_get_request(ip:str='localhost', port:int=5000,endpoint:str='',type:str='json',timeout=1):
        """Send GET request to the IP."""
        # get own data
        max_tries = 3
        for attempt in range(max_tries):
            try:
                response = requests.get(f"http://{ip}:{port}/{endpoint}", timeout=timeout)
                response.raise_for_status()
                if type == 'json':
                    res= baseline.parse_datetimes(baseline.convert_bools(response.json()))
                elif type == 'text':
                    res= response.text
                else:
                    res= response.status_code
                break
            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP error occurred: {e}")
            except Exception as e:
                logging.error(f'{e}')
                if attempt == max_tries-1: # try up to 3 times
                    return None
                else:
                    logging.debug('SLEEEEEEEEEEEEEEEEEPING')
                    await asyncio.sleep(1+attempt)
        return res

async def logPerformance(d:dict):
    try:
        try:
            with open(os.path.join(repoRoot,'data/performance.json'), "r") as json_file_r:
                lp = json.load(json_file_r)
        except FileNotFoundError:
            lp = {}
        except json.JSONDecodeError:
            lp = {}
        d['modified']= datetime.now()
        cd = baseline.convert_datetimes(d)
        lp[cd['datetime']] = cd
        with open(os.path.join(repoRoot,'data/performance.json'), 'w') as json_file_w:
            json.dump(lp, json_file_w, indent=4)
            logging.info(f'Performance written to file. :)')
    except Exception as e:
        logging.error(f'Exception writing performance to file: {e}')

##############
#### Main ####
##############

async def main():
    global buttonState, button_event, stateDict, shortpresses,longpresses

    #sleep for 15 seconds to give API time to start
    await asyncio.sleep(15)

    #track button presses
    shortpresses = []
    longpresses = []

    # Event used to "wake up" the sleeping task
    button_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    # pause
    def on_press():
        global held_triggered
        held_triggered = datetime.now()

    def on_release():
        global held_triggered
        # Reset hold flag on release
        if datetime.now() - held_triggered <= timedelta(seconds=button.hold_time):
            buttonState['state']=True
            buttonState['datetime']=datetime.now()
            stateDict['eventPause']=buttonState
            shortpresses.append(datetime.now())
            loop.call_soon_threadsafe(button_event.set)
            logging.info(f'Button pressed! {buttonState}')
        else:
            buttonState['state']=False
            buttonState['datetime']=datetime.now()
            stateDict['eventPause']=buttonState
            longpresses.append(datetime.now())
            loop.call_soon_threadsafe(button_event.set)
            logging.info(f'Button held! {buttonState}')


    button = Button(26,hold_time=2.0,bounce_time=0.1)  # Debounce time in seconds
    button.when_pressed = on_press
    button.when_released = on_release

    # initialize state
    try:
        stateDict = await send_get_request(endpoint='api/state')
    except Exception as e:
        logging.error(f"Couldn't initialize state: {e}")
        stateDict={"csrp":{"baselineW":0,"baselineTS":False,"now":False,"upcoming":False,"avgPerf":100},
                    "dlrp":{"baselineW":0,"baselineTS":False,"now":False,"upcoming":False,"avgPerf":100},
                    "datetime":datetime.now(),
                    "eventPause":{"datetime":datetime.now(), "state":False},
                    "relays":{'bat-in':True,'bat-out':True,'ac':True}}
    try:
        eventDF = atEvents.parseListToDF(await atEvents.listRecords())
    except Exception as e:
        logging.error(e)

    try:
        #baseline.eventStartTime = csrpTime
        #csrpBaseline=await getBaseline(eventDF,csrpTime,'csrp')
        csrpBaseline = await baseline.getCBL(eventDF,csrpTime)
        csrpBaselineTS = datetime.now()
    except Exception as e:
        try:
            csrpBaseline = stateDict['csrp']['baselineW']
        except:
            csrpBaseline = 0
        logging.error(e)

    #dlrpUpdated = False

    while True:
        buttonTracker={'onPause':shortpresses,'offPause':longpresses}

        # get event status from Airtable
        try:
            #if not eventDF:# conditional only needed to not call this twice at the start of the program
            eventDF = atEvents.parseListToDF(await atEvents.listRecords())
            # check for events
            eventCSRP = isCSRPEventUpcoming(eventDF,csrpTime)
            eventCSRP['baselineW']=csrpBaseline
            if csrpBaselineTS:
                eventCSRP['baselineTS']=csrpBaselineTS
            else:
                eventCSRP['baselineTS']=False

            if (eventCSRP['now']):
                await logPerformance(await baseline.getOngoingPerformance(csrpTime,'csrp',eventCSRP['baselineW'],buttonTracker))

            eventDLRP = isDLRPEventUpcoming(eventDF)
            # update DLRP baseline if needed
            if (eventDLRP['upcoming']):
                if (not 'baselineTS' in eventDLRP.keys()) or (eventDLRP['baselineTS'] != eventDLRP['upcoming']):
                    #eventDLRP['baselineW']=await getBaseline(eventDF,eventDLRP['upcoming'].time().hour,'dlrp')
                    eventDLRP['baselineW']=await baseline.getCBL(eventDF,eventDLRP['upcoming'].time().hour)
                    eventDLRP['baselineTS'] = eventDLRP['upcoming']
                    #dlrpUpdated = True
            elif (eventDLRP['now']):
                if (not 'baselineTS' in eventDLRP.keys()) or (eventDLRP['baselineTS'] != eventDLRP['now']):
                    #eventDLRP['baselineW']=await getBaseline(eventDF,eventDLRP['now'].time().hour,'dlrp')
                    eventDLRP['baselineW']=await baseline.getCBL(eventDF,eventDLRP['now'].time().hour)
                    eventDLRP['baselineTS'] = eventDLRP['now']
                    await logPerformance(await baseline.getOngoingPerformance(eventDLRP['now'].time().hour,'dlrp',eventDLRP['baselineW'],buttonTracker))
            else:
                try:
                    eventDLRP['baselineW']=stateDict['dlrp']['baselineW']
                except:
                    eventDLRP['baselineW']=0
            stateDict['datetime'] = datetime.now()
            stateDict['csrp']=eventCSRP
            stateDict['dlrp']=eventDLRP
            logging.debug(stateDict)

            # reset eventDF
            #eventDF = None
        except Exception as e:
            logging.error(f"Couldn't check event status: {e}")

        # if paused
        if stateDict['eventPause']['state']:
            #if eventPause has been going on for an hour or more, unpause it
            if datetime.now()-stateDict['eventPause']['datetime'] > timedelta(hours=1):
                # unpause
                stateDict['eventPause']={'state':False,'datetime':datetime.now()}
                logging.debug(f"unpausing!: {stateDict['eventPause']}")

            # if event no longer going on, unpause it
            if (not stateDict['csrp']['now']) and (not stateDict['dlrp']['now']):
                stateDict['eventPause']={'state':False,'datetime':datetime.now()}

        #save state before
        #await saveState(stateDict)

        # respond to event status as needed
        if ((eventCSRP['now']) or (eventDLRP['now'])) and (not stateDict['eventPause']['state']):
            # check that event is still going on...
            logging.debug('EVENT NOW!')
            await kD.setEventState()
            stateDict['relays']= {'bat-in':False,'bat-out':True,'ac':False}
        elif ((eventCSRP['upcoming']) or (eventDLRP['upcoming'])) :
            #if true, battery can discharge during prep state (add indicator for battery ok to use)
            # keep battery charged!
            logging.debug('EVENT UPCOMING!')
            await kD.setPrepState(True)
            stateDict['relays']= {'bat-in':True,'bat-out':True,'ac':True}
        elif stateDict['eventPause']['state']:
            await kD.setPauseState(True) #should it be in normal state when paused?
            stateDict['relays']= {'bat-in':False,'bat-out':True,'ac':True}
        else:
            await kD.setNormalState()
            stateDict['relays']= {'bat-in':True,'bat-out':True,'ac':True}

        #save state
        await saveState(stateDict)

        await sleeper(5*60)
        await asyncio.sleep(.1) # may not be necessary

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Main loop crashed: {e}")
