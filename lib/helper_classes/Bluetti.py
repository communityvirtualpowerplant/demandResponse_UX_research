#import argparse
import asyncio
#import base64
import signal
from bleak import BleakError
#from io import TextIOWrapper
#import json
import sys
#import textwrap
#import time
from typing import cast
from bluetti_mqtt.bluetooth import (
    check_addresses, build_device, scan_devices, BluetoothClient, ModbusError,
    ParseError, BadConnectionError
)
from bluetti_mqtt.core import (
    BluettiDevice, ReadHoldingRegisters, DeviceCommand
)

class Bluetti():
    def __init__(self, address: str, name: str):
        self.address = address
        self.name = name
        self.manufacturer = 'bluetti'
        self.data = {'total_battery_percent':0,'ac_output_power':0,'ac_input_power':0,'dc_output_power':0,'dc_input_power':0}
        #self.charge = False
        self.BLUETTI_GATT_SERVICE_UUID = "0000ff00-0000-1000-8000-00805f9b34fb" #not in use
        self.maxTries = 20

    async def log_command(self, client: BluetoothClient, device: BluettiDevice, command: DeviceCommand):
        try:
            response_future = await client.perform(command)
            response = cast(bytes, await response_future)
            if isinstance(command, ReadHoldingRegisters):
                body = command.parse_response(response)
                parsed = device.parse(command.starting_address, body)
                return parsed #print(parsed.keys())
        except (BadConnectionError, BleakError, ModbusError, ParseError) as err:
            print(f'Got an error running command {command}: {err}')

    async def getStatus(self):
        myData={
        }

        try:
            device = build_device(self.address, self.name)

            print(f'Connecting to {self.address}')
            client = BluetoothClient(self.address)

            # loop = asyncio.get_running_loop()
            # #bTask = loop.create_task(client.run())

        #try:
            # async with asyncio.TaskGroup() as tg:
            # #     # Start the client
            #     tg.create_task(client.run())

                # for _ in range(self.maxTries):
                #     if client.is_ready:
                #         break
                #     print('Waiting for connection...')
                #     await asyncio.sleep(1)
                # else:
                #     print('Connection timeout')
                #     # return myData
                # Wait for client.is_ready with timeout

                # try:
                #     await asyncio.wait_for(self._wait_for_ready(client), timeout=10)
                # except asyncio.TimeoutError:
                #     print("Timeout: Device did not become ready.")
                #     run_task.cancel()  # Cancel client.run()
                #     await asyncio.gather(run_task, return_exceptions=True)  # Clean cancellation
                #     return myData
            t = asyncio.get_running_loop().create_task(client.run())

            try:
                await asyncio.wait_for(self._wait_for_ready(client), timeout=20)
            except asyncio.TimeoutError:
                print("[BLE] Connection timeout. Cancelling client task...")
                t.cancel()
                await asyncio.gather(t, return_exceptions=True)
                #raise  # or handle however you want
                return myData

            # Poll device
            for command in device.logging_commands:
                commandResponse = await self.log_command(client, device, command)
                if commandResponse:
                    for k,v in commandResponse.items():
                        myData[k]=v
            #print(myData)
        except Exception as e:
            print(f"Unexpected error during command execution: {e}")
        finally:
            try:
                if client.client: # and client.client.is_connected:
                    await client.client.disconnect()
                    print("Disconnected BLE client")
            except Exception as e:
                print(f"Error during BLE disconnect: {e}")

        return myData


    async def _wait_for_ready(self, client: BluetoothClient):
        """Helper: wait until the client is ready."""
        while not client.is_ready:
            print('Waiting for connection...')
            await asyncio.sleep(1)
