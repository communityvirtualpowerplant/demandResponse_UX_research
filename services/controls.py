from dotenv import load_dotenv
import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd

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

def isCSRPEventUpcoming(df,t):
    csrpDF = df[df['type']=='csrp']

    for index, row in csrpDF.iterrows():
        csrpStartTime = row['date'].replace(hour=csrpTime)
        logging.debug(datetime.now()-csrpStartTime)
        if (datetime.now()-csrpStartTime < timedelta(hours=0)) and (datetime.now()-csrpStartTime >= timedelta(hours=-21)):
            logging.debug('event upcoming within 21 hours')
        elif (datetime.now()-csrpStartTime > timedelta(hours=0)) and (datetime.now()-csrpStartTime <= timedelta(hours=4)):
            logging.debug('event ongoing')

def isDLRPEventUpcoming(df):
    dlrpDF = df[df['type']=='dlrp']
    for index, row in dlrpDF.iterrows():
        dlrpStartTime = row['date'].replace(hour=int(row['time']))
        print(datetime.now()-dlrpStartTime)
        if (datetime.now()-dlrpStartTime < timedelta(hours=0)) and (datetime.now()-dlrpStartTime >= timedelta(hours=-2)):
            print('event upcoming within 2 hours')
        elif (datetime.now()-dlrpStartTime > timedelta(hours=0)) and (datetime.now()-dlrpStartTime <= timedelta(hours=4)):
            print('event ongoing')

async def main():

    eventDF = atEvents.parseListToDF(await atEvents.listRecords())

    #filter results
    eventDF = eventDF[~eventDF['status'].isin(['cancelled','past'])]

    csrpTime = 17 # pull this from config!
    isCSRPEventUpcoming(eventDF,csrpTime)

    isDLRPEventUpcoming(eventDF)

    logging.debug(eventDF)

    while True:
        # get event status from Airtable

        # pull dates and filter
        # get next event

        # listen for button to pause for 1 hour
        # try:
        #     if buttonPressed:
        #         buttonTime = datetime.now()
        # except Exception as e:
        #     logging.error(f'{e}')

        pause = False
        # if datetime.now() - buttonTime < 1:
        #     pause = True

        # respond to event status as needed
        if event and not pause:
            await kD.setEventState()
        elif eventUpcoming:
            #if true, battery can discharge during prep state (add indicator for battery ok to use)
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
