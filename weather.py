import requests
from dotenv import load_dotenv
import os
from dataclasses import dataclass
from geopy.distance import geodesic
from datetime import datetime


load_dotenv()
api_key = os.getenv('API_KEY')

@dataclass
class WeatherData:
    main: str
    description: str
    icon: str
    temperature: int
    feels_like: int
    pressure: int
    humidity: int
    wind_speed: float
    sunrise: str
    sunset: str

@dataclass
class ForecastData:
    datetime: str
    main: str
    description: str
    temp: int
    icon: str

@dataclass
class AirQualityData:
    station_id: int
    air_quality_index: str
    pm10: float
    pm25: float
    pm10_norm: int
    pm25_norm: int
    
def get_lan_lon(address):
    url = 'https://nominatim.openstreetmap.org/search.php?'
    
    parms = {
        'q': address,
        'format': 'geojson',
        'limit': 1
    }
    headers = {
        'User-Agent': 'YourAppName/1.0 (your@email.com)'
    }
    
    resp = requests.get(url, params=parms, headers=headers)
    data = resp.json()
    if data.get('features'):
        coordinates = data['features'][0]['geometry']['coordinates']
        lon, lat = coordinates
        display_name = data['features'][0]['properties']['display_name']
        return lat, lon, display_name
    else:
        return None, None, None
    
def get_current_weather(lat, lon, API_key):
    resp = requests.get(f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_key}&units=metric&lang=pl').json()
    data = WeatherData(
        main = resp.get('weather')[0].get('main'),
        description = resp.get('weather')[0].get('description'),
        icon = resp.get('weather')[0].get('icon'),
        temperature = int(resp.get('main').get('temp')),
        feels_like = int(resp.get('main').get('feels_like')),
        pressure = resp.get('main').get('pressure'),
        humidity = resp.get('main').get('humidity'),
        wind_speed = round(resp.get('wind').get('speed')*3.6, 2),
        sunrise = datetime.fromtimestamp(resp.get('sys').get('sunrise')).strftime('%H:%M'),
        sunset = datetime.fromtimestamp(resp.get('sys').get('sunset')).strftime('%H:%M')
    )
    return data

def get_weather_forecast(lat, lon , API_key):
    url = f'https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_key}&lang=pl&units=metric'
    resp = requests.get(url).json()
    forecasts = []

    for entry in resp["list"]:
        forecasts.append(ForecastData(
            datetime = entry["dt_txt"],
            main = entry["weather"][0]["main"],
            description = entry["weather"][0]["description"],
            temp = entry["main"]["temp"],
            icon = entry["weather"][0]["icon"]
        ))

    return forecasts

def is_in_poland(lat, lon):
    url = 'https://nominatim.openstreetmap.org/reverse'
    params = {
        'lat': lat,
        'lon': lon,
        'format': 'json'
    }
    headers = {
        'User-Agent': 'YourAppName/1.0 (your@email.com)'
    }
    
    resp = requests.get(url, params=params, headers=headers).json()
    country = resp.get('address').get('country')
    if country == 'Polska':
        return True
    else:
        return False

def get_nearest_station(lat, lon):
    url = 'https://api.gios.gov.pl/pjp-api/v1/rest/station/findAll'
    response = requests.get(url)
    stations = response.json()
    user_location = (lat, lon)
    closest_station = None
    min_distance = float('inf')
    
    pages = int(stations.get('totalPages'))
    
    for page in range(pages):
        for station in stations['Lista stacji pomiarowych']:
            try:
                station_lat = float(station['WGS84 φ N'])
                station_lon = float(station['WGS84 λ E'])
                station_coords = (station_lat, station_lon)
                distance = geodesic(user_location, station_coords).km
                
                if distance < min_distance:
                    min_distance = distance
                    closest_station = station
            except(KeyError, ValueError):
                continue
            
        next_page = stations.get('links').get('next')
        url = next_page
        response = requests.get(url)  
        stations = response.json()
    return closest_station['Identyfikator stacji']

def get_aq_index(station_id):
    url = f'https://api.gios.gov.pl/pjp-api/v1/rest/aqindex/getIndex/{station_id}'
    response = requests.get(url)
    data = response.json()
    air_quality_status = data.get('AqIndex').get('Nazwa kategorii indeksu')
    
    if air_quality_status == 'Brak indeksu':
        return None
    return air_quality_status

def get_sensors_id(station_id):
    url = f'https://api.gios.gov.pl/pjp-api/v1/rest/station/sensors/{station_id}'
    response = requests.get(url)
    data = response.json()
    
    pm10_sensorID = None
    pm25_sensorID = None
    
    for stanowisko in data['Lista stanowisk pomiarowych dla podanej stacji']:
        if stanowisko['Wskaźnik - kod'] == 'PM10':
            pm10_sensorID = stanowisko['Identyfikator stanowiska']
        elif stanowisko['Wskaźnik - kod'] == 'PM2.5':
            pm25_sensorID = stanowisko['Identyfikator stanowiska']
    return pm10_sensorID, pm25_sensorID

def get_aq_pm10(pm10_sensorID):
    try:
        if pm10_sensorID is None:
            return None
        url = f'https://api.gios.gov.pl/pjp-api/v1/rest/data/getData/{pm10_sensorID}'
        resp = requests.get(url)
        data = resp.json()

        pm10 = None
        for entry in data['Lista danych pomiarowych']:
            if entry['Wartość'] is not None:
                pm10 = entry['Wartość']
                break
        return pm10
    except:
        return None
    
def get_aq_pm25(pm25_sensorID):
    try:
        if pm25_sensorID is None:
            return None
        url = f'https://api.gios.gov.pl/pjp-api/v1/rest/data/getData/{pm25_sensorID}'
        resp = requests.get(url)
        data = resp.json()

        pm25 = None
        for entry in data['Lista danych pomiarowych']:
            if entry['Wartość'] is not None:
                pm25 = entry['Wartość']
                break
        return pm25
    except:
        return None
    
def pm10_pm25_norms_in_percent(pm10, pm25):
    if pm10 is None:
        pm10_norm = None
    else:
        pm10_norm = int((pm10/50)*100)
        
    if pm25 is None:
        pm25_norm = None
    else:
        pm25_norm = int((pm25/15)*100)
        
    return pm10_norm, pm25_norm
    
    
def main(addr):
    lat, lon, display_name = get_lan_lon(addr)
    if lat is None or lon is None:
        return None

    weather_data = get_current_weather(lat, lon, api_key)
    weather_forecast = get_weather_forecast(lat, lon, api_key)
    
    result = {
        "display_name": display_name,
        "lat": lat,
        "lon": lon,
        "weather": weather_data,
        "forecast": weather_forecast,
        "air": None,
    }
    
    if is_in_poland(lat, lon):
        station_id = get_nearest_station(lat, lon)
        air_quality = get_aq_index(station_id)
        pm10_sensor, pm25_sensor = get_sensors_id(station_id)
        pm10 = get_aq_pm10(pm10_sensor)
        pm25 = get_aq_pm25(pm25_sensor)
        pm10_norm, pm25_norm = pm10_pm25_norms_in_percent(pm10, pm25)

        result["air"] = AirQualityData(
            station_id=station_id,
            air_quality_index=air_quality,
            pm10=pm10,
            pm25=pm25,
            pm10_norm=pm10_norm,
            pm25_norm=pm25_norm
        )

    return result

#do testowania w konsoli    
if __name__ == "__main__":
    while True: 
        addr = input('Podaj adres: ')
        if len(addr) <= 1:
            break
        print(main(addr))
        
