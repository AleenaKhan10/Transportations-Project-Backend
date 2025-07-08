from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from providers.trailer_trip_provider import get_trailer_and_trips, get_trip_data
from auth.security import get_current_user
from db.models import User

router = APIRouter()

@router.get("/trailer-trips")
async def trailer_trips(current_user: User = Depends(get_current_user)):
    data = get_trailer_and_trips()
    return JSONResponse(content=data)

@router.get("/trip-data")
async def trip_data(trailer_id:str, trip_id:str, current_user: User = Depends(get_current_user)):
    if not trailer_id or not trip_id:
        return JSONResponse(status_code=400, content={"error": "Missing trailer_id or trip_id"})
    
    data = get_trip_data(trailer_id, trip_id)

    if "error" in data:
        return JSONResponse(status_code=400, content=data)
    
    return JSONResponse(content=data) 