from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from helpers import logger
from logic.auth.security import get_current_user
from models.drivers import Driver, DriverCallUpdate


router = APIRouter(
    prefix="/drivers", dependencies=[Depends(get_current_user)]
)

@router.get("/raw", response_model=List[Driver])
async def get_all_drivers_data_endpoint(limit: int = 5000):
    logger.info("getting all drivers' data")
    return Driver.get_all(limit=limit)

@router.get("/raw/{driver_id}", response_model=Driver)
async def get_driver_data_endpoint(driver_id: str):
    logger.info("getting driver's raw data")
    return Driver.get_by_id(driver_id)

@router.post("/settings/call/bulk")
async def configure_driver_call_settings(updates: List[DriverCallUpdate]):
    logger.info('updating driver call settings')
    Driver.bulk_update_calling_info(updates)
    return JSONResponse(status_code=200, content={"message": "Driver call settings updated"})
