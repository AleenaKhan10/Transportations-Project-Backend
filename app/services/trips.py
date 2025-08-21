from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse

from helpers.time_utils import BQTimeUnit
from logic.trips import fetch_latest_alerts
from logic.auth.security import get_current_user
from logic.trips import get_trailer_and_trips, get_trip_data
from models.trips import Trip, TripCreate, TripUpdate
from helpers import logger


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


@router.get("/alerts")
async def get_latest_alerts(
    value: int = Query(1, gt=0, description="Numeric value for time unit"),
    unit: BQTimeUnit = Query(BQTimeUnit.HOUR, description="Unit of time (minutes, hours, days, ...)"),
):
    result = fetch_latest_alerts(value, unit)
    return result


# New Trip Management Endpoints
@router.get("/all", response_model=List[Trip])
async def get_all_trips(limit: int = 5000):
    """
    Get all trips from database
    """
    logger.info("Getting all trips from database")
    trips = Trip.get_all(limit=limit)
    return trips


@router.get("/trip/{trip_id}", response_model=Trip)
async def get_trip_by_id(trip_id: str):
    """
    Get a trip by tripId
    """
    logger.info(f"Getting trip for ID: {trip_id}")
    trip = Trip.get_by_trip_id(trip_id)
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID '{trip_id}' not found"
        )
    
    return trip


@router.get("/driver/{driver_id}", response_model=List[Trip])
async def get_trips_by_driver(driver_id: str):
    """
    Get all trips by driver ID
    """
    logger.info(f"Getting trips for driver ID: {driver_id}")
    trips = Trip.get_by_driver_id(driver_id)
    return trips


@router.post("/upsert", response_model=Trip)
async def upsert_trip(trip_data: TripCreate):
    """
    Upsert a trip (insert or update if exists) - only updates provided fields
    """
    logger.info(f"Upserting trip for ID: {trip_data.tripId}")
    
    if not trip_data.tripId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tripId is required for upsert operation"
        )
    
    # Convert TripCreate to dict and remove tripId for kwargs
    trip_dict = trip_data.dict(exclude_unset=True)
    trip_id = trip_dict.pop('tripId')
    
    trip = Trip.upsert(trip_id=trip_id, **trip_dict)
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert trip"
        )
    
    return trip
