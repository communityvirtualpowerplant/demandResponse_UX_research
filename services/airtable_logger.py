import os
import sys
import datetime
import json
from dotenv import load_dotenv
import asyncio
import logging
import requests
from typing import Any, Dict, Optional, List
import random

# ------------------ Config ------------------ #
debug = False

if debug:
    logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.DEBUG)
else:
    logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.INFO)

libdir = '/home/drux/demandResponse_UX_research/lib/helper_classes'
if os.path.exists(libdir):
    sys.path.append(libdir)

from Airtable import Airtable

load_dotenv()
key = os.getenv('AIRTABLE')
if not key:
    logger.error("Missing AIRTABLE in environment.")
    raise EnvironmentError("Missing Airtable credentials")

try:
    repoRoot = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    with open(os.path.join(repoRoot,'config.json')) as f:
        config = json.load(f)
except Exception as e:
    logging.error(f"Error during reading config file: {e}")

participantNumber = int(config["participant"])

AT = Airtable(key,'appqYfVvpJR5kBATE')
AT.names = [f'participant{participantNumber}']

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

async def send_get_request(url:str='http://localhost:5000/',endpoint:str='',type:str='json',timeout=1):
        """Send GET request to the IP."""
        # get own data
        max_tries = 3
        for attempt in range(max_tries):
            try:
                response = requests.get(f"{url}{endpoint}", timeout=timeout)
                response.raise_for_status()
                if type == 'json':
                    res= convert_bools(response.json()) # add to parse datetimes: parse_datetimes()
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

async def logPerformance(n,i):
    try:
        performance = await send_get_request(endpoint='api/performance')

        performanceList = [json.dumps(performance)]

        try:
            # Remember, even if this is run successfully,
            # the modified timestamp wont be updated if the data hasn't changed!
            await AT.updateBatchPerformance(n,i,performanceList,table='performance')
        except Exception as e:
            logging.error(f'Error updating performance: {e}')
    except Exception as e:
        logging.error(f'Error getting performance: {e}')

async def startCheck():
    #stagger the start randomlly
    await asyncio.sleep(random.randint(20,80))

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

        await asyncio.sleep(20+(count**2)+random.randint(0,5))

async def main():

    await startCheck()

    # update state
    # get record IDs once at start to minimize API calls

    AT.stateIDs = await AT.getRecordIDbyName(AT.names,table='state')
    AT.healthIDs = await AT.getRecordIDbyName(AT.names,table='health')
    AT.performanceIDs = await AT.getRecordIDbyName(AT.names,table='performance')

    await logPerformance(AT.names,AT.performanceIDs)

    # logging.debug(AT.healthIDs)
    # logging.debug(AT.stateIDs)

    count = 0
    while True:

        #######################################
        ### HEALTH - only needed periodically ###
        #######################################
        if count % 4 == 0:
            try:
                health = await send_get_request(endpoint='api/health')
                #logging.debug(health)

                healthList = [health]
            except Exception as e:
                healthList = [f"Error getting health: {e}"]
                logging.error(f"Error getting health: {e}")

            try:
                await AT.updateBatch(AT.names,AT.healthIDs,healthList,table='health')
            except Exception as e:
                logging.error(f'Error updating health: {e}')

        #############
        ### STATE ###
        #############

        try:
            state = await send_get_request(endpoint='api/state')
            logging.debug(state)
            logging.debug(type(state))
        except Exception as e:
            logging.error(f'Error getting state: {e}')
            state = f'Error getting state: {e}'

        try:
            state["plugs"] = await send_get_request(endpoint='api/data?date=now&source=plugs')
        except Exception as e:
            logging.error(f"Error getting plugs: {e}")
            state["plugs"] = f"Error getting plugs: {e}"

        try:
            powerstation = await send_get_request(endpoint='api/data?date=now&source=powerstation')
            state["powerstation"] = powerstation
        except Exception as e:
            state["powerstation"] = f"Error getting powerstation: {e}"

        stateList = [state]

        try:
            await AT.updateBatch(AT.names,AT.stateIDs,stateList,table='state')
        except Exception as e:
            logging.error(f'Error updating state: {e}')

        ###################
        ### PERFORMANCE ###
        ###################

        if (state['csrp']['now']) or (state['dlrp']['now']):
            await logPerformance(AT.names,AT.performanceIDs)

        #############
        ### SLEEP ###
        #############

        count = count + 1

        # if event is happening update every 10 minutes, else update every half-hour
        if (state['csrp']['now']) or (state['dlrp']['now']):
            FREQ_SECONDS = 60 * 10
        else:
            FREQ_SECONDS = 60 * 30

        logging.debug(f'Sleeping for {FREQ_SECONDS/60} minutes.')

        await asyncio.sleep(FREQ_SECONDS)



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Main loop crashed: {e}")
