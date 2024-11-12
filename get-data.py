import os
import requests
import time
import logging
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment variables for InfluxDB connection
interval = 60*10 # one hour in seconds
influxdb_url = f"http://{os.getenv('INFLUXDB_HOST', '192.168.8.124')}:{os.getenv('INFLUXDB_PORT', '8086')}"
influxdb_token = os.getenv('INFLUXDB_TOKEN', 'replace with your influx token')
influxdb_org = os.getenv('INFLUXDB_ORG', 'ohgo')
influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'ohgo')

ohgo_api_key = os.getenv('OHGO_API_KEY', 'register for your own ohgo key')

# Connect to InfluxDB
try:
    influxdb_client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
    logging.info("Connected to InfluxDB")
except Exception as e:
    logging.error(f"Failed to connect to InfluxDB: {e}")
    exit(1)

def get_weather_sensor_data():
    url = "http://publicapi.ohgo.com/api/v1/weather-sensor-sites"
    headers = {
        "authorization": f"APIKEY {ohgo_api_key}",
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            data = response.json()
            logging.info(f"Raw data received: {data}")  # Log the raw data for inspection
            return data
        except ValueError as e:
            logging.error("Failed to parse JSON response")
            return None
    else:
        logging.error(f"Request failed with status code {response.status_code}")
        return None

def process_weather_data():
    while True:
        try:
            logging.info("Starting a new run...")

            data = get_weather_sensor_data()

            # Check if data is a dictionary and contains 'results' key with a list of sites
            if data and isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
                write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

                # Iterate over each site in the 'results' list
                for site in data["results"]:
                    if isinstance(site, dict):  # Ensure each site is a dictionary
                        logging.info(f"Processing site: {site.get('id', 'Unknown')}")

                        # Access atmospheric sensor data
                        severe = site.get("severe", "None")
                        atmospheric_data = site.get("atmosphericSensors", [{}])[0]
                        wind_direction = atmospheric_data.get("windDirection", "Unknown")
                        precipitation = atmospheric_data.get("precipitation", "None")

                        # Mapping values to integers
                        precipitation_mapping = {"None": 0, "Rain": 1, "Snow": 2}
                        severe_mapping = {"False": 0, "True": 1}
                        wind_direction_mapping = {
                            "North": 0, "Northeast": 45, "East": 90, "Southeast": 135, "South": 180,
                            "Southwest": 225, "West": 270, "Northwest": 315
                        }

                        severe_int = severe_mapping.get(severe, -1)
                        precipitation_int = precipitation_mapping.get(precipitation, -1)
                        wind_direction_int = wind_direction_mapping.get(wind_direction, -1)


                        zid = site.get('id')
                        zlat = site.get('latitude')
                        zlon = site.get('longitude')
                        zair = atmospheric_data.get("airTemperature")
                        zdew = atmospheric_data.get("dewpointTemperature")
                        zhum = atmospheric_data.get("humidity")
                        zwin = atmospheric_data.get("averageWindSpeed")
                        zmax = atmospheric_data.get("maximumWindSpeed")
                        zpcp = atmospheric_data.get("precipitationRate")
                        zvis = atmospheric_data.get("visibility")
                        zlas = atmospheric_data.get("lastUpdate")
                        logging.debug(f"ID: {zid}, Lat: {zlat}, Lon: {zlon}, Severe: {severe_int}, AirTemp: {zair}, DewPoint: {zdew}, Humidity: {zhum}, AvgWindSpeed: {zwin}, MaxWindSpeed: {zmax}, WindDirection: {wind_direction_int}, Precip: {precipitation_int}, RecipRate: {zpcp}, Visibility: {zvis}, LastUpdate: {zlas}")


                        # Create an InfluxDB point
                        point = (
                            Point("sensor_data")
                            .tag("id", site.get("id", "unknown"))
                            .tag("location", site.get("location"))
                            .field("latitude", site.get("latitude", 0))
                            .field("longitude", site.get("longitude", 0))
                            .field("severe", severe_int)
                            .field("airTemperature", atmospheric_data.get("airTemperature"))
                            .field("dewpointTemperature", atmospheric_data.get("dewpointTemperature"))
                            .field("humidity", atmospheric_data.get("humidity"))
                            .field("averageWindSpeed", atmospheric_data.get("averageWindSpeed"))
                            .field("maximumWindSpeed", atmospheric_data.get("maximumWindSpeed"))
                            .field("windDirection", wind_direction_int)
                            .field("precipitation", precipitation_int)
                            .field("precipitationRate", atmospheric_data.get("precipitationRate"))
                            .field("visibility", atmospheric_data.get("visibility"))
                            .time(atmospheric_data.get("lastUpdate"), WritePrecision.NS)
                        )

                        write_api.write(bucket=influxdb_bucket, org=influxdb_org, record=point)

                logging.info("Data successfully written to InfluxDB")

            else:
                logging.error("Unexpected data format received from API")

        except Exception as e:
            logging.error(f"An error occurred: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    process_weather_data()
