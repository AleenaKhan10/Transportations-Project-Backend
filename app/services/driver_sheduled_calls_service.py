from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import List, Optional, Any
from datetime import datetime
from models.driver_sheduled_calls import DriverSheduledCalls
import uuid

router = APIRouter(prefix="/driver_sheduled_calls", tags=["driver_sheduled_calls"])

# --------------------------------------------------------
# 1. RESPONSE MODEL (The Translator)
#    Yeh model decide karega ke Frontend ko data kaisa dikhega
# --------------------------------------------------------
class DriverScheduleResponse(BaseModel):
    id: uuid.UUID
    schedule_group_id: uuid.UUID
    driver: Optional[str] = None
    call_scheduled_date_time: datetime
    status: bool
    created_at: datetime
    updated_at: datetime
    
    # Notice: Type is List[str], but DB has String
    reminders: List[str] = []   
    violations: List[str] = []

    # --- MAGIC HAPPENS HERE (Validators) ---
    
    @field_validator('reminders', mode='before')
    def parse_reminders(cls, v: Any) -> List[str]:
        # Agar DB se string aayi (e.g., "Helmet, Speed")
        if isinstance(v, str):
            if not v.strip(): return [] # Agar empty string hai tow empty list
            return [item.strip() for item in v.split(',')]
        # Agar already list hai ya None hai
        return v if v else []

    @field_validator('violations', mode='before')
    def parse_violations(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            if not v.strip(): return []
            return [item.strip() for item in v.split(',')]
        return v if v else []

    class Config:
        # Yeh zaroori hai taaky Pydantic SQLModel object ko read kar sakey
        from_attributes = True 

# --------------------------------------------------------
# Input Schema for Create/Update (As it is)
# --------------------------------------------------------
class ScheduleCreateRequest(BaseModel):
    call_scheduled_date_time: datetime
    drivers: List[str]
    reminders: List[str]
    violations: List[str]

class ScheduleUpdateRequest(BaseModel):
    call_scheduled_date_time: datetime
    driver: str
    status: bool
    reminders: List[str]
    violations: List[str]

# --------------------------------------------------------
# GET Endpoint (Updated response_model)
# --------------------------------------------------------
@router.get("/", response_model=List[DriverScheduleResponse])
def fetch_all_driver_sheduled_calls():
    try:
        # 1. DB se Raw Data (Strings wala) ayega
        db_records = DriverSheduledCalls.get_all_sheduled_call_records()
        
        # 2. Humne 'reminder' (singular) ko 'reminders' (plural) mein map karna hai
        # Kyun k DB me column ka naam 'reminder' hai lekin Response Model me 'reminders' hai
        results = []
        for record in db_records:
            # Hum manually object bana rahy hain taaky mapping sahi ho
            results.append(DriverScheduleResponse(
                id=record.id,
                schedule_group_id=record.schedule_group_id,
                driver=record.driver,
                call_scheduled_date_time=record.call_scheduled_date_time,
                status=record.status,
                created_at=record.created_at,
                updated_at=record.updated_at,
                # YAHAN MAPPING HO RAHI HAI: DB column -> Response field
                reminders=record.reminder, 
                violations=record.violation 
            ))
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------
# GET BY ID (Updated response_model)
# --------------------------------------------------------
@router.get("/{query_id}", response_model=List[DriverScheduleResponse])
def get_schedule_by_id_or_group(query_id: uuid.UUID):
    try:
        db_records = DriverSheduledCalls.get_by_id_or_group(query_id)
        if not db_records:
            raise HTTPException(status_code=404, detail="No records found")
            
        # Converting DB objects to Response objects
        results = []
        for record in db_records:
            results.append(DriverScheduleResponse(
                id=record.id,
                schedule_group_id=record.schedule_group_id,
                driver=record.driver,
                call_scheduled_date_time=record.call_scheduled_date_time,
                status=record.status,
                created_at=record.created_at,
                updated_at=record.updated_at,
                reminders=record.reminder,   # Passing string, Validator will make it List
                violations=record.violation  # Passing string, Validator will make it List
            ))
        return results
    except HTTPException as he:
        raise he
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