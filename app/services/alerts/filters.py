from fastapi import APIRouter, Depends, HTTPException

from logic.alerts import (
    get_all_alert_filters,
    get_alert_filter_by_id,
    create_alert_filter_db,
    update_alert_filter_db,
    delete_alert_filter_db,
)
from logic.auth.security import get_current_user

from models.alert_filter import AlertFilterCreate, AlertFilter, AlertFilterUpdate


router = APIRouter(prefix="/filters", dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[AlertFilter])
async def get_alert_filters():
    return get_all_alert_filters()

@router.get("/{filter_id}", response_model=AlertFilter)
async def get_alert_filter(filter_id: int):
    alert_filter = get_alert_filter_by_id(filter_id)
    if not alert_filter:
        raise HTTPException(status_code=404, detail="Filter not found")
    return alert_filter

@router.post("/", response_model=AlertFilter)
async def create_alert_filter(alert_filter: AlertFilterCreate):
    new_filter = create_alert_filter_db(alert_filter)
    if not new_filter:
        raise HTTPException(status_code=400, detail="Failed to create alert filter")
    return new_filter

@router.put("/{filter_id}", response_model=AlertFilter)
async def update_alert_filter(filter_id: int, alert_filter: AlertFilterUpdate):
    updated_filter = update_alert_filter_db(filter_id, alert_filter)
    if not updated_filter:
        raise HTTPException(status_code=404, detail="Filter not found or update failed")
    return updated_filter

@router.delete("/{filter_id}")
async def delete_alert_filter(filter_id: int):
    result = delete_alert_filter_db(filter_id)
    if not result:
        raise HTTPException(status_code=404, detail="Filter not found")
    return result
