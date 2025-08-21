from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel, Field

from logic.weather import WeatherService
from logic.auth.security import get_current_active_user
from models.user import User


router = APIRouter(prefix="/weather", tags=["weather"])


class WeatherResponse(BaseModel):
    location: Optional[dict] = Field(None, description="Location information")
    current: Optional[dict] = Field(None, description="Current weather data")
    error: Optional[dict] = Field(None, description="Error information if request failed")


@router.get("/current", response_model=WeatherResponse)
async def get_current_weather(
    location: str = Query(..., description="Location (city name, zip code, coordinates, IP address)"),
    aqi: bool = Query(False, description="Include air quality data"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current weather for a specified location.
    
    Location can be:
    - City name (e.g., "London", "New York")
    - US Zipcode (e.g., "10001")
    - UK Postcode (e.g., "SW1")
    - Canada Postalcode (e.g., "G2J")
    - IP address (e.g., "100.0.0.1")
    - Latitude/Longitude (e.g., "48.8567,2.3508")
    """
    result = await WeatherService.get_current_weather(location, aqi)
    
    if "error" in result:
        if result["error"]["code"] == 1006:
            raise HTTPException(status_code=404, detail=result["error"]["message"])
        elif result["error"]["code"] == 2006:
            raise HTTPException(status_code=401, detail=result["error"]["message"])
        else:
            raise HTTPException(status_code=500, detail=result["error"]["message"])
    
    return result