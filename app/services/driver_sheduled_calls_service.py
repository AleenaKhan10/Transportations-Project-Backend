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
    
    # List of strings because from frontend, it is an array of checkboxes
    drivers: List[str]      
    # Same for reminders (Array of strings)
    reminders: List[str]
    # Same for violations (Array of strings)    
    violations: List[str]  
    

# --------------------------------------------------------
# UPDATE SCHEMA (Complete Payload expected)
# --------------------------------------------------------
class ScheduleUpdateRequest(BaseModel):
    call_scheduled_date_time: datetime
    driver: str             # Single string (Updates only when at a time)
    status: bool            # Whatever the status is send from frontend
    reminders: List[str]    # Array 
    violations: List[str]   # Array 

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
        # Calling the function of get_by_id_or_group
        records = DriverSheduledCalls.get_by_id_or_group(query_id)
        
        # If found nothing, it returns simply that neither of the id's were found
        if not records:
            raise HTTPException(status_code=404, detail="No records found for this ID (neither Record ID nor Group ID)")
            
        return records
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# --------------------------------------------------------
# DELETE ENDPOINT (Strictly by ID)
# --------------------------------------------------------
@router.delete("/{record_id}", status_code=200)
def delete_driver_schedule(record_id: uuid.UUID):
    try:
        # Calling function that deletes the record by id from model file
        is_deleted = DriverSheduledCalls.delete_record_by_id(record_id)
        
        if not is_deleted:
            # If not found, or a group id has been passed, it will return this
            raise HTTPException(status_code=404, detail="Record not found with this ID")
        
        return {"message": "Record deleted successfully"}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# --------------------------------------------------------
# UPDATE ENDPOINT (PUT - Complete Payload)
# --------------------------------------------------------
@router.put("/{record_id}", response_model=DriverSheduledCalls)
def update_driver_schedule(record_id: uuid.UUID, payload: ScheduleUpdateRequest):
    try:
        # 1.Converting payload into dictionary
        update_data = payload.dict()

        # 2. Need to convert arrays into string (DB Format)
        # Agar list khali hui tow Empty string jayegi ya None
        update_data["reminder"] = ", ".join(payload.reminders) if payload.reminders else None
        update_data["violation"] = ", ".join(payload.violations) if payload.violations else None
        
        # 3. Purani Lists (reminders, violations) ko dictionary se nikal do
        # Kyun ke DB model mein yeh columns exist nahi karte, wahan 'reminder' (singular) hai.
        update_data.pop("reminders", None)
        update_data.pop("violations", None)

        # 4. Model function call karo
        updated_record = DriverSheduledCalls.update_record(record_id, update_data)
        
        if not updated_record:
            raise HTTPException(status_code=404, detail="Record not found")
            
        return updated_record

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))