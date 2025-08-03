import os
import sys
import datetime
import json
from dotenv import load_dotenv
import asyncio
import logging
import requests
from typing import Any, Dict, Optional, List

# ------------------ Config ------------------ #
logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.DEBUG)

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

FREQ_SECONDS = 60 * 5

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

async def main():

    #sleep for 10 seconds at start
    await asyncio.sleep(10)

    # update state
    # get record IDs once at start to minimize API calls

    AT.stateIDs = await AT.getRecordIDbyName(AT.names,table='state')
    AT.healthIDs = await AT.getRecordIDbyName(AT.names,table='health')

    #logging.debug(AT.IDs)

    while True:

        #############
        ### STATE ###
        #############

        try:
            state = await send_get_request(endpoint='api/state')
            logging.debug(state)
            logging.debug(type(state))

            state["plugs"] = await send_get_request(endpoint='api/data?date=now&source=plugs')
            logging.debug(plugs)

            powerstation = await send_get_request(endpoint='api/data?date=now&source=powerstation')
            logging.debug(plugs)

            state["powerstation_percentage"] = powerstation['powerstation_percentage']

            stateList = [state]

            try:
                await AT.updateBatch(AT.names,AT.stateIDs,stateList,table='state')
            except Exception as e:
                logging.error(e)
        except Exception as e:
            logging.error(f'Error logging state: {e}')

        ##############
        ### HEALTH ###
        ##############
        try:
            health = [await send_get_request(endpoint='api/health')]
            #logging.debug(state)

            try:
                await AT.updateBatch(AT.names,AT.healthIDs,health,table='health')
            except Exception as e:
                logging.error(e)
        except Exception as e:
            logging.error(f'Error logging health: {e}')

        ###################
        ### PERFORMANCE ###
        ###################

        # try:
        #     performance = []

        #     perf = await send_get_request(endpoint='api/performance')

        #     for k in perf.keys():
        #         performance.append(perf[k])
        #         logging.debug(perf[k])

        #     try:
        #         # pIDs = await AT.getRecordIDbyName(perf.keys(),table=f'perf_participant{participantNumber}')
        #         # logging.debug(pIDs)

        #         # how does this deal with new additions?
        #         await AT.updatePerformance(perf.keys(),pIDs,performance,table=f'perf_participant{participantNumber}')
        #     except Exception as e:
        #         logging.error(e)
        # except Exception as e:
        #     logging.error(f'Error logging performance: {e}')

        # if event is happening update every 10 minutes, else update every half-hour
        if (state['csrp']['now']) or (state['dlrp']['now']):
            FREQ_SECONDS = 60 * 15
        else:
            FREQ_SECONDS = 60 * 30

        logging.debug(f'Sleeping for {FREQ_SECONDS/60} minutes.')

        await asyncio.sleep(FREQ_SECONDS)



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Main loop crashed: {e}")
