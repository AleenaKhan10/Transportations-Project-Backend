from fastapi import APIRouter
from fastapi.responses import JSONResponse
from providers.trailer_trip_provider import get_trailer_and_trips, get_trip_data

router = APIRouter()

@router.get("/trailer-trips")
async def trailer_trips():
    data = get_trailer_and_trips()
    return JSONResponse(content=data)

@router.get("/trip-data")
async def trip_data(trailer_id:str, trip_id:str):
    if not trailer_id or not trip_id:
        return JSONResponse(status_code=400, content={"error": "Missing trailer_id or trip_id"})
    
    data = get_trip_data(trailer_id, trip_id)

    if "error" in data:
        return JSONResponse(status_code=400, content=data)
    
    return JSONResponse(content=data) 