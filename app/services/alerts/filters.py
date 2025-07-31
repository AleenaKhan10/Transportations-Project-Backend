from fastapi import APIRouter, Body, Depends, HTTPException

from logic.alerts import (
    get_all_alert_filters,
    get_excluded_alert_filters,
    get_alert_filter_by_id,
    get_alert_filter_by_entity_id,
    create_alert_filter_db,
    update_alert_filter_by_id,
    update_alert_filter_by_entity_id,
    delete_alert_filter_by_id,
    delete_alert_filter_by_entity_id,
)
from logic.auth.security import get_current_user
from helpers.agy_utils import validate_entity_id_in_path
from models.alert_filter import AlertFilterCreate, AlertFilter, AlertFilterUpdate


router = APIRouter(prefix="/filters", dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[AlertFilter])
async def get_alert_filters(only_muted: bool = False):
    return get_excluded_alert_filters() if only_muted else get_all_alert_filters()


@router.post("/", response_model=AlertFilter)
async def create_alert_filter(alert_filter: AlertFilterCreate):
    new_filter_or_message = create_alert_filter_db(alert_filter)
    if not new_filter_or_message or isinstance(new_filter_or_message, str):
        raise HTTPException(status_code=400, detail=new_filter_or_message)
    return new_filter_or_message


@router.get("/entities/{entity_id}", response_model=AlertFilter)
async def get_alert_filter_with_entity_id(entity_id: str = Depends(validate_entity_id_in_path)):
    alert_filter = get_alert_filter_by_entity_id(entity_id)
    if not alert_filter:
        raise HTTPException(status_code=404, detail="Filter not found")
    return alert_filter


@router.put("/entities/{entity_id}", response_model=AlertFilter)
async def update_alert_filter_with_entity_id(
    entity_id: str = Depends(validate_entity_id_in_path),
    alert_filter: AlertFilterUpdate = Body(...),
):
    updated_filter = update_alert_filter_by_entity_id(entity_id, alert_filter)
    if not updated_filter:
        raise HTTPException(status_code=404, detail="Filter not found or update failed")
    return updated_filter


@router.delete("/entities/{entity_id}")
async def delete_alert_filter_with_entity_id(entity_id: str = Depends(validate_entity_id_in_path)):
    result = delete_alert_filter_by_entity_id(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Filter not found")
    return result


@router.get("/{filter_id}", response_model=AlertFilter)
async def get_alert_filter_with_id(filter_id: int):
    alert_filter = get_alert_filter_by_id(filter_id)
    if not alert_filter:
        raise HTTPException(status_code=404, detail="Filter not found")
    return alert_filter


@router.put("/{filter_id}", response_model=AlertFilter)
async def update_alert_filter_with_id(
    filter_id: int,
    alert_filter: AlertFilterUpdate = Body(...),
):
    updated_filter = update_alert_filter_by_id(filter_id, alert_filter)
    if not updated_filter:
        raise HTTPException(status_code=404, detail="Filter not found or update failed")
    return updated_filter


@router.delete("/{filter_id}")
async def delete_alert_filter_with_id(filter_id: int):
    result = delete_alert_filter_by_id(filter_id)
    if not result:
        raise HTTPException(status_code=404, detail="Filter not found")
    return result
