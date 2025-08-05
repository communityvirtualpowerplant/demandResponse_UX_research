
## Hardware Installation

The button is on GPIO26 and GND. Bend those 2 pins forwards to be able to access them when the screen is on.

## OS and Software Installation

### Pi Imager Settings

* Naming convention: participant + 0-3
* Enable ssh
* Wifi: connect to Pixel tether for remote access

See credentials doc for username, password, and network setting to use.

### Pi Setup

`sudo apt-get update`

`sudo apt-get upgrade`

`sudo raspi-config`
* Interface Options
	* Enable SSH
	* Enable I2C
	* Enable SPI
* Localization
	* enable US.UTF-8 (optionally, removing GB will free up a little space)
	* set timezone to NY
	* set WLAN to US
* Advanced Options
	* Expand filesystem
Reboot after configuration

Clone repository into home directory<br>
`git clone https://github.com/communityvirtualpowerplant/demandResponse_UX_research`

Make the data directory and copy state template
* `mkdir /home/drux/demandResponse_UX_research/data`
* `cp /home/drux/demandResponse_UX_research/state_template.json /home/drux/demandResponse_UX_research/data/state.json`

Create a virtual environment in demandResponse_UX_research/ directory
* `cd /home/drux/demandResponse_UX_research`
* `python -m venv venv`

Install python dependencies
* `source venv/bin/activate`
* `pip install -r requirements`

(If the waveshare and Jetson libraries fail - clone the epaper directory (see Waveshare instruction),navigate to the epaper directory, and use `pip install .`)

Run pigpiod as a service (this allows you to access gpio without sudo)
`sudo systemctl enable pigpiod`<br>
`sudo systemctl start pigpiod`

<!-- Edit hostname file, so the correct local IP can be retrieved easily
* `sudo nano /etc/hosts`
* comment out this line: `#127.0.1.1 HOSTNAME` -->

Copy the env-template file
* `sudo cp env-template.txt .env`
* `nano .env`
* Add the Airtable API key and Kasa user credentials, with the variable names shown below. See credentials doc for info.
	* `AIRTABLE=**************`
	* `KASA_UN=**************`
	* `KASA_PW=**************`

Copy config temp file:
* `cp config_template.json config.json`
* update with necessary info (participation #, etc.)

## Automate

Run this for all services - plug_logger, bluetti_logger, airtable_logger, controls, dashboard, eink_display
* `chmod +x /home/drux/demandResponse_UX_research/services/plug_logger.py`
* `sudo cp /home/drux/demandResponse_UX_research/services/plug_logger.service /etc/systemd/system/plug_logger.service`

Note: may need to uncomment the 127 ip in host file for some services to be enabled.

`sudo systemctl daemon-reexec`<br>
`sudo systemctl daemon-reload`<br>
`sudo systemctl enable plug_logger.service`<br>
`sudo systemctl start plug_logger.service`

Check for updates and reboot at 12:15am and 5am  with cron (DONT use sudo):
* `crontab -e`
* add this line to bottom of file:
	* `15 0 * * * bash /home/drux/demandResponse_UX_research/utilities/update.sh > /home/drux/demandResponse_UX_research/utilities/update.log 2>&1`
	* `0 5 * * * bash /home/drux/demandResponse_UX_research/utilities/update.sh > /home/drux/demandResponse_UX_research/utilities/update.log 2>&1`

<!-- `@midnight sudo reboot` -->

# Smart Plug Installation

1) Connect device to Wifi
2) Name device
	* `participant0-batteryout`
	* `participant0-batteryin`
	* `participant0-ac`
3) If it asks for location, use DRUX
4) Update device
5) Add device to Participant# group
6) Set default state to on.
7) Test by running `python examples/kasa_smart_plugs.py`. All 3 devices should show up.


# Troubleshooting

## Wifi

To switch networks from command line, use network manager tool:
* To see all networks: `nmcli connection show`


# On-site install

0) Clear past data before install - plugs, powerstation, performance
1) Install outlets on site wifi
2) Connect controller to site wifi
3) Test plugs
4) Test Bluetti
5) Test Airtable
* check updating - state, health,
* run test event to demo
	* check button
4) Photograph installation