from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from helpers.time_utils import BQTimeUnit
from logic.alerts import send_alerts_duration, send_latest_alerts
from logic.auth.security import verify_static_token


router = APIRouter()

@router.post("/")
async def latest_alerts():
    result = send_latest_alerts()
    return result

@router.post("/time-interval")
async def alerts_with_duration(value: int = Query(..., gt=0, description="Numeric value for time"),
    unit: BQTimeUnit = Query(..., description="Unit of time (minutes, hours, days)")):

    result = send_alerts_duration(value, unit)
    return result

