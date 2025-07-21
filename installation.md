
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

Clone repository<br>
`git clone https://github.com/communityvirtualpowerplant/demandResponse_UX_research`

Create .env file if accessing either the Kasa or Airtable APIs.
* In rpi_zero_sensor directory: `sudo nano /home/case/CASE_sensor_network/rpi_zero_sensor/.env`
* Add the Airtable API key and Kasa user credentials, with the variable names shown below. See credentials doc for info.
	* `AIRTABLE=**************`
	* `KASA_UN=**************`
	* `KASA_PW=**************`


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
7) Test by running `python utilities/collectPlugs.py`