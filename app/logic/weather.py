import httpx
from typing import Dict, Any
from config import settings


class WeatherService:
    @staticmethod
    async def get_current_weather(location: str, aqi: bool = False) -> Dict[str, Any]:
        """
        Fetch current weather data for a given location.
        
        Args:
            location: Can be US Zipcode, UK Postcode, Canada Postalcode, 
                     IP address, Latitude/Longitude (decimal degree) or city name
            aqi: Whether to include air quality data
            
        Returns:
            Dictionary containing weather data
        """
        params = {
            "key": settings.WEATHER_API_KEY,
            "q": location,
            "aqi": "yes" if aqi else "no"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{settings.WEATHER_API_BASE_URL}/current.json",
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    return {
                        "error": {
                            "code": 1006,
                            "message": "No matching location found."
                        }
                    }
                elif e.response.status_code == 401:
                    return {
                        "error": {
                            "code": 2006,
                            "message": "API key is invalid."
                        }
                    }
                else:
                    return {
                        "error": {
                            "code": e.response.status_code,
                            "message": f"Weather API error: {e.response.text}"
                        }
                    }
            except httpx.TimeoutException:
                return {
                    "error": {
                        "code": 408,
                        "message": "Request timeout while fetching weather data."
                    }
                }
            except Exception as e:
                return {
                    "error": {
                        "code": 500,
                        "message": f"Unexpected error: {str(e)}"
                    }
                }