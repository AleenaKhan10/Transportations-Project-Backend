from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
import httpx

from helpers import logger
from logic.auth.security import get_current_user
from models.pcmiler import ETARequest
from config import settings


router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])




@router.post("/eta")
async def get_eta(request: ETARequest):
    """
    Calculate ETA for a truck route using PC*MILER API
    """
    try:
        origin = request.origin
        destination = request.destination
        departure_time = request.departureTime

        if not origin or not destination:
            raise HTTPException(
                status_code=400,
                detail={"error": "Origin and destination are required."}
            )

        # Get API key from environment (you'll need to add this to config.py)
        api_key = getattr(settings, 'PCMILER_API_KEY', '')
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail={"error": "PC*MILER API key not configured"}
            )

        endpoint = "https://pcmiler.alk.com/apis/rest/v1.0/Service.svc/route/routeReports"

        payload = {
            "stops": [{"addr": origin}, {"addr": destination}],
            "options": {
                "routeType": "Practical",
                "vehicleProfile": {
                    "type": "Truck",
                    "length": 53,
                    "weight": 80000,
                },
            },
        }

        # Add departure time if provided
        if departure_time:
            payload["options"]["departureTime"] = departure_time

        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0
            )

            if response.status_code >= 400:
                raise Exception(f"PC*MILER API Error: {response.status_code} - {response.text}")

            response_data = response.json()

        total_hours = response_data.get("totalTime", 0)
        
        # Calculate ETA
        if departure_time:
            try:
                base_time = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
            except ValueError:
                base_time = datetime.now()
        else:
            base_time = datetime.now()

        eta = datetime.fromtimestamp(base_time.timestamp() + total_hours * 3600)

        return {
            "origin": origin,
            "destination": destination,
            "distance": response_data.get("distance"),
            "travelTimeHours": total_hours,
            "eta": eta.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"PC*MILER API Error: {str(error)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to calculate ETA.",
                "detail": str(error),
            }
        )