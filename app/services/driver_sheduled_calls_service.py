from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from models.driver_sheduled_calls import DriverSheduledCalls
import uuid

router = APIRouter(prefix="/driver_sheduled_calls", tags=["driver_sheduled_calls"])

# --------------------------------------------------------
# Input Schema
# --------------------------------------------------------
class ScheduleCreateRequest(BaseModel):
    call_scheduled_date_time: datetime
    
    # Yeh array ab simple names ki nahi, balky checkbox values (strings) ki hai
    drivers: List[str]      
    
    reminders: List[str]    
    violations: List[str]   

# --------------------------------------------------------
# GET Endpoint
# --------------------------------------------------------
@router.get("/", response_model=List[DriverSheduledCalls])
def fetch_all_driver_sheduled_calls():
    try:
        data = DriverSheduledCalls.get_all_sheduled_call_records()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------
# POST Endpoint
# --------------------------------------------------------
@router.post("/", status_code=201)
def create_driver_schedule(payload: ScheduleCreateRequest):
    try:
        result = DriverSheduledCalls.create_bulk_schedule(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------
# GET Endpoint: Search by Record ID or Group ID
# --------------------------------------------------------
@router.get("/{query_id}", response_model=List[DriverSheduledCalls])
def get_schedule_by_id_or_group(query_id: uuid.UUID):
    try:
        # Model wala function call kiya
        records = DriverSheduledCalls.get_by_id_or_group(query_id)
        
        # Agar list khali hai, iska matlab ID ghalat hai
        if not records:
            raise HTTPException(status_code=404, detail="No records found for this ID (neither Record ID nor Group ID)")
            
        return records
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))