import requests
import os
from config import settings

WEATHER_API_KEY = settings.WEATHER_API_KEY

def get_weather(lat: float, lon: float, aqi: bool = False) -> str:
    
    params = {
            "key": WEATHER_API_KEY,
            "q": f"{lat},{lon}",
            "aqi": "yes" if aqi else "no"
        }
    """Fetch current weather conditions for a given lat/lon."""
    url = (f"{settings.WEATHER_API_BASE_URL}/current.json?" )

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        location = data["location"]["name"]
        region = data["location"]["region"]
        temp = data["current"]["temp_f"]
        desc = data["current"]["condition"]["text"]
        wind = data["current"]["wind_mph"]

        return f"🌤 Weather at {location}, {region} location: {temp}°C, {desc}, Winds {wind} mp/h"
    except Exception as e:
        print(f"Weather API error: {e}")
        return "Weather data unavailable"
