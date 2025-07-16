from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from logic.auth.security import get_current_user
from logic.trips import get_trailer_and_trips, get_trip_data


router = APIRouter(prefix="/trips", dependencies=[Depends(get_current_user)])

@router.get("/trailers")
async def trailer_trips():
    data = get_trailer_and_trips()
    return JSONResponse(content=data)


@router.get("/{trip_id}/trailers/{trailer_id}")
async def trip_data(trip_id: str, trailer_id: str):
    if not trailer_id or not trip_id:
        return JSONResponse(status_code=400, content={"error": "Missing trailer_id or trip_id"})
    
    data = get_trip_data(trailer_id, trip_id)

    if "error" in data:
        return JSONResponse(status_code=400, content=data)
    
    return JSONResponse(content=data)
