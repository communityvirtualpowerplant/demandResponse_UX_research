import asyncio
import requests
from datetime import datetime, timedelta
import pandas as pd
from scipy.integrate import trapezoid
import math
from statistics import mean
from io import StringIO
import logging
import random
import subprocess

logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.INFO)

class Helpers():
    async def send_get_request(self,url:str='http://localhost:5000/',endpoint:str='',type:str='json',key=None,timeout=1):
        """Send GET request to the IP."""
        # get own data
        max_tries = 3

        if key:
            headers = {"Authorization": f"Bearer {key}"}
        else:
            headers = {}

        for attempt in range(max_tries):
            try:
                response = requests.get(f"{url}{endpoint}",headers=headers, timeout=timeout)
                response.raise_for_status()
                if type == 'json':
                    res= self.parse_datetimes(self.convert_bools(response.json()))
                elif type == 'text':
                    res= response.text
                else:
                    res= response.status_code
                break
            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP error occurred: {e}")
            except Exception as e:
                logging.error(f'{e}')
                if attempt == max_tries-1: # try up to 3 times
                    return None
                else:
                    logging.debug('SLEEEEEEEEEEEEEEEEEPING')
                    await asyncio.sleep(1+attempt)
        return res

    # convert datetimes to iso formatted strings
    def convert_datetimes(self, obj):
        if isinstance(obj, dict):
            return {k: self.convert_datetimes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_datetimes(i) for i in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    # convert to datetimes from iso formatted strings
    def parse_datetimes(self,obj):
        if isinstance(obj, dict):
            return {k: self.parse_datetimes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.parse_datetimes(i) for i in obj]
        elif isinstance(obj, str):
            try:
                return datetime.fromisoformat(obj)
            except ValueError:
                return obj
        else:
            return obj

    # Function to recursively convert "true"/"false" strings to Booleans
    def convert_bools(self, obj):
        if isinstance(obj, dict):
            return {k: self.convert_bools(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_bools(elem) for elem in obj]
        elif obj == "true":
            return True
        elif obj == "false":
            return False
        else:
            return obj

    def getUpdate(self):
        result = subprocess.run(
                ['git', 'pull'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

        if not 'Already up to date' in result.stdout:
            logging.info('Pulled update... rebooting now')
            os.system('sudo reboot')
        else:
            logging.info('Already up to date')

    # async def startCheck(self):
    #     #stagger the start randomly
    #     await asyncio.sleep(random.randint(0,60))

    #     count = 0
    #     while True:
    #         try:
    #             rCode = await send_get_request(endpoint='api/discover',type='code')
    #             logging.info(rCode)
    #             if rCode == 200:
    #                 return None
    #         except Exception as e:
    #             logging.error(e)
    #         logging.info('still waiting!')
    #         count = count + 1
    #         await asyncio.sleep(20+(count**2))

class DRUX_Baseline(Helpers):
    def __init__(self,st:int=None,pe:list=None):
        super()
        self.method = 'avg'
        self.eventStartTime = st # start time
        self.holidays = ['2025-09-01']
        self.pastEventDates = pe # past event dates
        self.DLRPrate = 18
        self.CSRPrate = 18

    async def getCBL(self,eDF,eTime):
        #self.eventStartTime = eTime

        # drop unnecessary columns
        try:
            eDF = eDF.drop(columns=['modified','notes','network'])
        except:
            logging.error(e)

        pastEventsDF=eDF[eDF['date']<datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)]

        self.pastEventDates = [d.date() for d in list(pastEventsDF['date'])]

        if self.method == 'avg':
            return await self.calcAverageDayMethod(eTime)
        else:
            return await self.calcWeatherSensitiveMethod()

    async def calcAverageDayMethod(self,eTime):
        # get data for up to the past 30 days
        data = await self.getPastData()

        #filter all data to event windows
        windowData = self.getEventWindows(data,eTime)
        windowDict= self.listToDict(windowData)

        windowDictBuckets = {}
        for k,v in windowDict.items():
            # create hourly buckets for each day
            formattedStartTime = v['datetime'].iloc[0].replace(hour=eTime,minute=0,second=0,microsecond=0)
            hourly = self.hourlyBuckets(v,formattedStartTime)

            # add increments within each hour
            incs = []
            for i,h in enumerate(hourly):
                # the increments function adds a column for the increment of a specific datapoint
                incs.append(self.increments(h,formattedStartTime+timedelta(hours=i)))

            hourlyEnergy = []
            for inc in incs:
                hourlyEnergy.append(self.getWh(inc['ac-W'],inc['increments']))
                if (math.isnan(hourlyEnergy[-1])):
                    hourlyEnergy[-1] = 0.0

            windowDictBuckets[k]=hourlyEnergy

        peakLoad = 0
        for k,v in windowDictBuckets.items():
            for i,h in enumerate(v):
                peakLoad = max(peakLoad,h)

        filteredBuckets = {}
        pastEventPriorDates = [d - timedelta(days=1) for d in self.pastEventDates]
        for k,v in windowDictBuckets.items():
            kDT = datetime.strptime(k, "%Y-%m-%d")
            #drop holidays
            if not (k in self.holidays):
                #drop DR event days
                if not (kDT.date() in self.pastEventDates):
                    #drop DR event prior days
                    if not (kDT.date() in pastEventPriorDates):
                        # drop weekends
                        if kDT.weekday() <=4: # filter out weekends
                            filteredBuckets[k]=v

        tD = self.tenDayCBL(filteredBuckets,peakLoad)
        CBLbasis = self.fiveDayCBL(tD)

        return self.avgCBL(list(CBLbasis.keys()), filteredBuckets)

    async def calcWeatherSensitiveMethod(self):
    	return None

    async def getPastData(self):
        # get file list
        fileList = await self.send_get_request('http://localhost:5000/api/files?source=plugs',type='json')
        logging.debug(f'all files: {fileList}')

        filteredFileList = []
        for f in fileList:
            dStr = f.split('_')[1].replace('.csv','')
            dDt = datetime.strptime(dStr, "%Y-%m-%d")
            # get only dates within the last 30 days
            if datetime.now() - dDt <= timedelta(days=30):
                filteredFileList.append(dDt)
        logging.debug(f'filtered file list: {filteredFileList}')

        data = []
        for f in filteredFileList:
            #filter out today's data
            fToGet = f.strftime("%Y-%m-%d")
            if datetime.now().date().strftime("%Y-%m-%d")  not in fToGet:
                r = await self.send_get_request(f'http://localhost:5000/api/data?source=plugs&date={fToGet}',type='text')
                if type(r) == tuple: # the tuple includes the response code, which we don't care about
                    r = r[0]
                data.append(r)

        #parse response
        parsedData = []
        for d in data:
            tempDF = pd.read_csv(StringIO(d), na_values=["", "NA", "NaN", "null", "NULL"])
            tempDF['datetime'] = pd.to_datetime(tempDF['datetime'])
            cleanedTempDF = tempDF.dropna()
            parsedData.append(cleanedTempDF)

        return parsedData

    # get event windows
    def getEventWindows(self, data,eTime):
        eW = []
        for d in data:
            #get on timestamps between event start and end times
            eW.append(d[[(d > d.replace(hour=eTime,minute=0,second=0,microsecond=0)) and (d <= d.replace(hour=eTime+4,minute=0,second=0,microsecond=0)) for d in d['datetime']]])

        return eW

    # get event windows
    def listToDict(self, data):
        rD = {}
        for d in data:
            if len(d)>0:
                rD[d['datetime'].iloc[0].date().strftime("%Y-%m-%d")]=d

        return rD

    # buckets df with datetime within an event window into hourly buckets
    # args: a dataframe with datetimes
    def hourlyBuckets(self,tempDF, tempStartTime:float, eventDuration:float=4) -> list[pd.DataFrame]:
        hourlyPower = []
        for h in range(eventDuration):
            #print(tempDF['datetime'])
            ts = tempStartTime + timedelta(hours=h)
            te = tempStartTime + timedelta(hours=h + 1)
            filteredTempDF = (tempDF[(tempDF['datetime']> ts) & (tempDF['datetime']<= te)]).copy() #data within the hour
            #filteredTempDF = increments(filteredTempDF,ts)
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

    def tenDayCBL(self,b,p):
        cblWindowAvg = {}
        avgList = []

        # loop backwards through dates
        for d in range(1,31):
            checkD = datetime.now().date() - timedelta(days=d)
            checkDstr = checkD.strftime("%Y-%m-%d")

            if checkDstr in list(b.keys()):
                if mean(b[checkDstr])> p * .25:
                    if len(cblWindowAvg.keys()) == 0:
                        p = mean(b[checkDstr])
                    else:
                        avgList.append(mean(b[checkDstr]))
                        p = mean(avgList)
                    cblWindowAvg[checkDstr]=mean(b[checkDstr])

            if len(cblWindowAvg.keys()) >= 10:
                break

        # if not enough days, repeat without removing low days
        if len(cblWindowAvg.keys()) < 10:
            cblWindowAvg = {}
            avgList = []
            # loop backwards through dates
            for d in range(1,31):
                checkD = datetime.now().date() - timedelta(days=d)
                checkDstr = checkD.strftime("%Y-%m-%d")
                if checkDstr in list(b.keys()):
                    cblWindowAvg[checkDstr]=mean(b[checkDstr])
                if len(cblWindowAvg.keys()) >= 10:
                    break

        return cblWindowAvg

    #get highest 5
    def fiveDayCBL(self,t):
        allV = list(t.values())
        allV.sort(reverse=True)

        f = {}
        for v in allV:
            for k,vt in t.items():
                if v == vt:
                    f[k]=v
        return f

    def avgCBL(self,dates,buckets):
        hourlyLists = [[],[],[],[]]
        for d in dates:
            hourlyLists[0].append(buckets[d][0])
            hourlyLists[1].append(buckets[d][1])
            hourlyLists[2].append(buckets[d][2])
            hourlyLists[3].append(buckets[d][3])
        hourlyAvg = []
        for h in hourlyLists:
            hourlyAvg.append(mean(h))

        return hourlyAvg

    async def getOngoingPerformance(self, eTime:float,eType:str,eBaseline:list[float],buttonTracker={'onPause':[0],'offPause':[0]}):

        # get today's file
        today = datetime.now().date()
        formattedStartTime = (datetime.now()).replace(hour=eTime,minute=0,second=0,microsecond=0)

        try:
            r = await self.send_get_request(f'http://localhost:5000/api/data?source=plugs&date={today.strftime("%Y-%m-%d")}',type='text')
            if type(r) == tuple:
                r = r[0]
            data=r

            tempDF = pd.read_csv(StringIO(data))
            tempDF['datetime'] = pd.to_datetime(tempDF['datetime'])
            parsedData = tempDF

            # get event window
            eventWindow = parsedData[[(d > d.replace(hour=eTime,minute=0,second=0,microsecond=0)) and (d <= d.replace(hour=eTime+4,minute=0,second=0,microsecond=0)) for d in parsedData['datetime']]]


            # create hourly buckets for each day
            hourly = self.hourlyBuckets(eventWindow,formattedStartTime)
            # the increments function adds a column for the increment of a specific datapoint
            incs = []
            dataLens = []
            for i,h in enumerate(hourly):
                dataLens.append(len(h))
                incs.append(self.increments(h,formattedStartTime+timedelta(hours=i)))

            try:
                hourlyEnergy = []
                for i, inc in enumerate(incs):
                    resW = self.getWh(inc['ac-W'],inc['increments'])
                    if (not resW) or (math.isnan(resW)):
                        if resW != 0:
                            resW = -1 #indicates no data without breaking it
                    if dataLens[i] == 0:
                        resW = -1 #indicates no data without breaking it
                    hourlyEnergy.append(resW)
                logging.info(hourlyEnergy)
            except Exception as e:
                logging.error(f"Can't get hourly energy: {e}")
                hourlyEnergy = 'NaN'

            # if no data
            if (len(hourlyEnergy) == 0) or (hourlyEnergy=='NaN'):
                hourlyEnergy = 'NaN'
                avgHourlyEnergy = hourlyEnergy
                goalPerc = 'NaN'
                avgGoalPerc = 'NaN'
                flexW = 'NaN'
                avgFlexW = flex
            else:
                hourlyEnergy = [float(h) for h in hourlyEnergy] #remove?

                avgHourlyEnergy = mean([h for h in hourlyEnergy if h != -1])

                goalPerc = []
                flexW = []
                for i,v in enumerate(hourlyEnergy):
                    if v == -1:
                        goalPerc.append(0)
                        flexW.append(0)
                        continue
                    try:
                        f = eBaseline[i]-v #if negative flex needs to be ignored, include max() here
                        flexW.append(f)
                        goalPerc.append(f/eBaseline[i])
                    except Exception as e:
                        if 'float division by zero' in e:
                            logging.error(f'likely missing past data: {e}')
                        else:
                            logging.error(e)
                        goalPerc = [0,0,0,0]

                avgGoalPerc = mean(goalPerc) #this is NOT the performance factor, which is calculated later
                avgFlexW = mean(flexW)

            perf = {'datetime':formattedStartTime,
                    'goalPerc':goalPerc,
                    'goalAvg':avgGoalPerc,
                    'loadW_hourly':hourlyEnergy,
                    'loadW_avg':avgHourlyEnergy,
                    'flexW_avg':avgFlexW,
                    'flexW': flexW,
                    'baselineW':eBaseline,
                    'event':eType,
                    'button':buttonTracker}


        except Exception as e:
            logging.error(f"Can't get ongoing performance: {e}")
            perf = {'datetime':formattedStartTime,
                    'goalPerc':'NaN',
                    'goalAvg':0,
                    'loadW_hourly':'NaN',
                    'loadW_avg':0,
                    'flexW_avg':0,
                    'flexW': 'NaN',
                    'baselineW':'NaN',
                    'event':eType,
                    'button':'NaN'}

        return perf

    async def getAvgReduction(self,eType,mon):
        performance = await self.send_get_request('http://localhost:5000/api/performance',type='json')

        #filter performance by event type
        filteredPerformance = {}
        for k,v in performance.items():
            if v['event']==eType:
                #filter by month
                if int(k.split('-')[1]) == mon:
                    filteredPerformance[k] = v

        # get all flexAvgs in kW
        allAvgFlexKW = []
        for k,v in filteredPerformance.items():
            allAvgFlexKW.append(v['flexW_avg']*.001)

        #totAvgFlexKW = mean(allAvgFlexKW)
        if len(allAvgFlexKW)>0:
            totAvgFlexKW = mean(allAvgFlexKW)
        else:
            totAvgFlexKW = 0

        return totAvgFlexKW

        #returns a tuple
    async def getPerformanceDollarValue(self,mon,cR=18,dR=18):
        c = await self.getAvgReduction('csrp',mon)
        d = await self.getAvgReduction('dlrp',mon)

        return (c * cR,d * dR)
