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

# async def discoverSingle():
#     #discover a single specific device
#     device = await Discover.discover_single(
#         "127.0.0.1",
#         credentials=Credentials(un, pw),
#         discovery_timeout=10
#     )

#     #await device.update()  # Request the update
#     print(device.alias)  # Print out the alias

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

        energy_module = device.modules.get("Energy")
        print(f'Power: {energy_module.current_consumption}W') #this library is really dumb - they use the word current to describe live power in Watts, NOT amperage

        # print("⚡ Energy Monitoring Data:")
        # for key, value in vars(energy_module).items():
        #     print(f"  {key}: {value}")
        await device.disconnect()
        print('')

    return devices

async def main():
    await discoverAll()

if __name__ == "__main__":
    asyncio.run(main())
