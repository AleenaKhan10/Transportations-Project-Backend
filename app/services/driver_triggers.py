from fastapi import APIRouter, HTTPException
from models.driver_triggers import DriverTriggersData, make_vapi_call
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
async def make_driver_vapi_call(request: DriverTriggerRequest):
    driver_data = DriverTriggersData.get_driver_trigger(request.dict())
    # Make the VAPI call and get the returned response data
    vapi_result = await make_vapi_call(driver_data)

    # Return both success message, driver info, and full VAPI API response
    return {
        "message": "Driver call initiated successfully",
        "driver": driver_data,
        "vapi_response": vapi_result.get("vapi_response"),
    }
