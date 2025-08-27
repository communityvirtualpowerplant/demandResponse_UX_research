from flask import Flask, render_template, render_template_string, request, send_file, abort, jsonify, make_response
from flask_cors import CORS
import csv
import datetime
from datetime import timedelta, date
import os
import sys
import glob
import json
import pandas as pd
import psutil
import logging
import subprocess

libdir = '/home/drux/demandResponse_UX_research/lib/helper_classes'
if os.path.exists(libdir):
    sys.path.append(libdir)

from API import API

logging.basicConfig(filename='/home/drux/demandResponse_UX_research/dashboard.log',format='%(asctime)s - %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',datefmt='%Y-%m-%d %H:%M:%S',level=logging.INFO)
#logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.INFO)

repoRoot = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
logging.debug(repoRoot)

try:
    with open(os.path.join(repoRoot,'config.json')) as f:
        config = json.load(f)
except Exception as e:
    logging.error(f"Error during reading config file: {e}")

participantNumber = int(config["participant"])

api = API(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),'data/'))

app = Flask(
    __name__,
    static_folder=api.static_folder,       # custom static folder
    template_folder=api.template_folder   # custom templates folder
)

def onStart():
    logging.info('starting dashboard')
    # disable wifi power saving
    os.system('sudo iw dev wlan0 set power_save off')
    #os.system('sudo /sbin/iwconfig wlan0 power off') # old way, still works but is depreciated

onStart()

# CORS is enabled for all routes. This simplifies the frontend visualization,
# but could be removed for security purposes or to more easily enforce throttling without straining the Pi Zeros.
CORS(app)

@app.route("/", methods=['GET'])
def index():
    return render_template('index.html')

@app.route("/today", methods=['GET'])
def today():
    #options: 'plugs' or 'powerstation'
    filePrefix = request.args.get("source")
    #file = request.args.get("date")

    file_pattern = os.path.join(api.dataPath, f"{filePrefix}*.csv")
    files = sorted(glob.glob(file_pattern))
    if len(files)>0:
        fileName = files[-1]
        with open(fileName, newline='') as f:
            reader = csv.reader(f)
            cols = next(reader)  # skip header
            rows = list(reader)#[-10:]  # last 10 readings
    else:
        cols = []
        rows = []
    return render_template('data.html', cols = cols, data=rows)

# upcoming and ongoing event info
@app.route("/api/state", methods=['GET'])
def getState():
    try:
        with open(os.path.join(repoRoot,'data/state.json'), "r") as jsonFile:
            data = json.load(jsonFile)
            return jsonify(data), 200
    except Exception as e:
        logging.error(f'Exception reading state.json: {e}')
        return jsonify({'error': str(e)}), 500

# upcoming and ongoing event info
@app.route("/api/performance", methods=['GET'])
def getPerformance():
    try:
        with open(os.path.join(repoRoot,'data/performance.json'), "r") as jsonFile:
            data = json.load(jsonFile)
            return jsonify(data), 200
    except Exception as e:
        logging.error(f'Exception reading performance.json: {e}')
        return jsonify({'error': str(e)}), 500

@app.route("/api/discover", methods=['GET'])
def discover():
    return jsonify({'name': config['participant']}), 200

@app.route("/api/data", methods=['GET'])
def get_csv_for_date():
    #options: 'plugs' or 'powerstation'
    filePrefix = request.args.get("source")
    file = request.args.get("date")

    if not filePrefix:
        return "Please provide source - either plugs or powerstation", 400
    if not file:
        return "Please provide file name in proper form (see api/files) or date=now for most recent data", 400

    if file == 'now':
        try:
            df = api.getMostRecent(api.dataPath,filePrefix)[0]
            last_row = df.iloc[-1].to_dict()
            return jsonify(last_row), 200
        except FileNotFoundError:
            return jsonify({'error': 'CSV file not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif file == 'recent':
        try:
            file_pattern = os.path.join(api.dataPath, f"{filePrefix}*.csv")
            files = sorted(glob.glob(file_pattern))
            fileName = files[-1]
            dn = fileName.split('/')[-1]
            return send_file(os.path.abspath(fileName), as_attachment=True, download_name=dn, mimetype='text/csv'), 200

        except FileNotFoundError:
            return jsonify({'error': 'CSV file not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        try:
            fileName = f'{filePrefix}_{file}.csv'

            file_pattern = os.path.join(api.dataPath, f"{filePrefix}*.csv")
            files = sorted(glob.glob(file_pattern))

            for f in files:
                if fileName in f:
                    return send_file(os.path.abspath(f), as_attachment=True, download_name=fileName, mimetype='text/csv'),200
        except FileNotFoundError:
            return jsonify({'error': 'CSV file not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route("/api/files", methods=['GET'])
def list_csv_files():
    filePrefix = request.args.get("source")

    if not filePrefix:
        return "Please provide source - either plugs or powerstation", 400

    # Get all CSV files in the data/ directory
    file_pattern = os.path.join(api.dataPath, f"{filePrefix}*.csv")
    files = sorted(glob.glob(file_pattern))

    # Return just the filenames (without full paths)
    filenames = [os.path.basename(f) for f in files]

    return jsonify(filenames), 200

@app.route("/api/health")
def health_check():
    # any run_command can also be entered manually in terminal
    dt = datetime.datetime.now()

    try:
        cpu_tempC = float(api.run_command("vcgencmd measure_temp").replace('temp=','').replace("\'C",""))
    except Exception as e:
        cpu_tempC = f"error: {str(e)}"

    try:
        uptime = api.run_command("uptime").split(',')[0]
    except Exception as e:
        uptime = f"error: {str(e)}"

    try:
        availMem = int(api.run_command("free -h").split('\n')[1].split()[-1].replace('Mi',''))
        memStatus = 'OK'
        if availMem < 50:
            memStatus = 'VERY LOW'
        elif availMem < 100:
            memStatus = 'LOW'
        memoryUsage = {'available memory':f'{availMem}Mi','status':memStatus}
    except Exception as e:
        memoryUsage = f"error: {str(e)}"

    try:
        diskUsage = api.parse_disk_usage()
    except Exception as e:
        diskUsage = f"error: {str(e)}"

    try:
        throttled = api.run_command("vcgencmd get_throttled")
        if "0x0" in throttled:
            throttled = "OK"
        else:
            throttled = "Power supply issue or undervoltage!"
        powerIssues = throttled
    except Exception as e:
        powerIssues = f"error: {str(e)}"

    try:
        sdCardErrors = api.check_mmc_errors()# run_command("dmesg | grep mmc")
    except Exception as e:
        sdCardErrors = f"error: {str(e)}"

    try:
        fileStatusPlugs = api.check_file_size_uniformity(api.dataPath,'plugs')
    except Exception as e:
        fileStatusPlugs = f"error: {str(e)}"

    try:
        fileStatusPowerStation = api.check_file_size_uniformity(api.dataPath,'powerstation')
    except Exception as e:
        fileStatusPowerStation = f"error: {str(e)}"

    try:
        serviceList = ['controls','eink_display','plug_logger','bluetti_logger','dashboard','airtable_logger']
        serviceDict = {}
        for s in serviceList:
            serviceDict[s] = api.getServiceStatus(s)
    except Exception as e:
        serviceDict = f"error:{str(e)}"

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd='/home/drux/demandResponse_UX_research').decode().strip()
    except Exception as e:
        commit = f"errpr{str(e)}"

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd='/home/drux/demandResponse_UX_research').decode().strip()
    except Exception as e:
        branch = f"errpr{str(e)}"

    controlLogFile = '/home/drux/demandResponse_UX_research/controls.log'
    try:
        # past 3 dates in format (YYYY-MM-DD)
        logDates = []
        duration = 4
        for d in range(duration):
            dt = date.today()-timedelta(days=duration-d-1)
            logDates.append(dt.strftime("%Y-%m-%d"))
        logging.info(f'dates:{logDates}')

        controlLog = []
        with open(controlLogFile, "r", encoding="utf-8") as f:
            for line in f:
                for d in logDates:
                    if d in line: # and ("ERROR" in line or "CRITICAL" in line):
                        controlLog.append(line.strip())

    except Exception as e:
        controlLog = f"Error getting control log: {e}"


    displayLogFile = '/home/drux/demandResponse_UX_research/display.log'
    try:
        # past 3 dates in format (YYYY-MM-DD)
        logDates = []
        duration = 4
        for d in range(duration):
            dt = date.today()-timedelta(days=duration-d-1)
            logDates.append(dt.strftime("%Y-%m-%d"))
        logging.info(f'dates:{logDates}')

        displayLog = []
        with open(displayLogFile, "r", encoding="utf-8") as f:
            for line in f:
                for d in logDates:
                    if d in line and ("ERROR" in line or "CRITICAL" in line):
                        displayLog.append(line.strip())
    except Exception as e:
        displayLog = f"Error getting display log: {e}"


    airtableLogFile = '/home/drux/demandResponse_UX_research/airtable.log'
    try:
        # past 3 dates in format (YYYY-MM-DD)
        logDates = []
        duration = 4
        for d in range(duration):
            dt = date.today()-timedelta(days=duration-d-1)
            logDates.append(dt.strftime("%Y-%m-%d"))
        logging.info(f'dates:{logDates}')

        airtableLog = []
        with open(airtableLogFile, "r", encoding="utf-8") as f:
            for line in f:
                for d in logDates:
                    if d in line and ("ERROR" in line or "CRITICAL" in line):
                        airtableLog.append(line.strip())
    except Exception as e:
        displayLog = f"Error getting airtable log: {e}"

    return jsonify({
        "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_tempC": cpu_tempC,
        "uptime": uptime,
        "memoryUsage": memoryUsage,
        "diskUsage" : diskUsage,
        "powerIssues" : powerIssues,
        "sdCardErrors" : sdCardErrors,
        "fileStatusPlugs":fileStatusPlugs,
        "fileStatusPowerStation":fileStatusPowerStation,
        "services":serviceDict,
        "controlLog":controlLog,
        "displayLog":displayLog,
        "airtableLog":airtableLog,
        "branch":branch,
        "commit":commit
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
