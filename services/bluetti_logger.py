# gets data and saves it in a CSV file

import sys
import os
import subprocess
import pandas as pd
import csv
import asyncio
import json
import signal
import logging
import datetime
from typing import cast
from typing import Any, Dict, Optional, Tuple, List

# add libraries to path
libdir = '/home/drux/demandResponse_UX_research/lib'
if os.path.exists(libdir):
    sys.path.append(libdir)
libdir = '/home/drux/demandResponse_UX_research/lib/helper_classes'
if os.path.exists(libdir):
    sys.path.append(libdir)

from Bluetti import Bluetti
from bluetti_mqtt.bluetooth import (
    check_addresses, build_device, scan_devices, BluetoothClient, ModbusError,
    ParseError, BadConnectionError
)
from bluetti_mqtt.core import (
    BluettiDevice, ReadHoldingRegisters, DeviceCommand
)
from bleak import BleakClient, BleakError, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from SmartPowerStation import SmartPowerStation

bluettiSTR = ['AC180','AC2']

logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.INFO)

freq = 60 * 5

dataDirectory = f'/home/drux/demandResponse_UX_research/data/'

try:
    repoRoot = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    with open(os.path.join(repoRoot,'config.json')) as f:
        config = json.load(f)
except Exception as e:
    logging.error(f"Error during reading config file: {e}")

try:
    pNum = int(config["participant"])
except:
    pNum = 0
logging.info(f"Participation #{pNum}")

# ============================
# Utilities
# ============================
def handle_signal(signal_num: int, frame: Any) -> None:
    """Handles termination signals for graceful shutdown."""
    logging.info(f"Received signal {signal_num}, shutting down gracefully...")
    sys.exit(0)

# ============================
# Main
# ============================        
async def main(SPS: SmartPowerStation) -> None:

    # dont run on devices without power station connections
    if pNum in [1,3]:
        while True:
            await asyncio.sleep(freq)

    scan_duration = 5

    while True:
        SPS.reset_bluetooth()

        # add wake up function to this
        for tries in range(3):
            try:
                devices = await scan_devices(scan_duration)
                logging.debug(devices)
                break
            except Exception as e:
                logging.error(f"Error during scanning: {e}")
                return

            if not devices:
                logging.error("No devices found.")
                #sys.exit(0)
            await asyncio.sleep(1+tries)

        #there should only be 1 device, so change this?
        for d in devices:
            print(d)
            result = await statusUpdate(d)
            if result:
                print(result)
                #tempResults = SPS.packageData(d, result, tempResults)
                tempResults = {
                        "datetime" : datetime.datetime.now(),
                        "powerstation_percentage": round(result['total_battery_percent'], 2),
                        "powerstation_inputWAC": result['ac_input_power'],
                        "powerstation_inputWDC": result['dc_input_power'],
                        "powerstation_outputWAC": result['ac_output_power'],
                        "powerstation_outputWDC": result['dc_output_power'],
                        "powerstation_outputMode": result['output_mode'],
                        "powerstation_deviceType": result['device_type']}

        fileName = f'{dataDirectory}powerstation_{str(datetime.date.today())}.csv'

        await writeData(fileName, pd.DataFrame([tempResults]))

        logging.debug('************ SLEEPING **************')
        await asyncio.sleep(freq)

async def writeData(fn, df):
    # create a new file daily to save data
    # or append if the file already exists
    logging.debug(df)

    try:
        with open(fn) as csvfile:
            savedDf = pd.read_csv(fn)
            savedDf = pd.concat([savedDf,df], ignore_index = True)
            #df = df.append(newDF, ignore_index = True)
            savedDf.to_csv(fn, sep=',',index=False)
    except Exception as err:
        logging.error(err)
        df.to_csv(fn, sep=',',index=False)

    logging.debug(f'csv writing: {str(datetime.datetime.now())}')
# returns list of BLE objects and matching saved devices i.e. [BLE, saved]
async def scan_devices(scan_duration: int):
    deviceList = []
    addresses = []

    def discovery_handler(device: BLEDevice, advertisement_data: AdvertisementData):

        if device.name is None:
            return

        #logging.debug(f'{device.name}')
        if any(b in device.name for b in bluettiSTR):
            if device.address not in addresses:
                addresses.append(device.address)
                deviceList.append(device)

    logging.info(f"Scanning for BLE devices for {scan_duration} seconds...")

    #adapter=bleAdapter,
    async with BleakScanner(detection_callback=discovery_handler) as scanner:
        await asyncio.sleep(scan_duration)
    
    logging.debug(deviceList)

    # Some BLE chipsets (especially on Raspberry Pi) need a few seconds between scanning and connecting.
    await asyncio.sleep(2)
    
    return deviceList

async def statusUpdate(bleDev):

    bluettiDev = Bluetti(bleDev.address,bleDev.name)
    try:
        result = await bluettiDev.getStatus()
    except Exception as e:
        logging.error(f"Error getting Bluetti status: {e}")

    if result:
        logging.debug(f"Method executed successfully. Result:")
        #print(result)
    else:
        logging.debug(f"Method executed successfully. No data returned.")

    return result

if __name__ == "__main__":
    # Suppress FutureWarnings
    import warnings

    warnings.simplefilter("ignore", FutureWarning)

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    SPS = SmartPowerStation()

    try:
        asyncio.run(main(SPS))
    except KeyboardInterrupt:
        logging.error("Script interrupted by user via KeyboardInterrupt.")
    except Exception as e:
        logging.error(f"Unexpected error in main: {e}")
