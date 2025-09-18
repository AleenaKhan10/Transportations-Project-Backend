import json
from datetime import datetime, timezone
from dataclasses import dataclass

import pytz
import requests
import pandas as pd
import pandas_gbq as pdg

from config import settings


@dataclass
class WeatherData:
    latitude: float
    longitude: float
    location: str
    region: str
    temperature: float
    description: str
    wind_mph: float
    timestamp: datetime
    raw_data: str


def make_weather_info(wd: WeatherData):
    if wd is None:
        return "Weather data not available"
    return f"🌤 Weather at {wd.location}, {wd.region} | {wd.temperature}°F | {wd.description} | Winds {wd.wind_mph} mp/h"


def cache_weather_bq(wds: list[WeatherData]):
    wds = [wd.__dict__ for wd in wds]
    df = pd.DataFrame(wds)
    df['ingestedAt'] = datetime.now(tz=timezone.utc)
    try:
        pdg.to_gbq(
            dataframe=df,
            destination_table="bronze.weather_cache",
            project_id="agy-intelligence-hub",
            if_exists="append",
        )
        return True
    except Exception as e:
        print(f"Error caching weather data: {e}")
        return False


def get_weather(lat: float, lon: float, aqi: bool = False):
    """Fetch current weather conditions for a given lat/lon."""
    params = {
        "key": settings.WEATHER_API_KEY,
        "q": f"{lat},{lon}",
        "aqi": "yes" if aqi else "no"
    }
    
    url = (f"{settings.WEATHER_API_BASE_URL}/current.json?" )

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        locat_ts = datetime.fromtimestamp(
            data['current']['last_updated_epoch'], 
            tz=pytz.timezone(data['location']['tz_id'])
        )
        utc_ts = locat_ts.astimezone(timezone.utc)

        weather_data = WeatherData(
            latitude=lat,
            longitude=lon,
            location=data["location"]["name"],
            region=data['location']['region'],
            temperature=data["current"]["temp_f"],
            description=data["current"]["condition"]["text"],
            wind_mph=data["current"]["wind_mph"],
            timestamp=utc_ts,
            raw_data=json.dumps(data),
        )
        return weather_data
    except Exception as e:
        print(f"Weather API error: {e}")
        return None
