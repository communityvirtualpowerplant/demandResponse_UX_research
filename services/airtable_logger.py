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

FREQ_SECONDS = 60

# async def send_get_request(url,type:str,timeout=1) -> Any:
#     """Send GET request to the IP."""

#     # get own data
#     max_tries = 3
#     for attempt in range(max_tries):
#         logging.debug(f'Attempt #{attempt+1}')
#         try:
#             response = requests.get(f"{url}", timeout=timeout)
#             response.raise_for_status()
#             if type == 'json':
#                 res = response.json()
#             elif type == 'text':
#                 res = response.text
#             else:
#                 res = response.status_code
#             break
#         except Exception as e:
#             logging.error(f'{e}')
#             if attempt == max_tries-1: # try up to 3 times
#                 res = {}
#                 logging.debug('FAILED!!!')
#             else:
#                 logging.debug('SLEEEEEEEEEEEEEEEEEPING')
#                 await asyncio.sleep(1)

#     return res

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

    # update state
    # get record IDs once at start to minimize API calls

    AT.IDs = await AT.getRecordIDbyName(AT.names,table='state')
    logging.debug(AT.IDs)

    while True:

        #############
        ### STATE ###
        #############

        state = []

        state.append(await send_get_request('localhost',endpoint='api/state'))

        try:
            await AT.updateBatch(AT.names,AT.IDs,state,table='state')
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
