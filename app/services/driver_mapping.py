from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from helpers import logger
from logic.auth.security import get_current_user
from models.driver_mapping import (
    DriverMapping,
    DriverMappingCreate,
    DriverMappingUpdate,
    DriverMappingResponse
)


router = APIRouter(
    prefix="/api/v1/driver-mapping",
    dependencies=[Depends(get_current_user)]
)


@router.get("/", response_model=Dict[str, Any])
async def get_driver_mappings(
    driverid: Optional[str] = Query(None, description="Filter by driver ID"),
    driverkey: Optional[str] = Query(None, description="Filter by driver key"),
    driverfullname: Optional[str] = Query(None, description="Filter by driver full name (case-insensitive partial match)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return (default: 100, max: 1000)"),
    offset: int = Query(0, ge=0, description="Pagination offset (default: 0)"),
    sort: Optional[str] = Query(None, description="Sort field (e.g., 'driverid', '-driverid' for DESC)")
):
    """
    Get driver mappings with flexible filtering through query parameters.

    All parameters are optional. When no parameters are provided, returns all records (with pagination).
    Multiple parameters can be combined for AND filtering.

    Examples:
    - Get all records: GET /api/v1/driver-mapping
    - Filter by driverid: GET /api/v1/driver-mapping?driverid=1122965
    - Filter by driverkey: GET /api/v1/driver-mapping?driverkey=91
    - Filter by name: GET /api/v1/driver-mapping?driverfullname=HOWARD
    - Combined filters: GET /api/v1/driver-mapping?driverkey=91&driverid=1122965
    - With pagination: GET /api/v1/driver-mapping?limit=50&offset=100
    - With sorting: GET /api/v1/driver-mapping?sort=-driverid
    """
    logger.info(f"Getting driver mappings with filters - driverid: {driverid}, driverkey: {driverkey}, driverfullname: {driverfullname}")

    result = DriverMapping.get_with_filters(
        driverid=driverid,
        driverkey=driverkey,
        driverfullname=driverfullname,
        limit=limit,
        offset=offset,
        sort=sort
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to retrieve driver mappings")
        )

    return result


@router.get("/{driverid}", response_model=DriverMappingResponse)
async def get_driver_mapping_by_id(driverid: str):
    """
    Get a specific driver mapping by driverid
    """
    logger.info(f"Getting driver mapping for driverid: {driverid}")
    mapping = DriverMapping.get_by_driverid(driverid)

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver mapping with driverid '{driverid}' not found"
        )

    return mapping


@router.post("/", response_model=DriverMappingResponse)
async def create_driver_mapping(mapping_data: DriverMappingCreate):
    """
    Create a new driver mapping
    """
    logger.info(f"Creating driver mapping for driverid: {mapping_data.driverid}")

    # Check if mapping already exists
    existing = DriverMapping.get_by_driverid(mapping_data.driverid)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Driver mapping with driverid '{mapping_data.driverid}' already exists"
        )

    mapping = DriverMapping.create(
        driverid=mapping_data.driverid,
        driverkey=mapping_data.driverkey,
        driverfullname=mapping_data.driverfullname
    )

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create driver mapping"
        )

    return mapping


@router.put("/{driverid}", response_model=DriverMappingResponse)
async def update_driver_mapping(driverid: str, mapping_data: DriverMappingUpdate):
    """
    Update an existing driver mapping
    """
    logger.info(f"Updating driver mapping for driverid: {driverid}")

    # Check if mapping exists
    existing = DriverMapping.get_by_driverid(driverid)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver mapping with driverid '{driverid}' not found"
        )

    mapping = DriverMapping.update(
        driverid=driverid,
        driverkey=mapping_data.driverkey,
        driverfullname=mapping_data.driverfullname
    )

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update driver mapping"
        )

    return mapping


@router.delete("/{driverid}")
async def delete_driver_mapping(driverid: str):
    """
    Delete a driver mapping
    """
    logger.info(f"Deleting driver mapping for driverid: {driverid}")

    # Check if mapping exists
    existing = DriverMapping.get_by_driverid(driverid)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver mapping with driverid '{driverid}' not found"
        )

    success = DriverMapping.delete(driverid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete driver mapping"
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Driver mapping with driverid '{driverid}' deleted successfully"}
    )