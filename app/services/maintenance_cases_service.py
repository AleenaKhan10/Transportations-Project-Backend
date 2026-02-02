"""
Maintenance Cases API endpoints.

This module provides REST API endpoints for:
1. Searching similar maintenance cases (for Maintenance Agent)
2. CRUD operations on maintenance cases (knowledge base)
3. Converting resolved tickets to cases

Endpoints:
    POST   /maintenance-cases/search-similar   - Search similar cases (ElevenLabs)
    POST   /maintenance-cases                  - Create new case
    GET    /maintenance-cases                  - List all cases (with filters)
    GET    /maintenance-cases/{id}             - Get single case
    PUT    /maintenance-cases/{id}             - Update case
    DELETE /maintenance-cases/{id}             - Delete case
    POST   /maintenance-cases/from-ticket      - Convert ticket to case
    GET    /maintenance-cases/health           - Health check for embedding service
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from models.maintenance_case import MaintenanceCase, CaseCategory
from services.embedding_service import (
    search_similar_cases,
    store_case_with_embedding,
    update_case_embedding,
    check_embedding_health,
)
from helpers import logger


# =============================================================================
# PYDANTIC SCHEMAS - Request/Response Models
# =============================================================================


class SearchSimilarRequest(BaseModel):
    """
    Request schema for searching similar cases.
    
    This is what ElevenLabs Maintenance Agent sends via tool call.
    """
    issue_description: str
    category: Optional[str] = None
    limit: int = 5


class SimilarCaseResponse(BaseModel):
    """Response for a single similar case."""
    id: int
    issue_description: str
    solution: Optional[str]
    resolution_steps: Optional[str]
    category: str
    similarity: float


class SearchSimilarResponse(BaseModel):
    """Response schema for similar cases search."""
    query: str
    found_count: int
    cases: List[SimilarCaseResponse]


class MaintenanceCaseCreate(BaseModel):
    """
    Request schema for creating a new maintenance case.
    
    Required fields:
        - issue_description: The problem that was reported
        
    Optional fields:
        - solution: How it was resolved
        - resolution_steps: Detailed steps
        - category: mechanical, tire, engine, etc.
        - driver_id, truck_id, trailer_id: Vehicle info
    """
    issue_description: str
    solution: Optional[str] = None
    resolution_steps: Optional[str] = None
    category: str = "other"
    driver_id: Optional[str] = None
    truck_id: Optional[str] = None
    trailer_id: Optional[str] = None


class MaintenanceCaseUpdate(BaseModel):
    """Request schema for updating a case."""
    solution: Optional[str] = None
    resolution_steps: Optional[str] = None
    category: Optional[str] = None


class MaintenanceCaseResponse(BaseModel):
    """Response schema for returning case data."""
    id: int
    issue_description: str
    solution: Optional[str]
    resolution_steps: Optional[str]
    category: str
    driver_id: Optional[str]
    truck_id: Optional[str]
    trailer_id: Optional[str]
    source_ticket_id: Optional[int]
    created_by: str
    created_at: str
    resolved_at: Optional[str]
    has_embedding: bool

    class Config:
        from_attributes = True


class FromTicketRequest(BaseModel):
    """Request schema for creating case from resolved ticket."""
    ticket_id: int
    issue_description: str
    solution: str
    category: str
    resolution_steps: Optional[str] = None
    driver_id: Optional[str] = None
    truck_id: Optional[str] = None
    trailer_id: Optional[str] = None


class DeleteResponse(BaseModel):
    """Response schema for delete operation."""
    message: str
    deleted_id: int


class HealthResponse(BaseModel):
    """Response schema for health check."""
    openai_configured: bool
    embedding_model: str
    dimensions: int
    test_embedding: Optional[str]


# =============================================================================
# ROUTER SETUP
# =============================================================================


router = APIRouter(prefix="/maintenance-cases", tags=["maintenance-cases"])


# =============================================================================
# HELPER FUNCTION - Convert Model to Response
# =============================================================================


def case_to_response(case: MaintenanceCase) -> MaintenanceCaseResponse:
    """Convert a MaintenanceCase model instance to a response schema."""
    return MaintenanceCaseResponse(
        id=case.id,
        issue_description=case.issue_description,
        solution=case.solution,
        resolution_steps=case.resolution_steps,
        category=case.category,
        driver_id=case.driver_id,
        truck_id=case.truck_id,
        trailer_id=case.trailer_id,
        source_ticket_id=case.source_ticket_id,
        created_by=case.created_by,
        created_at=case.created_at.isoformat() if case.created_at else None,
        resolved_at=case.resolved_at.isoformat() if case.resolved_at else None,
        has_embedding=case.embedding is not None,
    )


# =============================================================================
# API ENDPOINTS
# =============================================================================


# -----------------------------------------------------------------------------
# SEARCH SIMILAR CASES (Main endpoint for ElevenLabs Agent)
# -----------------------------------------------------------------------------

@router.post(
    "/search-similar",
    response_model=SearchSimilarResponse,
    summary="Search for similar maintenance cases",
    description="""
    Search the knowledge base for similar past maintenance cases.
    
    **Use Case:** Called by ElevenLabs Maintenance Agent via tool call
    
    **How it works:**
    1. Generates embedding for the issue description
    2. Uses cosine similarity to find matching cases
    3. Returns top N most similar cases with solutions
    
    **Request Body:**
    - issue_description: Driver's problem description (required)
    - category: Optional filter (mechanical, tire, engine, etc.)
    - limit: How many results to return (default: 5)
    
    **Returns:** List of similar cases with solutions and similarity scores
    """,
)
async def search_similar(data: SearchSimilarRequest):
    """
    Search for similar maintenance cases using vector similarity.
    
    This is the main endpoint that ElevenLabs agent calls to find
    past solutions for similar issues.
    """
    try:
        logger.info(f"Searching similar cases for: {data.issue_description[:50]}...")
        
        # Call embedding service to search
        cases = search_similar_cases(
            issue_description=data.issue_description,
            limit=data.limit,
            category=data.category,
        )
        
        # Format response
        similar_cases = [
            SimilarCaseResponse(
                id=c["id"],
                issue_description=c["issue_description"],
                solution=c["solution"],
                resolution_steps=c["resolution_steps"],
                category=c["category"],
                similarity=c["similarity"],
            )
            for c in cases
        ]
        
        logger.info(f"Found {len(similar_cases)} similar cases")
        
        return SearchSimilarResponse(
            query=data.issue_description,
            found_count=len(similar_cases),
            cases=similar_cases,
        )
        
    except Exception as err:
        logger.error(f"Error searching similar cases: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to search similar cases: {str(err)}"
        )


# -----------------------------------------------------------------------------
# CRUD ENDPOINTS
# -----------------------------------------------------------------------------

@router.post(
    "",
    response_model=MaintenanceCaseResponse,
    summary="Create a new maintenance case",
    description="""
    Create a new maintenance case in the knowledge base with auto-generated embedding.
    
    **Use Case:** Adding historical/resolved issues to the knowledge base
    
    **Returns:** Created case with confirmation
    """,
)
async def create_case(data: MaintenanceCaseCreate):
    """Create a new case with embedding."""
    try:
        logger.info(f"Creating maintenance case for category: {data.category}")
        
        # Use embedding service to create case with embedding
        case = store_case_with_embedding(
            issue_description=data.issue_description,
            solution=data.solution,
            category=data.category,
            resolution_steps=data.resolution_steps,
            driver_id=data.driver_id,
            truck_id=data.truck_id,
            trailer_id=data.trailer_id,
        )
        
        if not case:
            raise HTTPException(
                status_code=500,
                detail="Failed to create maintenance case"
            )
        
        logger.info(f"Maintenance case created: ID={case.id}")
        return case_to_response(case)
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error creating maintenance case: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create maintenance case: {str(err)}"
        )


@router.get(
    "",
    response_model=List[MaintenanceCaseResponse],
    summary="List all maintenance cases",
    description="""
    Retrieve all maintenance cases with optional filtering and pagination.
    
    **Query Parameters:**
    - category: Filter by category
    - limit: Maximum results (default: 100)
    - offset: Skip results for pagination
    
    **Returns:** List of cases ordered by created_at (newest first)
    """,
)
async def list_cases(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """List all cases with optional filters."""
    try:
        cases = MaintenanceCase.get_all(
            category=category,
            limit=limit,
            offset=offset,
        )
        return [case_to_response(case) for case in cases]
        
    except Exception as err:
        logger.error(f"Error listing maintenance cases: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list maintenance cases: {str(err)}"
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check embedding service health",
    description="""
    Check if the embedding service is properly configured and working.
    
    **Returns:** Health status including OpenAI configuration and test result
    """,
)
async def get_health():
    """Check embedding service health."""
    try:
        health = check_embedding_health()
        return HealthResponse(
            openai_configured=health["openai_configured"],
            embedding_model=health["embedding_model"],
            dimensions=health["dimensions"],
            test_embedding=health.get("test_embedding"),
        )
    except Exception as err:
        logger.error(f"Error checking embedding health: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(err)}"
        )


@router.get(
    "/{case_id}",
    response_model=MaintenanceCaseResponse,
    summary="Get a single case by ID",
    description="""
    Retrieve detailed information about a specific case.
    
    **Returns:** Single case details
    
    **Errors:** 404 if case not found
    """,
)
async def get_case(case_id: int):
    """Get a single case by ID."""
    try:
        case = MaintenanceCase.get_by_id(case_id)
        
        if not case:
            raise HTTPException(
                status_code=404,
                detail=f"Case with ID {case_id} not found"
            )
        
        return case_to_response(case)
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error getting case {case_id}: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get case: {str(err)}"
        )


@router.put(
    "/{case_id}",
    response_model=MaintenanceCaseResponse,
    summary="Update a case",
    description="""
    Update an existing maintenance case.
    
    **Note:** If solution or issue_description changes, embedding will be regenerated.
    
    **Returns:** Updated case
    
    **Errors:** 404 if case not found
    """,
)
async def update_case(case_id: int, data: MaintenanceCaseUpdate):
    """Update an existing case."""
    try:
        # First check if case exists
        existing = MaintenanceCase.get_by_id(case_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Case with ID {case_id} not found"
            )
        
        # Update the case
        case = MaintenanceCase.update_case(
            case_id=case_id,
            solution=data.solution,
            resolution_steps=data.resolution_steps,
            category=data.category,
        )
        
        # Regenerate embedding if content changed
        if data.solution is not None:
            update_case_embedding(case_id)
            logger.info(f"Regenerated embedding for case #{case_id}")
        
        logger.info(f"Maintenance case updated: ID={case_id}")
        
        # Refetch to get updated data
        case = MaintenanceCase.get_by_id(case_id)
        return case_to_response(case)
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error updating case {case_id}: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update case: {str(err)}"
        )


@router.delete(
    "/{case_id}",
    response_model=DeleteResponse,
    summary="Delete a case",
    description="""
    Delete a maintenance case from the knowledge base.
    
    **Returns:** Success message with deleted ID
    
    **Errors:** 404 if case not found
    """,
)
async def delete_case(case_id: int):
    """Delete a case by ID."""
    try:
        deleted = MaintenanceCase.delete_case(case_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Case with ID {case_id} not found"
            )
        
        logger.info(f"Maintenance case deleted: ID={case_id}")
        
        return DeleteResponse(
            message="Case deleted successfully",
            deleted_id=case_id,
        )
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error deleting case {case_id}: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete case: {str(err)}"
        )


# -----------------------------------------------------------------------------
# TICKET CONVERSION ENDPOINT
# -----------------------------------------------------------------------------

@router.post(
    "/from-ticket",
    response_model=MaintenanceCaseResponse,
    summary="Create case from resolved ticket",
    description="""
    Convert a resolved maintenance ticket into a knowledge base case.
    
    **Use Case:** When a ticket is resolved, call this endpoint to add
    the solution to the knowledge base for future similarity searches.
    
    **Request Body:**
    - ticket_id: The resolved ticket's ID
    - issue_description: From ticket's description
    - solution: From ticket's resolution_notes
    - category: From ticket's issue_type
    
    **Returns:** Created case with embedding
    """,
)
async def create_from_ticket(data: FromTicketRequest):
    """Create a case from a resolved ticket."""
    try:
        logger.info(f"Creating case from ticket #{data.ticket_id}")
        
        # Create case with embedding
        case = store_case_with_embedding(
            issue_description=data.issue_description,
            solution=data.solution,
            category=data.category,
            resolution_steps=data.resolution_steps,
            driver_id=data.driver_id,
            truck_id=data.truck_id,
            trailer_id=data.trailer_id,
            source_ticket_id=data.ticket_id,
        )
        
        if not case:
            raise HTTPException(
                status_code=500,
                detail="Failed to create case from ticket"
            )
        
        logger.info(f"Created case #{case.id} from ticket #{data.ticket_id}")
        return case_to_response(case)
        
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error creating case from ticket: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create case from ticket: {str(err)}"
        )
