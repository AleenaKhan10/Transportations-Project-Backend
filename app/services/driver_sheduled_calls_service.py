from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from models.driver_sheduled_calls import DriverSheduledCalls


# Router with prefix + tags
router = APIRouter(prefix="/driver_sheduled_calls", tags=["driver_sheduled_calls"])


@router.get("/", response_model=List[DriverSheduledCalls])
def fetch_all_driver_sheduled_calls():
    try:
        data = DriverSheduledCalls.get_all_sheduled_call_records()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
