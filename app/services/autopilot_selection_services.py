from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

# Import your model
from models.autopilot_selection_model import AutopilotSelection

router = APIRouter(prefix="/autopilot-selection", tags=["autopilot_selection"])

# --------------------------------------------------------
# SCHEMAS (Pydantic Models)
# --------------------------------------------------------

# 1. Output Model (Response)
class DriverSelectionResponse(BaseModel):
    id: uuid.UUID
    driverid: str
    drivername: str
    dispatch_selection: bool
    updated_at: datetime

    class Config:
        from_attributes = True

# 2. Input Item Model (Single Driver Update)
class DriverUpdateItem(BaseModel):
    driverid: str
    dispatch_selection: bool

# --------------------------------------------------------
# GET Endpoint
# --------------------------------------------------------
@router.get("/", response_model=List[DriverSelectionResponse])
def get_autopilot_drivers():
    try:
        results = AutopilotSelection.get_all_drivers()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------
# PUT Endpoint - SELECTIVE BULK UPDATE
# --------------------------------------------------------
@router.put("/", status_code=200)
def update_autopilot_selection(payload: List[DriverUpdateItem]):
    """
    Payload Example:
    [
      {"driverid": "TEST_001", "dispatch_selection": false},
      {"driverid": "584AARON", "dispatch_selection": true}
    ]
    Logic: Only update these specific drivers. Ignore everyone else.
    """
    try:
        # Pydantic list ko simple list of dicts mein convert karo
        updates_data = [item.dict() for item in payload]

        if not updates_data:
             raise HTTPException(status_code=400, detail="Payload cannot be empty")

        # Model function call
        result = AutopilotSelection.bulk_update_drivers_status(updates_data)
        
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))