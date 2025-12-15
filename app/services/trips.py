from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from helpers.time_utils import BQTimeUnit
from logic.trips import fetch_latest_alerts
from logic.auth.security import get_current_user
from logic.trips import get_trailer_and_trips, get_trip_data
from models.trips import Trip, TripCreate
from helpers import logger


class CustomerGroupUpdate(BaseModel):
    tripId: str
    customerGroup: str


router = APIRouter(prefix="/trips", dependencies=[Depends(get_current_user)])


@router.get("/trailers")
async def trailer_trips():
    data = get_trailer_and_trips()
    return JSONResponse(content=data)


@router.get("/{trip_id}/trailers/{trailer_id}")
async def trip_data(trip_id: str, trailer_id: str):
    if not trailer_id or not trip_id:
        return JSONResponse(
            status_code=400, content={"error": "Missing trailer_id or trip_id"}
        )

    data = get_trip_data(trailer_id, trip_id)

    if "error" in data:
        return JSONResponse(status_code=400, content=data)

    return JSONResponse(content=data)


@router.get("/alerts")
async def get_latest_alerts(
    value: int = Query(1, gt=0, description="Numeric value for time unit"),
    unit: BQTimeUnit = Query(
        BQTimeUnit.HOUR, description="Unit of time (minutes, hours, days, ...)"
    ),
    bt: BackgroundTasks = BackgroundTasks(),
):
    result = fetch_latest_alerts(value, unit, bt)
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


@router.delete("/delete-trip/{trip_id}", status_code=status.HTTP_200_OK)
async def delete_trip_by_id(trip_id: str):
    deleted = Trip.delete(trip_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with id '{trip_id}' not found",
        )

    return {"success": True, "message": f"Trip '{trip_id}' deleted successfully"}


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
            detail=f"Trip with ID '{trip_id}' not found",
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
            detail="tripId is required for upsert operation",
        )

    # Convert TripCreate to dict and remove tripId for kwargs
    trip_dict = trip_data.dict(exclude_unset=True)
    trip_id = trip_dict.pop("tripId")

    trip = Trip.upsert(trip_id=trip_id, **trip_dict)

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert trip",
        )

    return trip


@router.post("/update-customer-group")
async def update_customer_group(data: CustomerGroupUpdate):
    """
    Update only the customerGroup field for a specific trip
    """
    logger.info(f"Updating customerGroup for trip ID: {data.tripId}")

    # Check if trip exists
    existing_trip = Trip.get_by_trip_id(data.tripId)

    if not existing_trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID '{data.tripId}' not found",
        )

    # Update only the customerGroup field
    updated_trip = Trip.update(trip_id=data.tripId, customerGroup=data.customerGroup)

    if not updated_trip:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update customerGroup",
        )

    return {
        "success": True,
        "message": f"Successfully updated customerGroup for trip {data.tripId}",
        "tripId": data.tripId,
        "customerGroup": data.customerGroup,
        "trip": updated_trip,
    }


@router.delete("/truncate")
async def truncate_trips_table():
    """
    DANGER: Truncate the trips table (delete ALL records)
    This will permanently delete all trip data from the database.
    Use with extreme caution - this action cannot be undone.
    """
    from datetime import datetime

    logger.warning("⚠️  TRUNCATE REQUEST: About to delete ALL trips from database")

    result = Trip.truncate_table()

    if result["success"]:
        logger.info(f"✅ Successfully truncated trips table: {result['message']}")
        return {
            "success": True,
            "message": result["message"],
            "deleted_count": result["deleted_count"],
            "timestamp": datetime.utcnow().isoformat(),
            "warning": "All trip data has been permanently deleted",
        }
    else:
        logger.error(f"❌ Failed to truncate trips table: {result['message']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"]
        )
