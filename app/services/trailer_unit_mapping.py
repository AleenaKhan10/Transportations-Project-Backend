from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from helpers import logger
from logic.auth.security import get_current_user
from models.trailer_unit_mapping import TrailerUnitMapping, TrailerUnitMappingCreate, TrailerUnitMappingUpdate


router = APIRouter(
    prefix="/trailer-unit-mappings", 
    dependencies=[Depends(get_current_user)]
)


@router.get("/", response_model=List[TrailerUnitMapping])
async def get_all_trailer_unit_mappings(limit: int = 5000):
    """
    Get all trailer unit mappings
    """
    logger.info("Getting all trailer unit mappings")
    mappings = TrailerUnitMapping.get_all(limit=limit)
    return mappings


@router.get("/unit/{trailer_unit}", response_model=TrailerUnitMapping)
async def get_trailer_unit_mapping_by_unit(trailer_unit: str):
    """
    Get a trailer unit mapping by TrailerUnit
    """
    logger.info(f"Getting trailer unit mapping for unit: {trailer_unit}")
    mapping = TrailerUnitMapping.get_by_trailer_unit(trailer_unit)
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trailer unit mapping with unit '{trailer_unit}' not found"
        )
    
    return mapping


@router.get("/trailer/{trailer_id}", response_model=TrailerUnitMapping)
async def get_trailer_unit_mapping_by_id(trailer_id: int):
    """
    Get trailer unit mapping by TrailerID (returns first match)
    """
    logger.info(f"Getting trailer unit mapping for trailer ID: {trailer_id}")
    mappings = TrailerUnitMapping.get_by_trailer_id(trailer_id)
    
    if not mappings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trailer unit mapping with trailer ID '{trailer_id}' not found"
        )
    
    # Return the first mapping found
    return mappings[0]


@router.post("/upsert", response_model=TrailerUnitMapping)
async def upsert_trailer_unit_mapping(mapping_data: TrailerUnitMappingCreate):
    """
    Upsert a trailer unit mapping (insert or update if exists) - only updates provided fields
    """
    logger.info(f"Upserting trailer unit mapping for unit: {mapping_data.TrailerUnit}")
    
    if not mapping_data.TrailerUnit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TrailerUnit is required for upsert operation"
        )
    
    mapping = TrailerUnitMapping.upsert(
        trailer_unit=mapping_data.TrailerUnit,
        trailer_id=mapping_data.TrailerID
    )
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upsert trailer unit mapping"
        )
    
    return mapping


@router.post("/", response_model=TrailerUnitMapping)
async def create_trailer_unit_mapping(mapping_data: TrailerUnitMappingCreate):
    """
    Create a new trailer unit mapping
    """
    logger.info(f"Creating trailer unit mapping for unit: {mapping_data.TrailerUnit}")
    
    # Check if mapping already exists
    existing = TrailerUnitMapping.get_by_trailer_unit(mapping_data.TrailerUnit)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Trailer unit mapping with unit '{mapping_data.TrailerUnit}' already exists"
        )
    
    mapping = TrailerUnitMapping.create(
        trailer_unit=mapping_data.TrailerUnit,
        trailer_id=mapping_data.TrailerID
    )
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create trailer unit mapping"
        )
    
    return mapping


@router.put("/{trailer_unit}", response_model=TrailerUnitMapping)
async def update_trailer_unit_mapping(trailer_unit: str, mapping_data: TrailerUnitMappingUpdate):
    """
    Update an existing trailer unit mapping
    """
    logger.info(f"Updating trailer unit mapping for unit: {trailer_unit}")
    
    # Check if mapping exists
    existing = TrailerUnitMapping.get_by_trailer_unit(trailer_unit)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trailer unit mapping with unit '{trailer_unit}' not found"
        )
    
    mapping = TrailerUnitMapping.update(
        trailer_unit=trailer_unit,
        trailer_id=mapping_data.TrailerID
    )
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update trailer unit mapping"
        )
    
    return mapping


@router.delete("/{trailer_unit}")
async def delete_trailer_unit_mapping(trailer_unit: str):
    """
    Delete a trailer unit mapping
    """
    logger.info(f"Deleting trailer unit mapping for unit: {trailer_unit}")
    
    # Check if mapping exists
    existing = TrailerUnitMapping.get_by_trailer_unit(trailer_unit)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trailer unit mapping with unit '{trailer_unit}' not found"
        )
    
    success = TrailerUnitMapping.delete(trailer_unit)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete trailer unit mapping"
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Trailer unit mapping '{trailer_unit}' deleted successfully"}
    )