# code works for Kasa Smart Wi-Fi Plug Slim w/ Energy Monitoring Model:KP125MP4
# UN and PW are based on credentials used in the app when provisioning the devices
#docs: python-kasa.readthedocs.io

import asyncio
from kasa import Discover, Credentials
from dotenv import load_dotenv
import os

load_dotenv()
un = os.getenv('KASA_UN')
pw = os.getenv('KASA_PW')

# flip state of outlet
async def flipState(dev):

    await dev.update()

    if dev.is_on:
        print(dev.alias + ' is on. Turning off now...')
        await dev.turn_off()
    else:
        print(dev.alias + ' is off. Turning on now...')
        await dev.turn_on()

async def discoverAll():
    #discover all available devices
    devices = await Discover.discover(
        credentials=Credentials(un, pw),
        discovery_timeout=10
    )

    print(len(devices))

    for ip, device in devices.items():
        await device.update()
        print(f'{device.alias} ({device.mac}) at {device.host}')
        print(f'{device.modules}')

        await flipState(device)

        energy_module = device.modules.get("Energy")
        print(f'Power: {energy_module.current_consumption}W') #this library is really dumb - they use the word current to describe live power in Watts, NOT amperage

        await device.disconnect()
        print('')

    return devices

async def main():
    await discoverAll()

if __name__ == "__main__":
    asyncio.run(main())
