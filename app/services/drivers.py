from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session

from helpers import logger
from logic.auth.security import get_current_user
from models.drivers import Driver, DriverCallUpdate


router = APIRouter(
    prefix="/api", dependencies=[Depends(get_current_user)]
)

@router.get("/drivers", response_model=List[Driver])
async def get_all_drivers_data_endpoint(limit: int = 5000):
    logger.info("getting all drivers' data")
    return Driver.get_all(limit=limit)

@router.get("/drivers/{driver_id}", response_model=Driver)
async def get_driver_data_endpoint(driver_id: str):
    logger.info("getting driver's raw data")
    driver = Driver.get_by_id(driver_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver

class CreateDriverRequest(BaseModel):
    firstName: str
    lastName: str
    phoneNumber: str
    status: str = "Active"
    truckId: str = None
    email: str = None
    hiredOn: str = None
    companyId: str = "COMP_001"
    dispatcher: str = None
    firstLanguage: str = "English"
    secondLanguage: str = None
    globalDnd: bool = False
    safetyCall: bool = True
    safetyMessage: bool = True
    hosSupport: bool = True
    maintainanceCall: bool = True
    maintainanceMessage: bool = True
    dispatchCall: bool = True
    dispatchMessage: bool = True
    accountCall: bool = True
    accountMessage: bool = True
    telegramId: str = None


@router.post("/drivers", response_model=dict)
async def create_driver(driver_data: CreateDriverRequest):
    """Create a new driver"""
    try:
        # Generate a unique driver ID
        timestamp = int(datetime.now().timestamp() * 1000)
        driver_id = f"DRV_{timestamp}"
        
        # Create new driver instance
        new_driver = Driver(
            driverId=driver_id,
            status=driver_data.status,
            firstName=driver_data.firstName,
            lastName=driver_data.lastName,
            truckId=driver_data.truckId,
            phoneNumber=driver_data.phoneNumber,
            email=driver_data.email,
            hiredOn=driver_data.hiredOn or datetime.now().isoformat(),
            updatedOn=datetime.now().isoformat(),
            companyId=driver_data.companyId,
            dispatcher=driver_data.dispatcher,
            firstLanguage=driver_data.firstLanguage,
            secondLanguage=driver_data.secondLanguage,
            globalDnd=driver_data.globalDnd,
            safetyCall=driver_data.safetyCall,
            safetyMessage=driver_data.safetyMessage,
            hosSupport=driver_data.hosSupport,
            maintainanceCall=driver_data.maintainanceCall,
            maintainanceMessage=driver_data.maintainanceMessage,
            dispatchCall=driver_data.dispatchCall,
            dispatchMessage=driver_data.dispatchMessage,
            accountCall=driver_data.accountCall,
            accountMessage=driver_data.accountMessage,
            telegramId=driver_data.telegramId,
        )
        
        # Save to database
        with Driver.get_session() as session:
            session.add(new_driver)
            session.commit()
            session.refresh(new_driver)
        
        return {
            "success": True,
            "message": "Driver created successfully",
            "data": new_driver.model_dump(),
        }
        
    except Exception as error:
        logger.error(f"❌ Error creating driver: {str(error)}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "Failed to create driver"}
        )


@router.post("/settings/call/bulk")
async def configure_driver_call_settings(updates: List[DriverCallUpdate]):
    logger.info('updating driver call settings')
    Driver.bulk_update_calling_info(updates)
    return JSONResponse(status_code=200, content={"message": "Driver call settings updated"})
