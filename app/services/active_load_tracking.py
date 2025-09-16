from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from helpers import logger
from logic.auth.security import get_current_user
from models.load_tracking import (
    ActiveLoadTracking,
    ActiveLoadTrackingCreate,
    ActiveLoadTrackingUpdate,
    ActiveLoadTrackingUpsert,
    MuteFlagUpdateRequest
)

router = APIRouter(
    prefix="/active-load-tracking", 
    dependencies=[Depends(get_current_user)],
    tags=["active-load-tracking"]
)

@router.get("/", response_model=List[ActiveLoadTracking])
async def get_all_active_load_tracking(
    limit: int = Query(default=5000, ge=1, le=10000),
    sort_by: str = Query(default="created_at", description="Field to sort by"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$", description="Sort order: asc or desc")
):
    """
    Get all active load tracking records with optional sorting
    """
    logger.info(f"Getting all active load tracking records with limit: {limit}, sort: {sort_by} {sort_order}")
    return ActiveLoadTracking.get_all(limit=limit, sort_by=sort_by, sort_order=sort_order)

@router.get("/{load_id}", response_model=ActiveLoadTracking)
async def get_active_load_tracking_by_id(load_id: str):
    """
    Get a specific active load tracking record by load_id
    """
    logger.info(f"Getting active load tracking record by ID: {load_id}")
    
    record = ActiveLoadTracking.get_by_id(load_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active load tracking record with ID '{load_id}' not found"
        )
    
    return record

@router.post("/", response_model=ActiveLoadTracking)
async def create_active_load_tracking(record_data: ActiveLoadTrackingCreate):
    """
    Create a new active load tracking record
    """
    logger.info(f"Creating active load tracking record with ID: {record_data.load_id}")
    
    record = ActiveLoadTracking.create(record_data)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create active load tracking record"
        )
    
    return record

@router.put("/{load_id}", response_model=ActiveLoadTracking)
async def update_active_load_tracking(load_id: str, record_data: ActiveLoadTrackingUpdate):
    """
    Update an existing active load tracking record
    """
    logger.info(f"Updating active load tracking record with ID: {load_id}")
    
    record = ActiveLoadTracking.update(load_id, record_data)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active load tracking record with ID '{load_id}' not found"
        )
    
    return record

@router.delete("/{load_id}")
async def delete_active_load_tracking(load_id: str):
    """
    Delete an active load tracking record
    """
    logger.info(f"Deleting active load tracking record with ID: {load_id}")
    
    success = ActiveLoadTracking.delete(load_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active load tracking record with ID '{load_id}' not found"
        )
    
    return JSONResponse(
        status_code=200, 
        content={"message": f"Active load tracking record with ID '{load_id}' deleted successfully"}
    )

@router.post("/upsert", response_model=ActiveLoadTracking)
async def upsert_active_load_tracking(record_data: ActiveLoadTrackingUpsert):
    """
    Upsert an active load tracking record (insert or update if exists)
    """
    logger.info(f"Upserting active load tracking record with ID: {record_data.load_id}")
    
    if not record_data.load_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="load_id is required for upsert operation"
        )
    
    record = ActiveLoadTracking.upsert(record_data)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert active load tracking record"
        )
    
    return record

@router.get("/status/{status_filter}", response_model=List[ActiveLoadTracking])
async def get_active_load_tracking_by_status(
    status_filter: str,
    limit: int = Query(default=5000, ge=1, le=10000),
    sort_by: str = Query(default="created_at", description="Field to sort by"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$", description="Sort order: asc or desc")
):
    """
    Get active load tracking records by status with optional sorting
    """
    logger.info(f"Getting active load tracking records by status: {status_filter} with limit: {limit}, sort: {sort_by} {sort_order}")
    return ActiveLoadTracking.get_by_status(status_filter=status_filter, limit=limit, sort_by=sort_by, sort_order=sort_order)

@router.get("/created-at/{created_at_date}", response_model=List[ActiveLoadTracking])
async def get_active_load_tracking_by_created_at(
    created_at_date: str,
    limit: int = Query(default=5000, ge=1, le=10000),
    sort_by: str = Query(default="created_at", description="Field to sort by"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$", description="Sort order: asc or desc")
):
    """
    Get active load tracking records by created_at date (YYYY-MM-DD format) with optional sorting
    """
    logger.info(f"Getting active load tracking records by created_at date: {created_at_date} with limit: {limit}, sort: {sort_by} {sort_order}")
    
    # Validate date format
    try:
        from datetime import datetime
        datetime.strptime(created_at_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD format (e.g., 2025-09-10)"
        )
    
    records = ActiveLoadTracking.get_by_created_at(created_at_date=created_at_date, limit=limit, sort_by=sort_by, sort_order=sort_order)
    return records

@router.patch("/mute-flag", response_model=ActiveLoadTracking)
async def update_mute_flag(request_data: MuteFlagUpdateRequest):
    """
    Update mute_flag for an active load tracking record by trip_id
    """
    logger.info(f"Updating mute_flag to {request_data.mute} for trip_id: {request_data.tripId}")

    record = ActiveLoadTracking.update_mute_flag_by_trip_id(request_data.tripId, request_data.mute)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active load tracking record with trip_id '{request_data.tripId}' not found"
        )

    return record

@router.get("/mute-flag/{mute_flag}", response_model=List[ActiveLoadTracking])
async def get_active_load_tracking_by_mute_flag(
    mute_flag: bool,
    limit: int = Query(default=5000, ge=1, le=10000),
    sort_by: str = Query(default="created_at", description="Field to sort by"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$", description="Sort order: asc or desc")
):
    """
    Get active load tracking records by mute_flag with optional sorting
    """
    logger.info(f"Getting active load tracking records by mute_flag: {mute_flag} with limit: {limit}, sort: {sort_by} {sort_order}")
    return ActiveLoadTracking.get_by_mute_flag(mute_flag=mute_flag, limit=limit, sort_by=sort_by, sort_order=sort_order)