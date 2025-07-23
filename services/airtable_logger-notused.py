import os
import datetime
import json
from dotenv import load_dotenv
import asyncio
import logging
import requests
from typing import Any, Dict, Optional, List
from airtable import Airtable

# ------------------ Config ------------------ #
logging.basicConfig(level=logging.DEBUG)
#LOG_FILENAME = "kasa_log.log"

load_dotenv()
key = os.getenv('AIRTABLE')
if not key:
    logger.error("Missing AIRTABLE in environment.")
    raise EnvironmentError("Missing Airtable credentials")

# if true collect Kasa data
includeKasa = True

try:
    with open("/home/case/CASE_sensor_network/rpi_zero_sensor/config.json") as f:
        config = json.load(f)

    deviceNum = config["sensor"]["number"]
except Exception as e:
    logging.error(e)

# mode: 1 = only individual data; 8 = all data
MODE = 8

FREQ_SECONDS = 60 * 60 * 2

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

    # get record IDs once at start to minimize API calls
    if MODE == 1:
        AT.names = [f'sensor{deviceNum}']
    else:
        for n in range(8):
            AT.names.append(f'sensor{n+1}')

        if includeKasa:
            AT.names.append('kasa')

        logging.debug(AT.names)
    AT.IDs = await AT.getRecordID(AT.names)
    logging.debug(AT.IDs)

    while True:
        now = []
        # get own data - Mode1 not tested
        if MODE == 1:

            url = f"http://{localhost}:5000/api/data?date=now"
            now.append(await send_get_request(url,'json'))

            try:
                await AT.updateBatch(AT.names,AT.IDs,now)
            except Exception as e:
                logging.error(e)

        # get everyone elses data
        else:
            for n in range(8):
                url = f"http://pi{n+1}.local:5000/api/data?date=now"
                now.append(await send_get_request(url,'json'))

                #now.append(await getSensorData(f'pi{n+1}.local'))

            if includeKasa:
                url = f"http://kasa.local:5000/api/data?date=now"
                now.append(await send_get_request(url,'json'))

            print(now)
            try:
                await AT.updateBatch(AT.names,AT.IDs,now)
            except Exception as e:
                logging.error(e)

        logging.debug(f'Sleeping for {FREQ_SECONDS/60} minutes.')
        await asyncio.sleep(FREQ_SECONDS)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Main loop crashed: {e}")
