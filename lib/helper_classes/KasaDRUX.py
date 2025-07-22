import asyncio
from kasa import Discover, Credentials
import pandas as pd
import logging

logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.DEBUG)

class KasaDRUX():
    def __init__(self,un,pw):
        self.un =un
        self.pw = pw

    # discover Kasa devices and collect power data
    async def discoverAll(self):

        #discover all available devices
        devices = await Discover.discover(
            credentials=Credentials(self.un, self.pw),
            discovery_timeout=10
            )

        return devices

    async def getData(self):

        devices = await self.discoverAll()

        dataDF = pd.DataFrame(data={
            "datetime" : [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            "batteryin-W": "",
            "batteryout-W": "",
            "ac-W": ""})

        #logging.debug(len(devices))

        for ip, device in devices.items():
            try:
                await device.update()

                energy_module = device.modules.get("Energy")

                splitAlias = device.alias.split('-')
                dataDF[f'{splitAlias[1]}-W']=energy_module.current_consumption

                #logging.debug(energy_module.current_consumption)
                await device.disconnect()
            except Exception as e:
                logging.error(e)

        return dataDF

    # flip state of outlet
    async def flipState(self, dev):

        await dev.update()

        if dev.is_on:
            print(dev.alias + ' is on. Turning off now...')
            await dev.turn_off()
        else:
            print(dev.alias + ' is off. Turning on now...')
            await dev.turn_on()

    # flip state of outlet
    async def setState(self, dev,toState):

        #await dev.update()

        if toState:
            await dev.turn_on()
        else:
            await dev.turn_off()

        logging.debug(f'{dev.alias} is {toState}')

    async def getState(self,dev):
        await dev.update()

        s = dev.is_on
        logging.debug(f'{dev.alias} is {s}')
        return s

    async def setEventState(self):
        devices = await self.discoverAll()

        for ip, device in devices.items():
            try:
                #await device.update()

                # turn AC off
                if 'ac' in device.alias:
                    await self.setState(device,False)
                # turn battery input off
                elif 'batteryin' in dev.alias:
                    await self.setState(device,False)
                # turn battery output on
                elif 'batteryout' in dev.alias:
                    await self.setState(device,True)

                await device.disconnect()
            except Exception as e:
                logging.error(e)

        # turn all relays on
        async def setNormalState(self,dev):
            devices = await self.discoverAll()
            for ip, device in devices.items():
                try:
                    #await device.update()
                    await setState(device,True)
                    await device.disconnect()
                except Exception as e:
                    logging.error(e)
