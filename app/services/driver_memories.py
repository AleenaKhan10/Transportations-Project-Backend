from fastapi import APIRouter, HTTPException
from models.driver_memories import DriverMemories, DriverMemoriesResponse
from sqlmodel import text
from typing import List

# Router with prefix + tags
router = APIRouter(prefix="/driver_memories", tags=["driver_memories"])


# 1. Return all memories
@router.get("/")
def get_all_memories():
    memories = DriverMemories.get_all_driver_memories()  # ✅ call via class
    # Convert to response schema to exclude embedding (numpy array can't be serialized)
    response_data: List[DriverMemoriesResponse] = [
        DriverMemoriesResponse.model_validate(memory) for memory in memories
    ]
    return {
        "message": "Memories fetched successfully",
        "data": response_data,
    }
