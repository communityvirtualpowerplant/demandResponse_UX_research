
## OS and Software Installation

### Pi Imager Settings

Naming convention: 

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

<!-- Clone the display repository into home directory<br>
`git clone https://github.com/waveshareteam/e-Paper.git` -->

Make the data directory
Create a virtual environment in demandResponse_UX_research/ directory `python -m venv venv`

Install python dependencies
* `source venv/bin/activate`
* `pip install -r requirements`
Note that installing the waveshare and Jetson libraries will probably fail. Navigate to the epaper directory and use `pip install .`

Run pigpiod as a service (this allows you to access gpio without sudo)
`sudo systemctl enable pigpiod`<br>
`sudo systemctl start pigpiod`

Copy the env-template file
* `sudo cp env-template.txt .env`
* Add the Airtable API key and Kasa user credentials, with the variable names shown below. See credentials doc for info.
	* `AIRTABLE=**************`
	* `KASA_UN=**************`
	* `KASA_PW=**************`

## Automate
`chmod +x /home/drux/demandResponse_UX_research/services/plug_logger.py`
`cp /home/drux/demandResponse_UX_research/services/plug_logger.service /etc/systemd/system/plug_logger.service`

`systemctl daemon-reexec`
`systemctl daemon-reload`
`systemctl enable sht31d_logger.service`
`systemctl start sht31d_logger.service`

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