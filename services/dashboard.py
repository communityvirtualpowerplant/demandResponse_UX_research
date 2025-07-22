from flask import Flask, render_template, request, send_file, abort, jsonify
from flask_cors import CORS
import csv
import datetime
import os
import sys
import glob
import json
import pandas as pd
import psutil
import logging

libdir = '/home/drux/demandResponse_UX_research/lib/helper_classes'
if os.path.exists(libdir):
    sys.path.append(libdir)

from API import API

logging.basicConfig(format='%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',level=logging.DEBUG)

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

# CORS is enabled for all routes. This simplifies the frontend visualization,
# but could be removed for security purposes or to more easily enforce throttling without straining the Pi Zeros.
CORS(app)

@app.route("/", methods=['GET'])
def index():
    return render_template('index.html')

@app.route("/today", methods=['GET'])
def today():
    file_pattern = os.path.join(filePath, f"*.csv")
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

@app.route("/api/discover", methods=['GET'])
def discover():
    return jsonify({'name': config['location']}), 200

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
            df = api.getMostRecent(filePath,filePrefix)[0]
            last_row = df.iloc[-1].to_dict()
            return jsonify(last_row)
        except FileNotFoundError:
            return jsonify({'error': 'CSV file not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif file == 'recent':
        try:
            file_pattern = os.path.join(filePath, f"*.csv")
            files = sorted(glob.glob(file_pattern))
            fileName = files[-1]
            dn = fileName.split('/')[-1]
            return send_file(os.path.abspath(fileName), as_attachment=True, download_name=dn, mimetype='text/csv')

        except FileNotFoundError:
            return jsonify({'error': 'CSV file not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        try:
            fileName = file+'.csv'

            file_pattern = os.path.join(filePath, f"{filePrefix}*.csv")
            files = sorted(glob.glob(file_pattern))

            for f in files:
                if fileName in f:
                    return send_file(os.path.abspath(f), as_attachment=True, download_name=fileName, mimetype='text/csv')
        except FileNotFoundError:
            return jsonify({'error': 'CSV file not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# upcoming and ongoing event info
@app.route("/api/event", methods=['GET'])
def getEventInfo():
    return jsonify({'ongoing': 0,
        'upcoming': 0,
        'availableWh':0}), 200

@app.route("/api/files", methods=['GET'])
def list_csv_files():
    filePrefix = request.args.get("source")

    if not filePrefix:
        return "Please provide source - either plugs or powerstation", 400

    # Get all CSV files in the data/ directory
    file_pattern = os.path.join(filePath, f"{filePrefix}*.csv")
    files = sorted(glob.glob(file_pattern))

    # Return just the filenames (without full paths)
    filenames = [os.path.basename(f) for f in files]

    return jsonify(filenames)

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
        fileStatus = api.check_file_size_uniformity(api.dataPath)
    except Exception as e:
        fileStatus = f"error: {str(e)}"

    return jsonify({
        "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_tempC": cpu_tempC,
        "uptime": uptime,
        "memoryUsage": memoryUsage,
        "diskUsage" : diskUsage,
        "powerIssues" : powerIssues,
        "sdCardErrors" : sdCardErrors,
        "fileStatus":fileStatus
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
