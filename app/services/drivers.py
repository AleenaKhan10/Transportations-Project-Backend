from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
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

# @router.get("/json", response_model=List[DriverResponse])
# async def get_all_drivers_data_structured(limit: int = 5000):
#     logger.info("getting all drivers' structured data")
#     return Driver.get_all_structured(limit=limit)

@router.get("/raw/{driver_id}", response_model=Driver)
async def get_driver_data_endpoint(driver_id: str):
    logger.info("getting driver's raw data")
    return Driver.get_by_id(driver_id)


@router.get("/telegram/{telegram_id}", response_model=Driver)
async def get_driver_by_telegram_id(telegram_id: str):
    """
    Get a driver by their Telegram ID
    """
    logger.info(f"Getting driver by telegram ID: {telegram_id}")
    
    driver = Driver.get_by_telegram_id(telegram_id)
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with Telegram ID '{telegram_id}' not found"
        )
    
    return driver

# @router.get("/json/{driver_id}", response_model=DriverResponse)
# async def get_driver_data_structured(driver_id: str):
#     logger.info("getting driver's structured data")
#     return Driver.get_by_id(driver_id).to_structured_response()


@router.post("/upsert", response_model=Driver)
async def upsert_driver(driver_data: DriverCallUpdate):
    """
    Upsert a single driver (insert or update if exists)
    """
    logger.info(f"Upserting driver with ID: {driver_data.driverId}")
    
    if not driver_data.driverId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="driverId is required for upsert operation"
        )
    
    driver = Driver.upsert(driver_data)
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert driver"
        )
    
    return driver


@router.post("/upsert/bulk", response_model=List[Driver])
async def bulk_upsert_drivers(drivers_data: List[DriverCallUpdate]):
    """
    Bulk upsert multiple drivers (insert or update if exists)
    """
    logger.info(f"Bulk upserting {len(drivers_data)} drivers")
    
    # Validate that all drivers have driverId
    for i, driver_data in enumerate(drivers_data):
        if not driver_data.driverId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"driverId is required for driver at index {i}"
            )
    
    drivers = Driver.bulk_upsert(drivers_data)
    
    if not drivers:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk upsert drivers"
        )
    
    return drivers


@router.post("/settings/call/bulk")
async def configure_driver_call_settings(updates: List[DriverCallUpdate]):
    logger.info('updating driver call settings')
    Driver.bulk_update_calling_info(updates)
    return JSONResponse(status_code=200, content={"message": "Driver call settings updated"})
