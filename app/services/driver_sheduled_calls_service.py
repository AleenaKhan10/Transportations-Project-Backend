from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict


# Router with prefix + tags
router = APIRouter(prefix="/driver_sheduled_calls", tags=["driver_sheduled_calls"])
