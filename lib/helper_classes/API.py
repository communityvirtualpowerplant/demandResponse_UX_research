import os
import sys
import subprocess
import glob
import pandas as pd
from typing import Any, Dict, Optional, List
import logging

logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.DEBUG)

class API():
    def __init__(self,dd:str):
        self.dataPath = dd
        self.static_folder='../frontend/static'
        self.template_folder='../frontend/templates'

    def getMostRecent(d,s):

        file_pattern = os.path.join(f'{d}/{s}', f"*.csv")
        files = sorted(glob.glob(file_pattern))
        fileName = files[-1]

        fullFilePath = os.path.join(filePath, fileName) #os.path.join(fileName)
        df = pd.read_csv(fullFilePath)  # Update path as needed

        return [df, fileName]

    # run subprocess
    def run_command(self, cmd):
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr.strip()}"
        except Exception as e:
            return f"Exception: {str(e)}"


    def parse_disk_usage(self):
        stat = os.statvfs("/")

        total = stat.f_frsize * stat.f_blocks      # Total space
        free = stat.f_frsize * stat.f_bavail       # Available space
        used = total - free

        total_mb = total // (1024 * 1024)
        used_mb = used // (1024 * 1024)
        free_mb = free // (1024 * 1024)
        percent_used = round((used / total) * 100, 1)

        diskDict =  {
            "total_mb": total_mb,
            "used_mb": used_mb,
            "free_mb": free_mb,
            "percent_used": percent_used
        }

        return diskDict

    #parse timestamp
    def parse_timestamp(self, filename, startDate:str, time_format:str="%Y-%m-%d",):
        fileDate = filename.split("_")[-1].replace(".csv","")
        if fileDate and (fileDate != str(datetime.date.today())): #ignore today's file
            formattedFileDate = datetime.datetime.strptime(fileDate, time_format)
            if startDate == None:
                return formattedFileDate
            if formattedFileDate > datetime.datetime.strptime(startDate, time_format): #filter by start date
                return formattedFileDate
            return None
        return None


    def check_mmc_errors(self):
        dmesg_output = self.run_command("dmesg | grep mmc")

        error_keywords = ["error", "fail", "timeout", "crc", "interrupt", "reset", "re-init"]
        warnings = [
            line for line in dmesg_output.splitlines()
            if any(kw.lower() in line.lower() for kw in error_keywords)
        ]

        return warnings

    # startDate is used if there are test files that should be excluded
    def check_file_size_uniformity(self, folder_path:str, startDate=None,tolerance_ratio:float=0.2)->Dict:
        interval_minutes=60*60*24
        file_data=[]
        for f in os.listdir(folder_path):
            try:
                full_path = os.path.join(folder_path, f)
                if os.path.isfile(full_path):
                    ts = self.parse_timestamp(f,startDate)
                    if ts:
                        size = os.path.getsize(full_path)
                        file_data.append((f, ts, size))
            except Exception as e:
                logging.error(f'{e}')

        if not file_data:
            return "No timestamped files found in directory."

        # Sort by timestamp
        file_data.sort(key=lambda x: x[1])
        sizes = [s for _, _, s in file_data]
        avg = sum(sizes) / len(sizes)
        lower_bound = avg * (1 - tolerance_ratio)
        upper_bound = avg * (1 + tolerance_ratio)

        outliers = [(f, s) for f, _, s in file_data if s < lower_bound or s > upper_bound]

        # Find missing timestamps
        expected_ts = []
        current = file_data[0][1]
        end = file_data[-1][1]
        while current <= end:
            expected_ts.append(current)
            current += timedelta(minutes=interval_minutes)

        existing_ts = set(ts for _, ts, _ in file_data)
        missing_ts = [dt for dt in expected_ts if dt not in existing_ts]

        return {
            "total_files": len(file_data),
            "startDate" : startDate,
            "average_size_bytes": avg,
            "outliers": outliers,
            "missing_timestamps": [dt.strftime("%Y-%m-%d %H:%M") for dt in missing_ts],
            "status": "OK" if not outliers and not missing_ts else "WARNING: Issues found"
        }
