import json
from dataclasses import dataclass
from datetime import datetime, timezone

import pytz
import requests
import pandas as pd
import pandas_gbq as pdg
from fastapi import BackgroundTasks

from config import settings
from helpers.utils import run_parallel_exec


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


def get_weather_df(lat_lons: list[tuple[float, float]], bt: BackgroundTasks | None = None, keep_raw_columns_in_df: bool = False):
    """
    Returns a DataFrame containing weather data for each lat/lon pair.

    The DataFrame columns are:
        - latitude: The latitude of the location
        - longitude: The longitude of the location
        - weather_info: A string containing the weather info for the location

    The weather_info string is in the format: "Weather at {location}, {region} | {temperature}°F | {description} | Winds {wind_mph} mp/h"

    The DataFrame is sorted by latitude and longitude.
    """
    # Handle empty lat_lons - return empty DataFrame with correct columns and dtypes
    if lat_lons is None or len(lat_lons) == 0:
        return pd.DataFrame({
            "latitude": pd.Series(dtype='float64'),
            "longitude": pd.Series(dtype='float64'),
            "weather_info": pd.Series(dtype='object')
        })

    def get_weather_data(lat_lon):
        lat, lon = lat_lon
        return get_weather(lat, lon)

    lat_lons_weather = run_parallel_exec(get_weather_data, lat_lons)

    if bt is not None:
        bt.add_task(cache_weather_bq, wds=[w for _, w in lat_lons_weather if w is not None])
    else:
        cache_weather_bq(wds=[w for _, w in lat_lons_weather if w is not None])

    weather_df = pd.DataFrame([
        {
            "latitude": c[0],
            "longitude": c[1],
            "weather_info": make_weather_info(w),
        } | (w.__dict__ if keep_raw_columns_in_df and w is not None else {})
        for c, w in lat_lons_weather
    ])

    return weather_df
