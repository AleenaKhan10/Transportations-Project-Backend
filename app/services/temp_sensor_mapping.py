from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from helpers import logger
from logic.auth.security import get_current_user
from models.temp_sensor_mapping import TempSensorMapping, TempSensorMappingCreate, TempSensorMappingUpdate


router = APIRouter(
    prefix="/temp-sensor-mappings", 
    dependencies=[Depends(get_current_user)]
)


@router.get("/", response_model=List[TempSensorMapping])
async def get_all_temp_sensor_mappings(limit: int = 5000):
    """
    Get all temp sensor mappings
    """
    logger.info("Getting all temp sensor mappings")
    mappings = TempSensorMapping.get_all(limit=limit)
    return mappings


@router.get("/name/{sensor_name}", response_model=TempSensorMapping)
async def get_temp_sensor_mapping_by_name(sensor_name: str):
    """
    Get a temp sensor mapping by TempSensorNAME
    """
    logger.info(f"Getting temp sensor mapping for name: {sensor_name}")
    mapping = TempSensorMapping.get_by_sensor_name(sensor_name)
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Temp sensor mapping with name '{sensor_name}' not found"
        )
    
    return mapping


@router.get("/sensor/{sensor_id}", response_model=TempSensorMapping)
async def get_temp_sensor_mapping_by_id(sensor_id: int):
    """
    Get temp sensor mapping by TempSensorID (returns first match)
    """
    logger.info(f"Getting temp sensor mapping for sensor ID: {sensor_id}")
    mappings = TempSensorMapping.get_by_sensor_id(sensor_id)
    
    if not mappings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Temp sensor mapping with sensor ID '{sensor_id}' not found"
        )
    
    # Return the first mapping found
    return mappings[0]


@router.post("/", response_model=TempSensorMapping)
async def create_temp_sensor_mapping(mapping_data: TempSensorMappingCreate):
    """
    Create a new temp sensor mapping
    """
    logger.info(f"Creating temp sensor mapping for name: {mapping_data.TempSensorNAME}")
    
    # Check if mapping already exists
    existing = TempSensorMapping.get_by_sensor_name(mapping_data.TempSensorNAME)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Temp sensor mapping with name '{mapping_data.TempSensorNAME}' already exists"
        )
    
    mapping = TempSensorMapping.create(
        sensor_name=mapping_data.TempSensorNAME,
        sensor_id=mapping_data.TempSensorID
    )
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create temp sensor mapping"
        )
    
    return mapping


@router.put("/{sensor_name}", response_model=TempSensorMapping)
async def update_temp_sensor_mapping(sensor_name: str, mapping_data: TempSensorMappingUpdate):
    """
    Update an existing temp sensor mapping
    """
    logger.info(f"Updating temp sensor mapping for name: {sensor_name}")
    
    # Check if mapping exists
    existing = TempSensorMapping.get_by_sensor_name(sensor_name)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Temp sensor mapping with name '{sensor_name}' not found"
        )
    
    mapping = TempSensorMapping.update(
        sensor_name=sensor_name,
        sensor_id=mapping_data.TempSensorID
    )
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update temp sensor mapping"
        )
    
    return mapping


@router.delete("/{sensor_name}")
async def delete_temp_sensor_mapping(sensor_name: str):
    """
    Delete a temp sensor mapping
    """
    logger.info(f"Deleting temp sensor mapping for name: {sensor_name}")
    
    # Check if mapping exists
    existing = TempSensorMapping.get_by_sensor_name(sensor_name)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Temp sensor mapping with name '{sensor_name}' not found"
        )
    
    success = TempSensorMapping.delete(sensor_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete temp sensor mapping"
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Temp sensor mapping '{sensor_name}' deleted successfully"}
    )