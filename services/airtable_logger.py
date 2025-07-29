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

AT = Airtable(atKey,'appqYfVvpJR5kBATE')

FREQ_SECONDS = 60

async def send_get_request(url,type:str,timeout=1) -> Any:
    """Send GET request to the IP."""

    # get own data
    max_tries = 3
    for attempt in range(max_tries):
        logging.debug(f'Attempt #{attempt+1}')
        try:
            response = requests.get(f"{url}", timeout=timeout)
            response.raise_for_status()
            if type == 'json':
                res = response.json()
            elif type == 'text':
                res = response.text
            else:
                res = response.status_code
            break
        except Exception as e:
            logging.error(f'{e}')
            if attempt == max_tries-1: # try up to 3 times
                res = {}
                logging.debug('FAILED!!!')
            else:
                logging.debug('SLEEEEEEEEEEEEEEEEEPING')
                await asyncio.sleep(1)

    return res

async def main():
    AT = Airtable(key,'live')

    # update state
    # get record IDs once at start to minimize API calls
    AT.names = [f'participant{participantNumber}']

    AT.IDs = await AT.getRecordID(AT.names)
    logging.debug(AT.IDs)

    while True:

        #############
        ### STATE ###
        #############

        state = []

        url = f"http://{localhost}:5000/api/state"
        state.append(await send_get_request(url,'json'))

        try:
            await AT.updateBatch(AT.names,AT.IDs,state)
        except Exception as e:
            logging.error(e)

        logging.debug(f'Sleeping for {FREQ_SECONDS/60} minutes.')


        ###################
        ### PERFORMANCE ###
        ###################

        # # if event is happening update every 5 minutes, else update every half-hour
        # if (state['csrp']['now']) or (state['dlrp']['now']):
        #     FREQ_SECONDS = 60 * 5
        # else:
        #     FREQ_SECONDS = 60 * 30

        await asyncio.sleep(FREQ_SECONDS)



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Main loop crashed: {e}")
