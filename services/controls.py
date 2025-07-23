from dotenv import load_dotenv
import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import json

logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.DEBUG)

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

def convert_datetimes(obj):
    if isinstance(obj, dict):
        return {k: convert_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetimes(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

def saveState(d:dict):
    try:
        with open(os.path.join(repoRoot,'services/state.json'), "w") as json_file:
            json.dump(convert_datetimes(d), json_file, indent=4)
            logging.debug(f'State written to file. :)')
    except Exception as e:
        logging.error(f'Exception writing state to file: {e}')

async def main():

    while True:
        # get event status from Airtable
        eventDF = atEvents.parseListToDF(await atEvents.listRecords())
        # check for events
        eventCSRP = isCSRPEventUpcoming(eventDF,csrpTime)
        eventDLRP = isDLRPEventUpcoming(eventDF)

        stateDict = {'datetime':datetime.now(),
                    'csrp':eventCSRP,
                    'dlrp':eventDLRP,
                    'eventPause':False}

        logging.debug(stateDict)

        # listen for button to pause for 1 hour
        # try:
        #     if buttonPressed:
        #         buttonTime = datetime.now()
        #           eventDict['eventPause']=False
        # except Exception as e:
        #     logging.error(f'{e}')

        #save state
        saveState(stateDict)

        # respond to event status as needed
        if ((eventCSRP['now']) or (eventDLRP['now'])) and (not eventDict['eventPause']):
            # check that event is still going on...
            logging.debug('EVENT NOW!')
            await kD.setEventState()
        elif ((eventCSRP['upcoming']) or (eventDLRP['upcoming'])) :
            #if true, battery can discharge during prep state (add indicator for battery ok to use)
            # keep battery charged!
            logging.debug('EVENT UPCOMING!')
            await kD.setPrepState(True)
        elif pause:
            await kD.setPrepState(True) #should it be in normal state when paused?
        else:
            await kD.setNormalState()

        # periodically (once a day?) estimate baseline
            # read AC power data for required period
            # filter to event window
            # get energy w/ trapazoid method
            # divide by 4 hours

        await asyncio.sleep(5*60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Main loop crashed: {e}")
