from fastapi import APIRouter, HTTPException
from models.driver_triggers import DriverTriggersData
from pydantic import BaseModel
from typing import List, Optional, Dict


class Driver(BaseModel):
    driverId: str
    name: str
    phone: str


class DriverReminders(BaseModel):
    id: int
    message: str


class DriverTriggerRequest(BaseModel):
    driver: Driver
    selectedReminders: List[DriverReminders]
    selectedViolations: List[DriverReminders]


# Router with prefix + tags
router = APIRouter(prefix="/driver_triggers", tags=["driver_triggers"])


@router.get("/{driver_id}")
def get_trip_driverId(driver_id: str):
    result = DriverTriggersData.get_trip_by_driver_id(driver_id)
    return result


# @router.post("/")
# def check_driver_triggers(payload: dict):
#     return DriverTriggersData.get_driver_trigger(payload)


@router.post("/")
def get_trip_driver_id(request: DriverTriggerRequest):
    return DriverTriggersData.get_driver_trigger(request.dict())
