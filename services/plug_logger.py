import time
import csv
import os
import datetime
import json
from dotenv import load_dotenv
import asyncio
from kasa import Discover, Credentials
import logging
import pandas as pd

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
if not un or not pw:
    logger.error("Missing KASA_UN or KASA_PW in environment.")
    raise EnvironmentError("Missing Kasa credentials")

FREQ_SECONDS = 60 * 5

# discover Kasa devices and collect power data
async def discoverAll():

    #discover all available devices
    devices = await Discover.discover(
        credentials=Credentials(un, pw),
        discovery_timeout=10
        )

    dataDF = pd.DataFrame(data={
        "datetime" : [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "battery-in-W": "",
        "battery-out-W": "",
        "ac-W": ""})

    logging.debug(len(devices))

    for ip, device in devices.items():
        try:
            await device.update()

            energy_module = device.modules.get("Energy")

            dataDF[f'participant{participantNumber}-in-_W']=energy_module.current_consumption
            logging.debug(energy_module.current_consumption)
            await device.disconnect()
        except Exception as e:
            logging.error(e)

    return dataDF

async def main():

    while True:
        power_data = await discoverAll()

        logging.debug(power_data)

        # create a new file daily to save data or append if the file already exists
        fileName = '/home/drux/data/plugs' + '_'+str(datetime.date.today())+'.csv'

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
