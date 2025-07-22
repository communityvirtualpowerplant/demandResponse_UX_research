# gets data and saves it in a CSV file
# run with "python -m examples.ble_logStatus" + location from parent directory

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

logging.basicConfig(level=logging.DEBUG)

# dataDirectory = '../data/'
# deviceFile = '../config/devices.json'
# configFile = '../config/config.json'

#changed based on hardware
#bleAdapter = "hci0"

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
    SPS.reset_bluetooth()

    scan_duration = 5

    try:
        devices = await scan_devices(scan_duration)
    except Exception as e:
        logging.error(f"Error during scanning: {e}")
        return

    if not devices:
        logging.error("No devices found. Exiting")
        sys.exit(0)

    tempResults = {
                    "datetime" : datetime.datetime.now(),
                    "powerstation_percentage": '',
                    "powerstation_inputWAC": '',
                    "powerstation_inputWDC": '',
                    "powerstation_outputWAC": '',
                    "powerstation_outputWDC":'',
                    "powerstation_outputMode":'',
                    "powerstation_deviceType":'',
                    "relay1_power": '',
                    "relay1_current":'',
                    "relay1_voltage": '',
                    "relay1_status": '',
                    "relay1_device": '',
                    "relay2_power": '',
                    "relay2_current":'',
                    "relay2_voltage": '',
                    "relay2_status": '',
                    "relay2_device": ''}

    #results = []
    for d in devices:
        logging.debug(d)
        result = await statusUpdate(d)
        if result:
            logging.info(result)

# returns list of BLE objects and matching saved devices i.e. [BLE, saved]
async def scan_devices(scan_duration: int):
    deviceList = []

    def discovery_handler(device: BLEDevice, advertisement_data: AdvertisementData):

        if device.name is None:
            return

        #logging.debug(f'{device.name}')
        if any(b in device.name for b in bluettiSTR):
            if device.address not in deviceList:
                deviceList.append(device)

    logging.info(f"Scanning for BLE devices for {scan_duration} seconds...")

    #adapter=bleAdapter,
    async with BleakScanner(detection_callback=discovery_handler) as scanner:
        await asyncio.sleep(scan_duration)
    
    logging.debug(deviceList)

    # Some BLE chipsets (especially on Raspberry Pi) need a few seconds between scanning and connecting.
    await asyncio.sleep(2)
    
    return deviceList

async def statusUpdate(device):
    bleDev = device[0]
    #savedDev = device[1]

    bluettiDev = Bluetti(bleDev["address"],bleDev["name"])
    try:
        result = await bluettiDev['device'].getStatus()
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
