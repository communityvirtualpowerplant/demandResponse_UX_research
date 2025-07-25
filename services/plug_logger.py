import time
import csv
import os
import sys
import datetime
import json
from dotenv import load_dotenv
import asyncio
from kasa import Discover, Credentials
import logging
import pandas as pd

libdir = '/home/drux/demandResponse_UX_research/lib/helper_classes'
if os.path.exists(libdir):
    sys.path.append(libdir)
from KasaDRUX import KasaDRUX
#from Airtable import Airtable


# ------------------ Config ------------------ #
logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.DEBUG)

repoRoot = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
logging.debug(repoRoot)

with open(os.path.join(repoRoot,'config.json')) as f:
    config = json.load(f)

participantNumber = int(config["participant"])
network = config["network"]
logging.debug(network)

# ------------------ Environmental Variables ------------------ #
load_dotenv()
un = os.getenv('KASA_UN')
pw = os.getenv('KASA_PW')
#atKey = os.getenv('AIRTABLE')
if not un or not pw:
    logger.error("Missing KASA_UN or KASA_PW in environment.")
    raise EnvironmentError("Missing Kasa credentials")
# if not atKey:
#     logger.error("Missing Airtable key in environment.")
#     raise EnvironmentError("Missing Airtable credentials")

kD = KasaDRUX(un,pw)
#atEvents = Airtable(atKey,'apptjKq3GAr5CVOQT','events')

freq = 60 * 5

async def main():

    while True:
        power_data = await kD.getData()

        logging.debug(power_data)

        # create a new file daily to save data or append if the file already exists
        fileName = f'/home/drux/demandResponse_UX_research/data/plugs_{str(datetime.date.today())}.csv'

        try:
            with open(fileName) as csvfile:
                df = pd.read_csv(fileName)
                df = pd.concat([df,power_data], ignore_index = True)
                df.to_csv(fileName, sep=',',index=False)
                logging.debug('Data appended.')
        except Exception as e:
            logging.debug(f'Failed to append CSV... trying to write new CSV. {e}')
            try:
                power_data.to_csv(fileName, sep=',',index=False)
                logging.debug('New CSV created.')
            except Exception as e:
                logging.error(f'Failed to write new CSV. {e}')

        await asyncio.sleep(freq)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Main loop crashed: {e}")
