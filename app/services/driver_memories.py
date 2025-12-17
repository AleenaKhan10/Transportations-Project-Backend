from fastapi import APIRouter, HTTPException
from models.driver_memories import DriverMemories
from sqlmodel import text

# Router with prefix + tags
router = APIRouter(prefix="/driver_memories", tags=["driver_memories"])


# 1. Return all memored
@router.get("/")
def get_all_memories():
    memories = DriverMemories.get_all_driver_memories()  # ✅ call via class
    return {
        "message": "Memories fetched successfully",
        "data": memories,
    }
