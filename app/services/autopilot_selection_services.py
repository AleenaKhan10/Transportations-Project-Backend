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

class DriverSelectionResponse(BaseModel):
    id: uuid.UUID
    driverid: str
    drivername: str
    dispatch_selection: bool
    updated_at: datetime

    class Config:
        from_attributes = True

# --------------------------------------------------------
# GET Endpoint - Fetch all drivers
# --------------------------------------------------------
@router.get("/", response_model=List[DriverSelectionResponse])
def get_autopilot_drivers():
    """
    Get list of all drivers and their current dispatch status.
    """
    try:
        results = AutopilotSelection.get_all_drivers()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------
# PUT Endpoint - BULK UPDATE
# --------------------------------------------------------
# --- 1. NEW INPUT SCHEMA (Simple List of Strings) ---
class DriverSelectionListRequest(BaseModel):
    driver_ids: List[str] 

# --- 2. PUT ENDPOINT (Updated Logic) ---
@router.put("/", status_code=200)
def update_autopilot_selection(payload: DriverSelectionListRequest):
    """
    Payload Example:
    {
      "driver_ids": ["DRV-001", "DRV-005"]
    }
    Logic: "DRV-001" and "DRV-005" will become TRUE. Everyone else becomes FALSE.
    """
    try:
        # Hum direct model function call karenge list pass karke
        result = AutopilotSelection.sync_drivers_status(payload.driver_ids)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))