from fastapi import APIRouter, HTTPException, Body
from models.driver_triggers_violations_calls import DriverTriggersViolationCalls
from typing import List
import uuid

router = APIRouter(
    prefix="/drivers_triggers_violation_calls",
    tags=["drivers_triggers_violation_calls"],
)


# ----------------------------------------------------
# GET: All Records
# ----------------------------------------------------
@router.get("/", response_model=List[DriverTriggersViolationCalls])
def get_all_records_violations():
    return DriverTriggersViolationCalls.get_all_records_violations()


# ----------------------------------------------------
# GET: Record by ID
# ----------------------------------------------------
@router.get("/{record_id}", response_model=DriverTriggersViolationCalls)
def get_record_by_id(record_id: uuid.UUID):
    record = DriverTriggersViolationCalls.get_violation_record_by_id(record_id)

    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    return record


# ----------------------------------------------------
# POST: Create New Record
# ----------------------------------------------------
@router.post("/", response_model=DriverTriggersViolationCalls, status_code=201)
def create_violation_record(payload: dict):
    try:
        record = DriverTriggersViolationCalls.create_violation_data(payload)
        return record
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to create record: {str(e)}"
        )


# ----------------------------------------------------
# PUT: Update Record by call_id
# ----------------------------------------------------
@router.put("/update_by_call_id/{call_id}", response_model=DriverTriggersViolationCalls)
def update_violation_record_by_call_id(call_id: str, payload: dict = Body(...)):
    record = DriverTriggersViolationCalls.update_violation_by_call_id(call_id, payload)

    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    return record
