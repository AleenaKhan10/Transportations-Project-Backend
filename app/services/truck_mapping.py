from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from helpers import logger
from logic.auth.security import get_current_user
from models.truck_mapping import TruckMapping, TruckMappingCreate, TruckMappingUpdate


router = APIRouter(
    prefix="/truck-mappings", 
    dependencies=[Depends(get_current_user)]
)


@router.get("/", response_model=List[TruckMapping])
async def get_all_truck_mappings(limit: int = 5000):
    """
    Get all truck mappings
    """
    logger.info("Getting all truck mappings")
    mappings = TruckMapping.get_all(limit=limit)
    return mappings


@router.get("/unit/{truck_unit}", response_model=TruckMapping)
async def get_truck_mapping_by_unit(truck_unit: str):
    """
    Get a truck mapping by TruckUnit
    """
    logger.info(f"Getting truck mapping for unit: {truck_unit}")
    mapping = TruckMapping.get_by_truck_unit(truck_unit)
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Truck mapping with unit '{truck_unit}' not found"
        )
    
    return mapping


@router.get("/truck/{truck_id}", response_model=TruckMapping)
async def get_truck_mapping_by_id(truck_id: int):
    """
    Get truck mapping by TruckId (returns first match)
    """
    logger.info(f"Getting truck mapping for truck ID: {truck_id}")
    mappings = TruckMapping.get_by_truck_id(truck_id)
    
    if not mappings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Truck mapping with truck ID '{truck_id}' not found"
        )
    
    # Return the first mapping found
    return mappings[0]


@router.post("/upsert", response_model=TruckMapping)
async def upsert_truck_mapping(mapping_data: TruckMappingCreate):
    """
    Upsert a truck mapping (insert or update if exists) - only updates provided fields
    """
    logger.info(f"Upserting truck mapping for unit: {mapping_data.TruckUnit}")
    
    if not mapping_data.TruckUnit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TruckUnit is required for upsert operation"
        )
    
    mapping = TruckMapping.upsert(
        truck_unit=mapping_data.TruckUnit,
        truck_id=mapping_data.TruckId
    )
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert truck mapping"
        )
    
    return mapping


@router.post("/", response_model=TruckMapping)
async def create_truck_mapping(mapping_data: TruckMappingCreate):
    """
    Create a new truck mapping
    """
    logger.info(f"Creating truck mapping for unit: {mapping_data.TruckUnit}")
    
    # Check if mapping already exists
    existing = TruckMapping.get_by_truck_unit(mapping_data.TruckUnit)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Truck mapping with unit '{mapping_data.TruckUnit}' already exists"
        )
    
    mapping = TruckMapping.create(
        truck_unit=mapping_data.TruckUnit,
        truck_id=mapping_data.TruckId
    )
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create truck mapping"
        )
    
    return mapping


@router.put("/{truck_unit}", response_model=TruckMapping)
async def update_truck_mapping(truck_unit: str, mapping_data: TruckMappingUpdate):
    """
    Update an existing truck mapping
    """
    logger.info(f"Updating truck mapping for unit: {truck_unit}")
    
    # Check if mapping exists
    existing = TruckMapping.get_by_truck_unit(truck_unit)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Truck mapping with unit '{truck_unit}' not found"
        )
    
    mapping = TruckMapping.update(
        truck_unit=truck_unit,
        truck_id=mapping_data.TruckId
    )
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update truck mapping"
        )
    
    return mapping


@router.delete("/{truck_unit}")
async def delete_truck_mapping(truck_unit: str):
    """
    Delete a truck mapping
    """
    logger.info(f"Deleting truck mapping for unit: {truck_unit}")
    
    # Check if mapping exists
    existing = TruckMapping.get_by_truck_unit(truck_unit)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Truck mapping with unit '{truck_unit}' not found"
        )
    
    success = TruckMapping.delete(truck_unit)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete truck mapping"
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Truck mapping '{truck_unit}' deleted successfully"}
    )