import datetime
import json
import asyncio
import logging
import requests
from typing import Any, Dict, Optional, List

# ------------------ Airtable Class ------------------ #
class Airtable():
    def __init__(self, key:str, base:str,table:str, name:str=''):
        self.key = key
        self.baseURL = 'https://api.airtable.com/v0/'
        self.base = base
        self.table = table
        self.IDs = []
        self.names=[]

    async def listRecords(self):
        try:
            res = await self.send_secure_get_request(f'{self.baseURL}{self.base}/{self.table}')
            return res
        except Exception as e:
            logging.error(e)
        return None

    # retrieves record IDs by name column (if name column exists)
    async def getRecordIDbyName(self,name:List)-> List:
        IDlist = []
        for n in name:
            logging.debug(name)
            try:
                # get list of records filtered by date

                mURL = f'{self.url}{self.table}?maxRecords=3&view=Grid%20view&filterByFormula=name%3D%22{n}%22' #filter results by name column
                res = await self.send_secure_get_request(mURL)
                logging.debug(res)

                # pull the id for the first record
                recordID = res['records'][0]['id']
                IDlist.append(recordID)
                logging.debug(recordID)
            except Exception as e:
                logging.error(e)

        return IDlist

    # updates up to 10 records at once
    # https://airtable.com/developers/web/api/update-multiple-records
    async def updateBatch(self, names:List, recordIDs:List,data:List):
        logging.debug(names)

        records = []
        for n in range(len(names)):
            if data[n]=={}:
                continue
            try:
                logging.debug(f'{names[n]}!')

                # patch record - columns not included are not changed
                # keys in data must be identical to Airtable columns
                records.append({
                    "id": str(recordIDs[n]),
                    "fields": {
                        "name": str(names[n]),
                        **{key: str(value) for key, value in data[n].items()}
                        }
                    })
            except Exception as e:
                logging.error(f'Exception while formatting sensor data: {e}')

            pData={"records": records}

            logging.debug(pData)

            try:

                patch_status = 0
                while patch_status < 3:
                    # note that patch leaves unchanged data in place, while a post would delete old data in the record even if not being updated
                    r = await self.send_patch_request(f'{self.url}{self.table}',pData)
                    if r != False:
                        break
                    await asyncio.sleep(1+patch_status)
                    patch_status += 1
                logging.debug(r)
            except Exception as e:
                logging.error(f'Exception while patching Airtable: {e}')

    async def send_secure_get_request(self, url:str,type:str='json',timeout=2) -> Any:
        """Send GET request to the IP."""
        try:
            headers = {"Content-Type": "application/json; charset=utf-8"}

            if self.key != '':
                headers = {"Authorization": f"Bearer {self.key}"}

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

    async def send_patch_request(self, url:str, data:Dict={},timeout=1):

        headers = {"Content-Type": "application/json; charset=utf-8"}

        if self.key != '':
            headers = {"Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {self.key}"}

        response = requests.patch(url, headers=headers, json=data)

        if response.ok:
            return response.json()
        else:
            logging.warning(f'{response.status_code}: {response.text}')
            return False

    def parseListToDF(self,res):
        fields = []
        for r in res['records']:
            fields.append(r['fields'])

        df = pd.DataFrame(data=fields)
        df['date'] = pd.to_datetime(df['date'])

        return df
