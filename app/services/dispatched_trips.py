from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from helpers import logger
from logic.auth.security import get_current_user
from models.load_tracking import (
    DispatchedTrip, 
    DispatchedTripCreate, 
    DispatchedTripUpdate, 
    DispatchedTripUpsert
)

router = APIRouter(
    prefix="/dispatched-trips", 
    dependencies=[Depends(get_current_user)],
    tags=["dispatched-trips"]
)

@router.get("/", response_model=List[DispatchedTrip])
async def get_all_dispatched_trips(
    limit: int = Query(default=5000, ge=1, le=10000),
    sort_by: str = Query(default="created_on", description="Field to sort by"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$", description="Sort order: asc or desc")
):
    """
    Get all dispatched trips with optional sorting
    """
    logger.info(f"Getting all dispatched trips with limit: {limit}, sort: {sort_by} {sort_order}")
    return DispatchedTrip.get_all(limit=limit, sort_by=sort_by, sort_order=sort_order)

@router.get("/{trip_id}", response_model=DispatchedTrip)
async def get_dispatched_trip_by_id(trip_id: str):
    """
    Get a specific dispatched trip by trip_id
    """
    logger.info(f"Getting dispatched trip by trip_id: {trip_id}")
    
    record = DispatchedTrip.get_by_id(trip_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispatched trip with trip_id '{trip_id}' not found"
        )
    
    return record

@router.post("/", response_model=DispatchedTrip)
async def create_dispatched_trip(record_data: DispatchedTripCreate):
    """
    Create a new dispatched trip
    """
    logger.info("Creating dispatched trip record")
    
    record = DispatchedTrip.create(record_data)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create dispatched trip"
        )
    
    return record

@router.put("/{trip_id}", response_model=DispatchedTrip)
async def update_dispatched_trip(trip_id: str, record_data: DispatchedTripUpdate):
    """
    Update an existing dispatched trip
    """
    logger.info(f"Updating dispatched trip with trip_id: {trip_id}")
    
    record = DispatchedTrip.update(trip_id, record_data)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispatched trip with trip_id '{trip_id}' not found"
        )
    
    return record

@router.delete("/{trip_id}")
async def delete_dispatched_trip(trip_id: str):
    """
    Delete a dispatched trip
    """
    logger.info(f"Deleting dispatched trip with trip_id: {trip_id}")
    
    success = DispatchedTrip.delete(trip_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispatched trip with trip_id '{trip_id}' not found"
        )
    
    return JSONResponse(
        status_code=200, 
        content={"message": f"Dispatched trip with trip_id '{trip_id}' deleted successfully"}
    )

@router.delete("/by-trip-key/{trip_key}")
async def delete_dispatched_trip_by_trip_key(trip_key: int):
    """
    Delete a dispatched trip by trip_key
    """
    logger.info(f"Deleting dispatched trip with trip_key: {trip_key}")
    
    success = DispatchedTrip.delete_by_trip_key(trip_key)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispatched trip with trip_key '{trip_key}' not found"
        )
    
    return JSONResponse(
        status_code=200, 
        content={"message": f"Dispatched trip with trip_key '{trip_key}' deleted successfully"}
    )

@router.post("/upsert", response_model=DispatchedTrip)
async def upsert_dispatched_trip(record_data: DispatchedTripUpsert):
    """
    Upsert a dispatched trip (insert or update if exists)
    """
    logger.info("Upserting dispatched trip record")
    
    record = DispatchedTrip.upsert(record_data)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert dispatched trip"
        )
    
    return record