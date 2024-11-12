# ohgo-grafana
OLF 24 Presentation Example for OH GO API


## Register for OH Go API access here
https://ohgo.com/api/login

## Stand up Grafana and InfluxDB
I have a docker-compose.yml file in this repo that should help get you started
Make sure to get your InfluxDB token

## Edit get-data.py
Make sure to add your ohgo api token and influxdb token.
You will also want to update the ip address of influxdb for your environment.

## Install Python packages
python -m venv env
source env/bin/activate
pip3 install -r requirements.txt

## Run get-data.py
python get-data.py
