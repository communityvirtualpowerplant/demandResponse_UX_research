# TP Link Kasa Smart Plug with Energy Monitoring
'''
documentation:
https://python-kasa.readthedocs.io/en/latest/index.html
https://python-kasa.readthedocs.io/en/latest/smartdevice.html
'''

import asyncio
from kasa import Discover, Credentials, Module
#from kasa.iot import IotPlug
from dotenv import load_dotenv
import os

load_dotenv()
un = os.getenv('KASA_UN')
pw = os.getenv('KASA_PW')

async def initialize():
    #discover a single specific device
    # device = await Discover.discover_single(
    #     "127.0.0.1",
    #     credentials=Credentials("myusername", "mypassword"),
    #     discovery_timeout=10
    # )


    devices = await Discover.discover(
        credentials=Credentials(un, pw),
        discovery_timeout=10
    )
    for ip, device in devices.items():
        await device.update()
        print(device.features)
        for feature_id, feature in device.features.items():
            print(f"{feature.name} ({feature_id}): {feature.value}")


    return devices

# get power and energy data
async def getData(dev):
    try:
        await dev.update()
        print('')
        print(f'{dev.features['current_consumption'].value} W')
        print(f'{dev.features['voltage'].value} V')
        print(f'{dev.features['current'].value} A')
        # w = float(dev.features.current) * float(dev.features.voltage)
        # print(f'{w} W')
        print("Outlet is on: " + str(dev.is_on))
        print('')
    # except Exception as e:
    #     print(e)
    finally:
        if hasattr(dev, "session"):
            await dev.session.close()

# flip state of outlet
async def flipState(dev):

    #p = SmartPlug(ip)
    await dev.update()

    if dev.is_on:
        print(dev.alias + ' is on. Turning off now...')
        await dev.turn_off()
    else:
        print(dev.alias + ' is off. Turning on now...')
        await dev.turn_on()

async def main():

    try:
        deviceList = await initialize()

        for ip, device in deviceList.items():
            #await flipState(device)
            await getData(device)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    asyncio.run(main())
