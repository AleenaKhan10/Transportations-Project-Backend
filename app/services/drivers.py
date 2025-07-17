from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from logic.auth.security import get_current_user
from helpers import logger
from models.drivers import Driver, DriverResponse, DriverCallUpdate


router = APIRouter(
    prefix="/drivers", dependencies=[Depends(get_current_user)]
)

@router.post("/settings/call/bulk")
async def configure_driver_call_settings(updates: List[DriverCallUpdate]):
    logger.info('updating driver call settings')
    Driver.bulk_update_calling_info(updates)
    return JSONResponse(status_code=200, content={"message": "Driver call settings updated"})

@router.get("/raw", response_model=List[Driver])
async def get_all_drivers_data_endpoint(limit: int = 5000):
    logger.info("getting all drivers' raw data")
    return Driver.get_all(limit=limit)

@router.get("/json", response_model=List[DriverResponse])
async def get_all_drivers_data_structured(limit: int = 5000):
    logger.info("getting all drivers' structured data")
    return Driver.get_all_structured(limit=limit)
