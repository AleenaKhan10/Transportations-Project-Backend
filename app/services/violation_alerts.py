from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from helpers import logger
from logic.auth.security import get_current_user
from models.load_tracking import (
    ViolationAlert, 
    ViolationAlertCreate, 
    ViolationAlertUpdate, 
    ViolationAlertUpsert
)

router = APIRouter(
    prefix="/violation-alerts", 
    dependencies=[Depends(get_current_user)],
    tags=["violation-alerts"]
)

@router.get("/", response_model=List[ViolationAlert])
async def get_all_violation_alerts(
    limit: int = Query(default=5000, ge=1, le=10000),
    sort_by: str = Query(default="created_at", description="Field to sort by"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$", description="Sort order: asc or desc")
):
    """
    Get all violation alerts with optional sorting
    """
    logger.info(f"Getting all violation alerts with limit: {limit}, sort: {sort_by} {sort_order}")
    return ViolationAlert.get_all(limit=limit, sort_by=sort_by, sort_order=sort_order)

@router.get("/{alert_id}", response_model=ViolationAlert)
async def get_violation_alert_by_id(alert_id: int):
    """
    Get a specific violation alert by ID
    """
    logger.info(f"Getting violation alert by ID: {alert_id}")
    
    record = ViolationAlert.get_by_id(alert_id)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation alert with ID '{alert_id}' not found"
        )
    
    return record

@router.post("/", response_model=ViolationAlert)
async def create_violation_alert(record_data: ViolationAlertCreate):
    """
    Create a new violation alert
    """
    logger.info("Creating violation alert record")
    
    record = ViolationAlert.create(record_data)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create violation alert"
        )
    
    return record

@router.put("/{alert_id}", response_model=ViolationAlert)
async def update_violation_alert(alert_id: int, record_data: ViolationAlertUpdate):
    """
    Update an existing violation alert
    """
    logger.info(f"Updating violation alert with ID: {alert_id}")
    
    record = ViolationAlert.update(alert_id, record_data)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation alert with ID '{alert_id}' not found"
        )
    
    return record

@router.delete("/{alert_id}")
async def delete_violation_alert(alert_id: int):
    """
    Delete a violation alert
    """
    logger.info(f"Deleting violation alert with ID: {alert_id}")
    
    success = ViolationAlert.delete(alert_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation alert with ID '{alert_id}' not found"
        )
    
    return JSONResponse(
        status_code=200, 
        content={"message": f"Violation alert with ID '{alert_id}' deleted successfully"}
    )

@router.post("/upsert", response_model=ViolationAlert)
async def upsert_violation_alert(record_data: ViolationAlertUpsert):
    """
    Upsert a violation alert (insert or update if exists)
    """
    logger.info("Upserting violation alert record")
    
    record = ViolationAlert.upsert(record_data)
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert violation alert"
        )
    
    return record