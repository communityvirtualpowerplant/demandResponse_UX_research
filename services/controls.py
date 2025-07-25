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

##########################
#### Helper Functions ####
##########################

def calcBaseline(st):
    return None

# returns a dictionary with either False or datetime values
def isCSRPEventUpcoming(df,t)-> dict:
    cState = {'now':False,'upcoming':False,'baselineW':0}

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

    #cState['baselineW']=calcBaseline(csrpStartTime)
    return cState

# returns a dictionary with either False or datetime values
def isDLRPEventUpcoming(df)-> dict:
    dState = {'now':False,'upcoming':False,'baselineW':0}
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

    #dState['baselineW']=calcBaseline(dlrpStartTime)
    return dState

# convert datetimes to iso formatted strings
def convert_datetimes(obj):
    if isinstance(obj, dict):
        return {k: convert_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetimes(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

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

def saveState(d:dict):
    try:
        with open(os.path.join(repoRoot,'services/state.json'), "w") as json_file:
            json.dump(convert_datetimes(d), json_file, indent=4)
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

async def send_get_request(ip:str='localhost', port:int=5000,endpoint:str='',type:str='json',timeout=1):
        """Send GET request to the IP."""
        # get own data
        max_tries = 3
        for attempt in range(max_tries):
            try:
                response = requests.get(f"http://{ip}:{port}/{endpoint}", timeout=timeout)
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
                if attempt == max_tries-1: # try up to 3 times
                    return None
                else:
                    logging.debug('SLEEEEEEEEEEEEEEEEEPING')
                    await asyncio.sleep(1+attempt)
        return res

# # its dumb to have both of these request functions!
# async def send_secure_get_request(url:str,key:str=None,type:str='json',timeout=2):
#     """Send GET request to the IP."""
#     try:
#         headers = {"Content-Type": "application/json; charset=utf-8"}

#         if key:
#             headers = {"Authorization": f"Bearer {key}"}
#         else:
#             heads = {}

#         response = requests.get(url, headers=headers, timeout=timeout)
#         if type == 'json':
#             return response.json()
#         elif type == 'text':
#             return (response.text, response.status_code)
#         else:
#             return response.status_code
#     except requests.Timeout as e:
#         return e
#     except Exception as e:
#         return e

####################
### get baseline ###
####################

# currently only works with eTime as ints (whole hours)
#args: event type, event log df
async def getBaseline(eType:str,eDF:pd.DataFrame,eTime:float):
    # drop unnecessary columns
    eType = eType.drop(columns=['modified','notes','network'])

    # filter to only past events
    pastEventsDF=eType[eType['date']<datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)]

    # get file list
    fileList = await send_get_request(endpoint='api/files?source=plugs')
    logging.debug(fileList)

    # retrieve files
    data = []
    for f in fileList:
        if datetime.now().date().strftime("%Y-%m-%d")  not in f:
            d = f.replace('.csv','').replace('plugs_','')

            r = await send_get_request(endpoint=f'api/data?source=plugs&date={d}',type='text')
            if type(r) == tuple:
                r = r[0]
            data.append(r)

    #parse response
    parsedData = []
    for d in data:
        tempDF = pd.read_csv(StringIO(d))
        tempDF['datetime'] = pd.to_datetime(tempDF['datetime'])
        parsedData.append(tempDF)

    #update with actual baseline requirements

    # filter out event dates
    pastEvents_type = pastEventsDF[pastEventsDF['type']==eType]
    pastEventDates = [d.date() for d in list(pastEvents_type['date'])]
    print(pastEventDates)

    filteredData = []
    for d in parsedData:
        #ignore days with past events (should this ignore those days regardless of type?
        print(d['datetime'][0])
        if list(d['datetime'])[0].date() not in pastEventDates:
            if list(d['datetime'])[0].date().weekday() <=4: # filter out weekends
                filteredData.append(d)

    # get event windows
    eventWindows = []
    for d in filteredData:
        #get on timestamps between event start and end times
        eventWindows.append(d[[(d > d.replace(hour=eTime,minute=0,second=0,microsecond=0)) and (d <= d.replace(hour=eTime+4,minute=0,second=0,microsecond=0)) for d in d['datetime']]])

    dailyWindowAvgW = []
    # eventLength = 4
    for i, d in enumerate(eventWindows):
        if len(d['datetime']) == 0:
            continue

        formattedStartTime = d['datetime'].iloc[0].replace(hour=eTime,minute=0,second=0,microsecond=0)

        # create hourly buckets for each day
        hourly = hourlyBuckets(d,formattedStartTime)

        # add increments within each hour
        incs = []
        for ih,h in enumerate(hourly):
            # the increments function adds a column for the increment of a specific datapoint
            incs.append(increments(h,formattedStartTime+timedelta(hours=ih)))

        #print(incs)

        hourlyEnergy = []
        for inc in incs:
            hourlyEnergy.append(getWh(inc['ac-W'],inc['increments']))
            if (math.isnan(hourlyEnergy[-1])):
                hourlyEnergy[-1] = 0.0

        dailyWindowAvgW.append(mean(hourlyEnergy))

    logging.debug(mean(dailyWindowAvgW))
    return mean(dailyWindowAvgW)

# buckets df with datetime within an event window into hourly buckets
# args: a dataframe with datetimes
def hourlyBuckets(tempDF, tempStartTime:float, eventDuration:float=4) -> list[pd.DataFrame]:
    hourlyPower = []
    for h in range(eventDuration):
        #print(tempDF['datetime'])
        ts = tempStartTime + timedelta(hours=h)
        te = tempStartTime + timedelta(hours=h + 1)
        filteredTempDF = (tempDF[(tempDF['datetime']> ts) & (tempDF['datetime']<= te)]).copy() #data within the hour
        #filteredTempDF = increments(filteredTempDF,ts)
        hourlyPower.append(filteredTempDF)
    return hourlyPower


#args: a dataframe with datetime column
# returns df with added increments column based on an hour
def increments(df,fm=0)->pd.DataFrame:
    if fm==0:
        firstMeasurement = df['datetime'].min()
    else:
        firstMeasurement = fm

    #print(firstMeasurement)
    incList = []
    for r in range(len(df['datetime'])):
        incSec = (df['datetime'].iloc[r] - firstMeasurement).total_seconds()/60/60 #must convert back from seconds
        incList.append(incSec)
    df['increments'] = incList
    return df

#args: power and time increments (relative to the hour) for a given hour
# returns the energy (Wh) for the hour
def getWh(p:list[float],t:list[datetime])->float:
    e = trapezoid(y=p, x=t)
    return e

##############
#### Main ####
##############

async def main():
    global buttonState, button_event, stateDict

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
            loop.call_soon_threadsafe(button_event.set)
            logging.info(f'Button pressed! {buttonState}')
        else:
            buttonState['state']=False
            buttonState['datetime']=datetime.now()
            stateDict['eventPause']=buttonState
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
        stateDict={"csrp":{"baselineW":0,"now":False,"upcoming":False},
                    "dlrp":{"baselineW":0,"now":False,"upcoming":False},
                    "datetime":datetime.now(),
                    "eventPause":{"datetime":datetime.now(), "state":False}}

    try:
        eventDF = atEvents.parseListToDF(await atEvents.listRecords())
        stateDict['csrp']['baselineW']=await getBaseline('CSRP',eventDF,csrpTime)
    except Exception as e:
        logging.error(e)

    while True:
        # get event status from Airtable
        try:
            if not eventDF:# conditional only needed to not call this twice at the start of the program
                eventDF = atEvents.parseListToDF(await atEvents.listRecords())
            # check for events
            eventCSRP = isCSRPEventUpcoming(eventDF,csrpTime)

            eventDLRP = isDLRPEventUpcoming(eventDF)
            if (eventDLRP['now']) or (eventDLRP['upcoming']):
                stateDict['dlrp']['baselineW']=await getBaseline('DLRP',eventDF,eventDLRP['upcoming'].time().hour)

            stateDict['datetime'] = datetime.now()
            stateDict['csrp']=eventCSRP
            stateDict['dlrp']=eventDLRP
            logging.debug(stateDict)

            # reset eventDF
            eventDF = None
        except Exception as e:
            logging.error(f"Couldn't check event status: {e}")

        # if paused
        if stateDict['eventPause']['state']:
            #if eventPause has been going on for an hour or more, unpause it
            if datetime.now()-stateDict['eventPause']['datetime'] > timedelta(hours=1):
                # unpause
                stateDict['eventPause']={'state':False,'datetime':datetime.now()}
                logging.debug(f"unpausing!: {stateDict['eventPause']}")

        #save state
        saveState(stateDict)

        # respond to event status as needed
        if ((eventCSRP['now']) or (eventDLRP['now'])) and (not stateDict['eventPause']['state']):
            # check that event is still going on...
            logging.debug('EVENT NOW!')
            await kD.setEventState()
        elif ((eventCSRP['upcoming']) or (eventDLRP['upcoming'])) :
            #if true, battery can discharge during prep state (add indicator for battery ok to use)
            # keep battery charged!
            logging.debug('EVENT UPCOMING!')
            await kD.setPrepState(True)
        elif stateDict['eventPause']['state']:
            await kD.setPrepState(True) #should it be in normal state when paused?
        else:
            await kD.setNormalState()

        # periodically (once a day?) estimate baseline
            # read AC power data for required period
            # filter to event window
            # get energy w/ trapazoid method
            # divide by 4 hours

        await sleeper(5*60)
        await asyncio.sleep(.1) # may not be necessary

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Main loop crashed: {e}")
