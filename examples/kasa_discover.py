#source: https://python-kasa.readthedocs.io/en/latest/tutorial.html

import asyncio
from kasa import Discover, Credentials
from dotenv import load_dotenv
import os

load_dotenv()
un = os.getenv('KASA_UN')
pw = os.getenv('KASA_PW')

async def discoverSingle():
    #discover a single specific device
    device = await Discover.discover_single(
        "127.0.0.1",
        credentials=Credentials(un, pw),
        discovery_timeout=10
    )

    await device.update()  # Request the update
    print(device.alias)  # Print out the alias

async def discoverAll():
    #discover all available devices
    devices = await Discover.discover(
        credentials=Credentials(un, pw),
        discovery_timeout=10
    )
    for ip, device in devices.items():
        await device.update()
        print(f'{device.alias} ({device.mac}) at {device.host}')
        print(f'{device.features['voltage']} and {device.features['current']}')
        print('')

    return devices

async def main():
    await discoverAll()

    # dev = await Discover.discover_single("127.0.0.1",username="un@example.com",password="pw")
    # await dev.turn_on()
    # await dev.update()

if __name__ == "__main__":
    asyncio.run(main())
