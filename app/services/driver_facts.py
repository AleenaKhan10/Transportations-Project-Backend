from fastapi import APIRouter, HTTPException
from models.driver_facts import DriverFacts
from sqlmodel import text
from typing import List

# Router with prefix + tags
router = APIRouter(prefix="/driver_facts", tags=["driver_facts"])


@router.get("/")
def get_all_driver_facts():
    driver_facts = DriverFacts.get_all_driver_facts()
    return {
        "message": "driver facts fetched successfully",
        "data": driver_facts,
    }
