import json
import subprocess
import logging
from typing import cast
from typing import Any, Dict, Optional, Tuple, List
from bleak import BleakClient, BleakError, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import asyncio
from datetime import datetime, date, timedelta, time
import requests
import pandas as pd
from io import StringIO
from scipy.integrate import trapezoid
import math
import numpy as np
import statistics
import sys
import os

class SmartPowerStation():
    def __init__(self,info=True, debug=True,error=True):
        # self.config = self.getConfig(conf)
        # self.name = self.config['location']
        # self.location = self.config['location']
        # self.promise = self.config['promise']
        # self.network = self.config['network']
        self.printInfo = info
        self.printDebug = debug
        self.printError = error
        self.dataFilePrefix = 'sps'
        self.shellySTR = 'Shelly'
        self.bluettiSTR = ['AC180','AC2']
        self.devices = []
        self.bleAdapter = "hci0" #changed based on hardware

    ######### SETUP ###############

    # reads json config file and returns it as dict
    def getConfig(self, fn:str) -> Any:
        # Read data from a JSON file
        try:
            with open(fn, "r") as json_file:
                return json.load(json_file)
        except Exception as e:
            self.log_error(f"Error during reading {fn} file: {e}")
            if 'devices' in fn.lower():
                return []
            else:
                return {}
    
    # get list of saved devices from device file, filtered by location
    def getDevices(self, dF:str, location:Optional[str] = None)->list[Dict]:
        if location is None:
            location = self.location

        self.log_debug(location)

        # Read data from a JSON file
        try:
            with open(dF, "r") as json_file:
                savedDevices = json.load(json_file)
        except Exception as e:
            log_error(f"Error during reading devices.json file: {e}")
            savedDevices = []

        filteredEntries = []

        #filter by location
        for entry in savedDevices:
            if entry['location'] == location:
                filteredEntries.append(entry)

        self.devices=filteredEntries

        return self.devices

    ################# FILE IO ######################

    def writeJSON(self, data:Dict, fn:str)-> None:
        # Save data to a JSON file
        try:
            with open(fn, "w") as json_file:
                json.dump(data, json_file, indent=4)

            print(f"JSON file written successfully at {fn}")
        except Exception as e:
            self.log_error(f"Error writing {fn} file: {e}")

    async def readJSON(self, fn:str):
        # Read data from a JSON file
        try:
            with open(fn, "r") as json_file:
                savedDevices = json.load(json_file)
        except Exception as e:
            self.log_error(f"Error reading json file {fn}: {e}")

    async def concatCSV(self,df:pd.DataFrame, fn:str)->None:
        # create a new file daily to save data
        # or append if the file already exists
        try:
            if os.path.exists(fn):
                with open(fn) as csvfile:
                    savedDf = pd.read_csv(csvfile)
                    savedDf = pd.concat([savedDf,df], ignore_index = True)
                    savedDf.to_csv(fn, sep=',',index=False)
                    self.log_debug(f"Concatinating existing CSV: {fn}")
            else:
                #if file doesn't exist, create it
                df.to_csv(fn, sep=',',index=False)
                self.log_debug(f"Creating new CSV: {fn}")

        except Exception as e:
            self.log_error(e)

    ######### BLUETOOTH ############
    def reset_bluetooth(self) -> None:
        try:
            subprocess.run(["sudo", "rfkill", "unblock", "bluetooth"], check=True)
            subprocess.run(["sudo", "hciconfig", "hci0", "down"], check=True)
            subprocess.run(["sudo", "hciconfig", "hci0", "up"], check=True)

        except subprocess.CalledProcessError as e:
            self.log_error(f"Bluetooth interface reset failed: {e}")

    # scans for BLE devices and filters them by the saved device list (already filtered by location)
    # returns list of BLE objects and matching saved devices i.e. [BLE, saved]
    async def scan_devices(self, saved_devices: list[Dict])->list[Dict]:
        filteredDevices = []
        scan_duration = 5

        addressList = []
        def discovery_handler(device: BLEDevice, advertisement_data: AdvertisementData):
            # mf = ''
            # notFound = 1

            if device.name is None:
                return

            for sd in saved_devices:
                #print(sd)
                if device.address == sd['address'] and device.address not in addressList:    
                    self.log_debug(device)
                    addressList.append(device.address)
                    filteredDevices.append([device,sd])

        self.log_info(f"Scanning for BLE devices for {scan_duration} seconds...")

        async with BleakScanner(adapter=self.bleAdapter, detection_callback=discovery_handler) as scanner:
            await asyncio.sleep(scan_duration)
        
        self.log_debug(addressList)

        # Some BLE chipsets (especially on Raspberry Pi) need a few seconds between scanning and connecting.
        await asyncio.sleep(2)
        
        return filteredDevices

    # ============================
    # Utilities
    # ============================
    def handle_signal(self, signal_num: int, frame: Any) -> None:
        """Handles termination signals for graceful shutdown."""
        self.log_info(f"Received signal {signal_num}, shutting down gracefully...")
        sys.exit(0)

    def log_info(self, message: str) -> None:
        """Logs an info message."""
        logging.info(message)
        self.log_print(message, self.printInfo)

    def log_error(self, message: str) -> None:
        """Logs an error message."""
        logging.error(message)
        self.log_print(message, self.printError)

    def log_debug(self, message: str) -> None:
        """Logs a debug message."""
        logging.debug(message)
        self.log_print(message, self.printDebug)

    def log_print(self, message:str, b:bool) -> None:
        if b:
            print(message)

    # ============================
    # Data
    # ============================
    #Check if the timestamp is within the last 10 minutes.
    def isRecent(ts, seconds=600)->bool:
        if isinstance(ts, str):
            ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") #check if the ts is a string and convert
        now = datetime.now()
        return now - ts <= timedelta(seconds)

    def packageData(self, d, r, t) -> Dict:
        try:
            if d[1]['manufacturer'].lower() == 'bluetti':
                #print('bluetti!')
                t["powerstation_percentage"] = round(r['total_battery_percent'], 2)
                t["powerstation_inputWAC"] = r['ac_input_power']
                t["powerstation_inputWDC"] = r['dc_input_power']
                t["powerstation_outputWAC"] = r['ac_output_power']
                t["powerstation_outputWDC"] = r['dc_output_power']
                t["powerstation_outputMode"] = r['output_mode']
                t["powerstation_deviceType"] = r['device_type']
                # temp values
                t["relay3_power"] = r['ac_output_power']
                t["relay3_status"] =str(True)
                t["relay3_device"] = r['device_type']
            elif 'Shelly'.lower() in d[1]['name'].lower():
                if '1PM'.lower() in d[1]['name'].lower():
                    #print('1pm!')
                    if int(d[1]['relay1']) in [1,2,3]:
                        p = int(d[1]['relay1'])
                        t[f'relay{p}_power'] = r[0]["apower"]
                        t[f'relay{p}_current'] =r[0]["current"]
                        t[f'relay{p}_voltage'] =r[0]["voltage"]
                        t[f'relay{p}_status'] =str(r[0]["output"]) #must be cast to str because the dict interprets the bool as an int
                        t[f'relay{p}_device'] = d[1]['name']
                    # elif int(d[1]['relay1']) == 2:
                    #     t['relay2_power'] = r[0]["apower"]
                    #     t['relay2_current'] =r[0]["current"]
                    #     t['relay2_voltage'] =r[0]["voltage"]
                    #     t['relay2_status'] =str(r[0]["output"]) #must be cast to str because the dict interprets the bool as an int
                    #     t['relay2_device'] = d[1]['name']
                elif '2PM'.lower() in d[1]['name'].lower():
                    #print('2pm!')
                    t['relay1_power'] = r[0]["apower"]
                    t['relay1_current'] =r[0]["current"]
                    t['relay1_voltage'] =r[0]["voltage"]
                    t['relay1_status'] =str(r[0]["output"]) #must be cast to str because the dict interprets the bool as an int
                    t['relay1_device'] = d[1]['name']
                    t['relay2_power'] = r[1]["apower"]
                    t['relay2_current'] =r[1]["current"]
                    t['relay2_voltage'] =r[1]["voltage"]
                    t['relay2_status'] =str(r[1]["output"]) #must be cast to str because the dict interprets the bool as an int
                    t['relay2_device'] = d[1]['name']
            elif KASA:
                if int(d[1]['relay1']) in [1,2,3]:
                    p = int(d[1]['relay1'])
                    t[f'relay{p}_power'] = r[0]["apower"]
                    t[f'relay{p}_current'] =r[0]["current"]
                    t[f'relay{p}_voltage'] =r[0]["voltage"]
                    t[f'relay{p}_status'] =str(r[0]["output"]) #must be cast to str because the dict interprets the bool as an int
                    t[f'relay{p}_device'] = d[1]['name']
        except Exception as e:
            print(e)

        return t

# ============================
# Control
# ============================
class Controls():
    def __init__(self):
        self.goalWh = 0
        self.duration = 4
        self.batCapWh = 0
        self.maxFlexibilityWh = 0
        self.availableFlexibilityWh = 0
        self.invEff = .85 #assumes 85% efficient inverter
        self.dod = .8 # assumes 80% depth of discharge
        self.avgPvWh = 0 # recent daily average
        self.maxPvWh = 0 # recent daily max
        self.eventStartT = time(16,00)
        self.eventDurationH = 4
        self.eventEndT = time(self.eventDurationH,00)
        self.eventDT = datetime(year=1,month=1,day=1)
        self.baseline = 0
        self.modeZero = {1:0,2:0,3:0}
        self.modeOne = {1:1,2:1,3:0} #with an autotransfer, if pos 1 is on pos 3 is automatically off
        self.modeTwo = {1:1,2:0,3:0} #with an autotransfer, if pos 1 is on pos 3 is automatically off
        self.modeThree = {1:0,2:1,3:1}
        self.modeFour = {1:0,2:1,3:0}
        self.modeFive = {1:0,2:0,3:1}
        #self.pvSetPoint = 50 # battery percentage to maximize solar utilization
        #self.minSetPoint = int(100 * (1.0-self.dod))
        self.dischargeT = time(16,00)
        self.upcomingDischargeDT = datetime.now() # temp?
        self.sunWindowStart = 10
        self.sunWindowDuration = 3
        self.url = 'localhost'
        self.port = 5000
        self.fileList = []
        self.rules = {}

        # kind of not used
        self.Kp = 1.0
        self.Ki = 0.1
        self.step = 1
        #self.Kd = Kd
        self.previous_error = 0
        self.integral = 0

    # reads json config file and returns it as dict
    def getRules(self, fn:str) -> Dict:
        # Read data from a JSON file
        try:
            with open(fn, "r") as json_file:
                self.rules = json.load(json_file)

                try:
                    self.setTimes()
                    #self.pvSetPoint = self.rules['battery']['pvSetPoint']
                    #self.minSetPoint = self.rules['battery']['minSetPoint']
                    print('ingested rules! tastes good!')
                except:
                    print('failed to ingest rules.')
                return self.rules
        except Exception as e:
            print(f"Error during reading {fn} file: {e}")
            return {}

    # send get request
    # type = json, text, or status_code
    # to do, port should be before timeout with a default value of 80
    async def send_get_request(self, ip:str, port:int,endpoint:str,type:str,timeout=1) -> Any:
        """Send GET request to the IP."""
        try:
            response = requests.get(f"http://{ip}:{port}{endpoint}", timeout=timeout)
            if type == 'json':
                return response.json()
            elif type == 'text':
                return response.text
            else:
                return response.status_code
        except requests.Timeout as e:
            return e
        except Exception as e:
            return e

    async def send_secure_get_request(self, url:str,key:str='',type:str='json',timeout=2) -> Any:
        """Send GET request to the IP."""
        try:
            headers = {"Content-Type": "application/json; charset=utf-8"}

            if key != '':
                headers = {"Authorization": f"Bearer {key}"}

            response = requests.get(url, headers=headers, timeout=timeout)
            if type == 'json':
                return response.json()
            elif type == 'text':
                return (response.text, response.status_code)
            else:
                return response.status_code
        except requests.Timeout as e:
            return e
        except Exception as e:
            return e

    async def send_post_request(self,url:str, data:Dict={}, key:str='',timeout=1)-> Any:

        headers = {"Content-Type": "application/json; charset=utf-8"}

        if key != '':
            headers = {"Authorization": f"Bearer {key}"}

        response = requests.post(url, headers=headers, json=data)

    async def send_patch_request(self,url:str, data:Dict={}, key:str='',timeout=1):

        headers = {"Content-Type": "application/json; charset=utf-8"}

        if key != '':
            headers = {"Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {key}"}

        response = requests.patch(url, headers=headers, json=data)

        if response.ok:
            return response.json()
        else:
            print(f'{response.status_code}')
            return False

    # set time variables based on ingested rules file
    # to do: dont create new variables, just convert the old ones to DT format!!!
    def setTimes(self)-> None:
        dt = self.rules['battery']['dischargeTime']
        et = self.rules['event']['startTime']
        ed = self.rules['event']['durationHours']
        ued = self.rules['event']['eventDate']

        # TO DO: add in conditionals for uneven hours
        ehm = et.split(':')
        edhm = ed.split(':')
        self.eventDurationH = int(edhm[0])
        self.eventStartT = time(hour=int(ehm[0]),minute=int(ehm[1]))

        dm = int(ehm[1]+edhm[1]) # total minutes
        dh = int(ehm[0]) + int(edhm[0]) # duration hours
        if dm >= 60:
            dh = dh + int(dm/60)
            dm = dm%60
        self.eventEndT = time(hour=int(dh),minute=int(dm))

        try:
            if ued !='':
                self.eventDT = datetime.strptime(ued, "%Y-%m-%d %H:%M:%S")
        except:
            print('failed to set eventDT')

        hm = dt.split(':')
        self.dischargeT = time(hour=int(hm[0]),minute=int(hm[1])) # discharge time should be set based on behavior

        # initialize discharge datetime
        if datetime.now() > datetime.combine(datetime.now().date(),self.dischargeT):
            self.upcomingDischargeDT = datetime.combine((datetime.now()+timedelta(days=1)),self.dischargeT)
        else:
            self.upcomingDischargeDT = datetime.combine((datetime.now()),self.dischargeT)

    # set discharge datetime for tomorrow
    def setNextDischargeDT(self):
        tom = datetime.now().date()+timedelta(days=1)
        self.upcomingDischargeDT = datetime.combine(tom,self.dischargeT)
    # sets battery capacity and determines maximum automatable flexibility

    def setBatCap(self,Wh:int) -> None:
        try:
            if Wh != '':
                self.batCapWh = int(Wh)
                self.maxFlexibilityWh = self.getAvailableFlex(100)
        except Exception as e:
            print(f'Exception setting battery capacity: {e}')

    # checks if a datetime is after that day's sunwindow
    def isAfterSun(self,dt:datetime) -> bool:
        sWE = time(hour=int(self.sunWindowStart + self.sunWindowDuration)) # gets the end time of the sun window

        #if its after sun window
        upcomingSunWindowEnd = datetime.combine(dt,sWE) #combine provided datetime with sunwindow end to get a datetime object
        if dt > upcomingSunWindowEnd:
            print(f'Sun window closed at {upcomingSunWindowEnd}')
            return True
        else:
            print(f'Sun window closes at {upcomingSunWindowEnd}')
            return False

    # # checks if a datetime is after that day's sunwindow
    # def isAfterChargetime(self,dt:datetime) -> bool:

    #     if dt > upcomingChargeTime:
    #         return True
    #     else:
    #         return False

    # args: a dataframe with a datetime column with only one days worth of data
    # returns a Tuple with the start and end times for the event window as datetime objects for a given day
    def getStartEndDatetime(self, df)->Tuple:
        #df['datetime']=pd.to_datetime(df['datetime'])
        fileDate = datetime.date(df['datetime'].iloc[0])
        startDT = datetime.combine(fileDate,self.eventStartT)
        endDT = datetime.combine(fileDate,self.eventEndT)
        return (startDT, endDT)

    #filters a df for an individual day with datetime values to only those within the event window
    #args: pass a dataframe with the datetime column
    def filterEventWindow(self,df:pd.DataFrame) -> pd.DataFrame:
        #get date
        # df['datetime']=pd.to_datetime(df['datetime'])
        # fileDate = datetime.date(df['datetime'].iloc[0])
        startEnd = self.getStartEndDatetime(df)
        #startList.append(startDT)
        #endDT = datetime.combine(fileDate,self.eventEndDT)
        return df[(df['datetime']>=startEnd[0]) & (df['datetime']<startEnd[1])]

    # buckets df with datetime within an event window into hourly buckets
    # pass in a dataframe with datetimes
    # args
    def hourlyBucket(self,tempDF, tempStart:list) -> list[pd.DataFrame]:
        hourlyPower = []
        for h in range(self.eventDurationH):
            ts = tempStart + timedelta(hours=h)
            te = tempStart + timedelta(hours=h + 1)
            filteredTempDF = (tempDF[(tempDF['datetime']> ts) & (tempDF['datetime']<= te)]).copy() #data within the hour
            #filteredTempDF['increments'] = (filteredTempDF['datetime']-ts).total_seconds()

            filteredTempDF = self.increments(filteredTempDF,ts)

            hourlyPower.append(filteredTempDF)
        return hourlyPower

    #args: a dataframe with datetime column
    # returns df with added increments column based on an hour
    def increments(self,df,fm=0)->pd.DataFrame:
        if fm==0:
            firstMeasurement = df['datetime'].min()
        else:
            firstMeasurement = fm

        #print(firstMeasurement)
        incList = []
        for r in range(len(df['datetime'])):
            incSec = (df['datetime'].iloc[r] - firstMeasurement).total_seconds()/60/60 #must convert back from seconds
            incList.append(incSec)
        df['increments'] = incList
        return df

    #args: power and time increments (relative to the hour) for a given hour
    # returns the energy (Wh) for the hour
    def getWh(self,p:list[float],t:list[datetime])->float:
        e = trapezoid(y=p, x=t)
        return e

    # returns the available flexibility in WhAC
    # pass in battery percentage
    def getAvailableFlex(self,perc:Any)->float:
        if perc > 1.0:#convert percentage to decimal if needed
            perc = perc * .01

        f = ((self.batCapWh * perc) - (self.batCapWh * (1-self.dod))) * self.invEff

        if f < 0:
            f =0
        return f

    # returns all file names within the last X days
    async def getRecentFileList(self,d:int=30)->list:
        self.fileList = await self.send_get_request(self.url, self.port,'/api/files','json',timeout=2)
        self.fileList = sorted(self.fileList, reverse=True)

        # start with todays date
        checkFile = date.today()
        recentFileNames = [] #store most recent found file names

        #look for files within the last X days
        for days in range(1,d+1):
            for f in self.fileList: # loop through file list to get recent
                if str(checkFile) in f:
                    # add file to recent files
                    recentFileNames.append(f)
                    break
            checkFile = checkFile - timedelta(days=1)

        return recentFileNames

    # retrieves recent CSV files for specified amount of days
    # returns list of data by day in df format
    async def getRecentData(self,d:int=30)-> pd.DataFrame:
        # get list of recent files for specified number of past days
        recentFileNames = await self.getRecentFileList(d)

        #format list for API call
        formattedFn = []
        for f in recentFileNames:
            formattedFn.append(f.split('.')[0])

        #print(formattedFn)

        # fetch data
        tasks = [self.send_get_request(self.url, self.port,f"/api/data?file={fn}",'text') for fn in formattedFn]
            #r = await self.send_get_request(self.url, self.port,f"/api/data?files={fn}",'text')
        responses = await asyncio.gather(*tasks)

        data = []
        for r in responses:
            data.append(pd.read_csv(StringIO(r))) #convert files to df

        #convert datetime columns to datetime objects from str
        for d in range(len(data)):
            data[d]['datetime']=pd.to_datetime(data[d]['datetime'])

        return data

    # estimate DR baseline for the specified event window
    async def estBaseline(self, d:int=30, files:list=None)->float:

        data=[]
        if files == None:
            data = await self.getRecentData(d)
        else:
            for index, file in enumerate(files):
                data.append(file)
                if index >= d-1:
                    break

        # filter out all data except for event window
        filteredDF = []
        startList = []
        for d in data:
            startList.append(self.getStartEndDatetime(d)[0])
            filteredDF.append(self.filterEventWindow(d))

        # create hourly buckets for each day
        hourlyPower = []
        for i in range(len(startList)):
            hourlyPower.append(self.hourlyBucket(filteredDF[i],startList[i]))

        # get energy by hour by day
        listSums = []
        for d in hourlyPower:
            sumEnergy = 0
            #print('')
            for h in range(len(d)):
                hourlyEnergy = self.getWh(d[h]['powerstation_inputWAC'],d[h]['increments'])# change from inputWAC to whatever is more appropriate
                if (math.isnan(hourlyEnergy)):
                    hourlyEnergy = 0.0
                #print(f'{h}: {hourlyEnergy}')
                sumEnergy += hourlyEnergy
            #print(f'tot: {sumEnergy}')
            listSums.append(sumEnergy)

        return sum(listSums)/len(listSums)

    # determines AC energy draw or demand for a given range
    # assumes NaN = 0W
    # args: start datetime, end datetime, power columns to sum
    # async def trackWh(self,start: datetime, end:datetime='now', cols:list[str]=['relay1_power','relay2_power'])->float:
    #     if end == 'now':
    #         end = datetime.now()

    #     # determine days of data based on starting value
    #     d = int((end - start).days + 1)
    #     data = await self.getRecentData(d)

    #     #merge files - this is wrong!!!
    #     allData = data[0].copy()
    #     for d in range(1,len(data)):
    #         allData = pd.concat([allData, data[d]], ignore_index=True)

    #     allData = allData.sort_values(by='datetime').reset_index(drop=True)

    #     filteredData = allData[(allData['datetime']>=start) & (allData['datetime']<end)]

    #     #fill NaN with 0
    #     filteredData = filteredData.fillna(0)

    #     filteredData = self.increments(filteredData)

    #     # columns in the data with values to sum
    #     summedData = filteredData.copy()
    #     summedData['summedPower'] = filteredData[cols].sum(axis=1)

    #     return self.getWh(summedData['summedPower'],summedData['increments'])

    # attempts to reach a certain amount of energy avoidance - not in use
    def pi_controller_energy(self, setpoint, pv, kp, ki,):
        error = setpoint - pv
        self.integral += error * dt
        control = kp * error + ki * self.integral
        return control, error, integral

    # determines solar window, solar production
    # to do: determine PV-to-battery efficiency
    async def analyzeSolar(self,d:int=30, files:list=None)->Tuple:

        data=[]
        if files == None:
            data = await self.getRecentData(d)
        else:
            for index, file in enumerate(files):
                data.append(file)
                if index >= d-1:
                    break

        # filter out all data without PV input
        filteredDF = []
        for d in data:
            newD = d[d['powerstation_inputWDC']>0]
            filteredDF.append(newD)
        
        #drop unneeded columns
        trimmedDf = []
        cols=['datetime','powerstation_percentage','powerstation_inputWAC','powerstation_inputWDC','powerstation_outputWAC','powerstation_outputWDC']
        for d in filteredDF:
            if not d[cols].empty: #filter out empties
                trimmedDf.append(d[cols])

        # create list[Dict] with analysis results
        metaList = []
        for df in trimmedDf:
            meta={}
            meta['raw min time']=df['datetime'].min()
            meta['raw max time']=df['datetime'].max()
            meta['max power W']=float(df['powerstation_inputWDC'].max())
            meta['max power time']=df[df['powerstation_inputWDC']==df['powerstation_inputWDC'].max()]['datetime']
            try:
                meta['power std']=statistics.stdev(df['powerstation_inputWDC'])
            except:
                meta['power std']=float('nan')
            try:
                meta['power mean']=statistics.mean(df['powerstation_inputWDC'])
            except:
                meta['power mean']=float('nan')
            metaList.append(meta)

        # get sun window (2 std deviations)
        stdDf = []
        amountStd = 1
        for i in range(len(trimmedDf)):
            stdDf.append(trimmedDf[i][(trimmedDf[i]['powerstation_inputWDC']<= metaList[i]['power mean']+(amountStd*metaList[i]['power std'])) &
                            (trimmedDf[i]['powerstation_inputWDC']>= metaList[i]['power mean']-(amountStd*metaList[i]['power std']))])

        for m in range(len(metaList)):
            metaList[m]['sun window min']=stdDf[m]['datetime'].min()
            metaList[m]['sun window max']=stdDf[m]['datetime'].max()
            metaList[m]['sun window duration']= metaList[m]['sun window max'] - metaList[m]['sun window min']
            metaList[m]['PV Wh DC'] = float(self.getWh(stdDf[m]['powerstation_inputWDC'],self.prepWh(stdDf[m])['increments']))
            #metaList[m]['percentage input'] = 

        sunWindowMin = []
        sunWindowMax = []
        sunWindowDuration = []
        dcIn = []

        for m in metaList:
            sunWindowMin.append(m['sun window min'])
            sunWindowMax.append(m['sun window max'])
            sunWindowDuration.append(m['sun window duration'])
            dcIn.append(m['PV Wh DC'])

        listAvg = {'sunWindowMin':self.avgTimes(sunWindowMin),
                   'sunWindowMax':self.avgTimes(sunWindowMax),
                   'sunWindowDuration':self.avgTimes(sunWindowDuration),
                   'maxPVWh':max(dcIn),
                   'dailyPVWh':statistics.mean(dcIn)}

        return (metaList,listAvg)

    # get Wh at each sensor point
    # returns a tuple - 1st elements is a dictionary for each available file, 2nd element is averages
    # note - this is raw data and doesn't take into account conversion efficiencies or sun window
    async def analyzeDailyWh(self,d:int=30,files:list=None)->Tuple[Dict,Dict]:

        data=[]
        if files == None:
            data = await self.getRecentData(d)
        else:
            for index, file in enumerate(files):
                data.append(file)
                if index >= d-1:
                    break

        filteredDF = []
        for d in data:
            # get columns of interest
            try:
                cols=['datetime','powerstation_percentage','powerstation_inputWDC','relay1_power','relay2_power','relay3_power']
                filteredDF.append(d[cols])
            except Exception as e:
                #print(f'{e}')
                pass
                      
        print(len(filteredDF))
        print('')
        # create list[Dict] with analysis results
        metaDict = {}

        runningS1 = []
        runningS2 = []
        runningS3 = []
        runningS4 = []
        runningL = []
        runningG = []

        for m in range(len(filteredDF)):
            meta={}
            meta['S1 Wh AC'] = float(self.getWh(filteredDF[m]['relay1_power'].fillna(0),self.prepWh(filteredDF[m])['increments']))
            runningS1.append(meta['S1 Wh AC'])
            meta['S2 Wh AC'] = float(self.getWh(filteredDF[m]['relay2_power'].fillna(0),self.prepWh(filteredDF[m])['increments']))
            runningS2.append(meta['S2 Wh AC'])
            meta['S3 Wh AC'] = float(self.getWh(filteredDF[m]['relay3_power'].fillna(0),self.prepWh(filteredDF[m])['increments']))
            runningS3.append(meta['S3 Wh AC'])
            meta['S4 Wh DC'] = float(self.getWh(filteredDF[m]['powerstation_inputWDC'].fillna(0),self.prepWh(filteredDF[m])['increments']))
            runningS4.append(meta['S4 Wh DC'])
            meta['load Wh AC'] = meta['S1 Wh AC'] + meta['S3 Wh AC']
            runningL.append(meta['load Wh AC'])
            meta['total grid demand'] = meta['S1 Wh AC'] + meta['S2 Wh AC']
            runningG.append(meta['total grid demand'])

            metaDict[filteredDF[m].iloc[0]['datetime']]=meta

        avgDict={}

        for a in metaDict.keys():
            avgDict['days sampled'] = len(filteredDF)
            avgDict['S1 Daily Avg'] = statistics.mean(runningS1)
            avgDict['S2 Daily Avg'] = statistics.mean(runningS2)
            avgDict['S3 Daily Avg'] = statistics.mean(runningS3)
            avgDict['S4 Daily Avg'] = statistics.mean(runningS4)
            avgDict['load Daily Avg'] = statistics.mean(runningL)
            avgDict['grid Daily Avg'] = statistics.mean(runningG)

        return (metaDict,avgDict)

    # cleans data
    def prepWh(self, df:pd.DataFrame)->pd.DataFrame:
        #fill NaN with 0
        df = df.fillna(0)
        df = self.increments(df)
        return df

    #get average time from list of datetime or timedelta objects
    def avgTimes(self,dtL:list[datetime])->time:
        # to numeric
        timeToNum = []
        for t in dtL:
            #check timedelta
            if 'timedelta' in str(type(t)):
                timeToNum.append(t.seconds)
            #t = t.to_pydatetime()
            # print(type(t))
            else:
                if math.isnan(t.hour):
                    continue
                timeToNum.append((t.hour*60*60)+(t.minute*60))

        #print(timeToNum)
        x = statistics.mean(timeToNum)
        xMin = x / 60
        h = int(xMin/60)
        m = int(xMin%60)
        return time(h,m)

    # pass in Wh (usually from analysis) and convert to % of full battery, without any derating
    def whToPerc(self, Wh:int)->int:
        return (Wh / self.batCapWh)*100

    # #estimate when the PV will start producing and for how long
    # async def estSunWindow(self,d:int=30):
    #     data = await self.getRecentData(d)

    #     # filter out all data without PV input

    #     filteredDF = []
    #     for d in data:
    #         newD = d[d['powerstation_inputWDC']>0]
    #         filteredDF.append(newD)
    #     return filteredDF
    
    # get tomorrows weather
    def getWeather(self):
        pass

    #estimate recent daily average and max PV production(Wh)
    def estPV(self):
        # get 
        pass

    # maintains battery at level to utilize PV
    def utilizePV(self):
        pass

    def checkMode(self):
        pass


    def normalLoop(self,now):
        pass

    def eventUpcomingLoop(self):
        pass

    def eventOngoingLoop(self):
        pass
