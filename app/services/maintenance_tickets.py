"""
Maintenance Tickets API endpoints.

This module provides REST API endpoints for managing maintenance tickets
created by the ElevenLabs Maintenance Agent when drivers report vehicle issues.

Endpoints:
    POST   /maintenance-tickets           - Create new ticket
    GET    /maintenance-tickets           - List all tickets (with filters)
    GET    /maintenance-tickets/{id}      - Get single ticket
    PUT    /maintenance-tickets/{id}      - Update ticket
    DELETE /maintenance-tickets/{id}      - Delete ticket
    GET    /maintenance-tickets/driver/{driver_id} - Get tickets by driver
    GET    /maintenance-tickets/stats/open-count   - Get open tickets count
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from models.maintenance_ticket import (
    MaintenanceTicket,
    TicketSeverity,
    TicketStatus,
    IssueType,
)
from helpers import logger
from services.embedding_service import store_case_with_embedding
from models.slack import Payload, HeaderBlock, SectionBlock, MDText, DividerBlock
from config import settings


# =============================================================================
# PYDANTIC SCHEMAS - Request/Response Models
# =============================================================================


class MaintenanceTicketCreate(BaseModel):
    """
    Request schema for creating a new maintenance ticket.
    
    Required fields:
        - driver_id: Driver who reported the issue
        - issue_type: Category (mechanical, electrical, tire, etc.)
        - description: Detailed problem description
    
    Optional fields:
        - driver_name: For display purposes
        - truck_id, trailer_id: Vehicle identification
        - severity: Priority level (default: medium)
        - call_sid, conversation_id: Link to originating call
    """

    driver_id: str
    issue_type: str
    description: str
    driver_name: Optional[str] = None
    truck_id: Optional[str] = None
    trailer_id: Optional[str] = None
    severity: str = "medium"
    call_sid: Optional[str] = None
    conversation_id: Optional[str] = None


class MaintenanceTicketUpdate(BaseModel):
    """
    Request schema for updating an existing ticket.
    
    All fields are optional - only provided fields will be updated.
    """

    status: Optional[str] = None
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    description: Optional[str] = None


class MaintenanceTicketResponse(BaseModel):
    """
    Response schema for returning ticket data.
    
    This is what the API returns for each ticket.
    """

    id: int
    driver_id: str
    driver_name: Optional[str]
    truck_id: Optional[str]
    trailer_id: Optional[str]
    issue_type: str
    description: str
    severity: str
    status: str
    created_by: str
    assigned_to: Optional[str]
    call_sid: Optional[str]
    conversation_id: Optional[str]
    resolution_notes: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TicketStatsResponse(BaseModel):
    """Response schema for ticket statistics."""

    open_tickets: int


class DeleteResponse(BaseModel):
    """Response schema for delete operation."""

    message: str
    deleted_id: int


# =============================================================================
# ROUTER SETUP
# =============================================================================


router = APIRouter(prefix="/maintenance-tickets", tags=["maintenance-tickets"])


# =============================================================================
# HELPER FUNCTION - Convert Model to Response
# =============================================================================


def ticket_to_response(ticket: MaintenanceTicket) -> MaintenanceTicketResponse:
    """
    Convert a MaintenanceTicket model instance to a response schema.
    
    This helper ensures consistent response formatting across all endpoints.
    """
    return MaintenanceTicketResponse(
        id=ticket.id,
        driver_id=ticket.driver_id,
        driver_name=ticket.driver_name,
        truck_id=ticket.truck_id,
        trailer_id=ticket.trailer_id,
        issue_type=ticket.issue_type,
        description=ticket.description,
        severity=ticket.severity,
        status=ticket.status,
        created_by=ticket.created_by,
        assigned_to=ticket.assigned_to,
        call_sid=ticket.call_sid,
        conversation_id=ticket.conversation_id,
        resolution_notes=ticket.resolution_notes,
        created_at=ticket.created_at.isoformat(),
        updated_at=ticket.updated_at.isoformat(),
    )


# =============================================================================
# HELPER FUNCTIONS - Slack & Case Conversion
# =============================================================================


def send_ticket_slack_notification(ticket: MaintenanceTicket, action: str = "created"):
    """
    Send Slack notification for ticket events.
    
    Args:
        ticket: The maintenance ticket
        action: Event type (created, resolved, updated)
    """
    try:
        # Build message blocks
        emoji = "🎫" if action == "created" else "✅" if action == "resolved" else "📝"
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠", 
            "medium": "🟡",
            "low": "🟢"
        }.get(ticket.severity, "⚪")
        
        blocks = [
            HeaderBlock(text=f"{emoji} Maintenance Ticket {action.title()}"),
            SectionBlock(text=MDText(
                f"*Ticket #{ticket.id}* | {severity_emoji} {ticket.severity.upper()}\n"
                f"*Driver:* {ticket.driver_name or ticket.driver_id}\n"
                f"*Issue Type:* {ticket.issue_type}\n"
                f"*Description:* {ticket.description[:200]}..."
            )),
            DividerBlock(),
        ]
        
        if action == "resolved" and ticket.resolution_notes:
            blocks.insert(2, SectionBlock(text=MDText(
                f"*Resolution:* {ticket.resolution_notes[:300]}"
            )))
        
        # Send to Slack
        payload = Payload(
            channel=settings.ALERTS_APPROACH1_SLACK_CHANNEL,
            blocks=blocks
        )
        payload.post()
        
        logger.info(f"Slack notification sent for ticket #{ticket.id} ({action})")
        
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {str(e)}")


def convert_ticket_to_case(ticket: MaintenanceTicket):
    """
    Convert a resolved ticket to a maintenance case (knowledge base).
    
    This creates a new case with embedding for future similarity searches.
    
    Args:
        ticket: The resolved maintenance ticket
    """
    try:
        if not ticket.resolution_notes:
            logger.warning(f"Ticket #{ticket.id} has no resolution notes, skipping case creation")
            return
        
        # Create case with embedding
        case = store_case_with_embedding(
            issue_description=ticket.description,
            solution=ticket.resolution_notes,
            category=ticket.issue_type,
            driver_id=ticket.driver_id,
            truck_id=ticket.truck_id,
            trailer_id=ticket.trailer_id,
            source_ticket_id=ticket.id,
        )
        
        if case:
            logger.info(f"Created case #{case.id} from resolved ticket #{ticket.id}")
        else:
            logger.error(f"Failed to create case from ticket #{ticket.id}")
            
    except Exception as e:
        logger.error(f"Error converting ticket to case: {str(e)}")


# =============================================================================
# API ENDPOINTS
# =============================================================================


@router.post(
    "",
    response_model=MaintenanceTicketResponse,
    summary="Create a new maintenance ticket",
    description="""
    Create a new maintenance ticket when a driver reports an issue.
    
    **Use Case:** Called by ElevenLabs Maintenance Agent via webhook
    
    **Required Fields:**
    - driver_id: Driver identifier
    - issue_type: mechanical, electrical, tire, brake, reefer, engine, other
    - description: Detailed problem description
    
    **Returns:** Created ticket with generated ID
    """,
)
async def create_ticket(data: MaintenanceTicketCreate, background_tasks: BackgroundTasks):
    """
    Create a new maintenance ticket.
    
    Flow:
    1. Pydantic validates input data
    2. Call model's create_ticket method
    3. Send Slack notification (background)
    4. Return created ticket in response format
    """
    try:
        # Log the incoming request
        logger.info(f"Creating maintenance ticket for driver: {data.driver_id}")

        # Create ticket using model method
        ticket = MaintenanceTicket.create_ticket(
            driver_id=data.driver_id,
            issue_type=data.issue_type,
            description=data.description,
            driver_name=data.driver_name,
            truck_id=data.truck_id,
            trailer_id=data.trailer_id,
            severity=data.severity,
            call_sid=data.call_sid,
            conversation_id=data.conversation_id,
        )

        logger.info(f"Maintenance ticket created: ID={ticket.id}")
        
        # Send Slack notification in background
        background_tasks.add_task(send_ticket_slack_notification, ticket, "created")

        # Return response
        return ticket_to_response(ticket)

    except Exception as err:
        logger.error(f"Error creating maintenance ticket: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create maintenance ticket: {str(err)}"
        )


@router.get(
    "",
    response_model=List[MaintenanceTicketResponse],
    summary="List all maintenance tickets",
    description="""
    Retrieve all maintenance tickets with optional filtering and pagination.
    
    **Query Parameters:**
    - status: Filter by status (open, in_progress, resolved, closed)
    - severity: Filter by severity (low, medium, high, critical)
    - driver_id: Filter by driver
    - truck_id: Filter by truck
    - limit: Maximum results (default: 100, max: 500)
    - offset: Skip results for pagination
    
    **Returns:** List of tickets ordered by created_at (newest first)
    """,
)
async def list_tickets(
    status: Optional[str] = Query(
        None, description="Filter by status: open, in_progress, resolved, closed"
    ),
    severity: Optional[str] = Query(
        None, description="Filter by severity: low, medium, high, critical"
    ),
    driver_id: Optional[str] = Query(None, description="Filter by driver ID"),
    truck_id: Optional[str] = Query(None, description="Filter by truck ID"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
):
    """
    List all tickets with optional filters.
    
    Flow:
    1. Extract query parameters
    2. Call model's get_all method with filters
    3. Convert each ticket to response format
    4. Return list
    """
    try:
        # Get tickets from database
        tickets = MaintenanceTicket.get_all(
            status=status,
            severity=severity,
            driver_id=driver_id,
            truck_id=truck_id,
            limit=limit,
            offset=offset,
        )

        # Convert to response format
        return [ticket_to_response(ticket) for ticket in tickets]

    except Exception as err:
        logger.error(f"Error listing maintenance tickets: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to list maintenance tickets: {str(err)}"
        )


@router.get(
    "/stats/open-count",
    response_model=TicketStatsResponse,
    summary="Get count of open tickets",
    description="""
    Get the total number of tickets with status=open.
    
    **Use Case:** Dashboard statistics
    
    **Returns:** { "open_tickets": 42 }
    """,
)
async def get_open_tickets_count():
    """
    Get count of open tickets for dashboard stats.
    
    Flow:
    1. Call model's get_open_tickets_count method
    2. Return count in response format
    """
    try:
        count = MaintenanceTicket.get_open_tickets_count()
        return TicketStatsResponse(open_tickets=count)

    except Exception as err:
        logger.error(f"Error getting open tickets count: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get open tickets count: {str(err)}"
        )


@router.get(
    "/driver/{driver_id}",
    response_model=List[MaintenanceTicketResponse],
    summary="Get tickets by driver",
    description="""
    Get all maintenance tickets for a specific driver.
    
    **URL Parameters:**
    - driver_id: The driver's identifier
    
    **Returns:** List of tickets for this driver (max 50)
    """,
)
async def get_tickets_by_driver(driver_id: str):
    """
    Get all tickets for a specific driver.
    
    Flow:
    1. Call model's get_tickets_by_driver method
    2. Convert to response format
    3. Return list
    """
    try:
        tickets = MaintenanceTicket.get_tickets_by_driver(driver_id)
        return [ticket_to_response(ticket) for ticket in tickets]

    except Exception as err:
        logger.error(
            f"Error getting tickets for driver {driver_id}: {str(err)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get tickets for driver: {str(err)}"
        )


@router.get(
    "/{ticket_id}",
    response_model=MaintenanceTicketResponse,
    summary="Get a single ticket by ID",
    description="""
    Retrieve detailed information about a specific ticket.
    
    **URL Parameters:**
    - ticket_id: The ticket's unique ID
    
    **Returns:** Single ticket details
    
    **Errors:** 404 if ticket not found
    """,
)
async def get_ticket(ticket_id: int):
    """
    Get a single ticket by ID.
    
    Flow:
    1. Call model's get_by_id method
    2. If None, raise 404 error
    3. Convert to response format and return
    """
    try:
        ticket = MaintenanceTicket.get_by_id(ticket_id)

        if not ticket:
            raise HTTPException(
                status_code=404, detail=f"Ticket with ID {ticket_id} not found"
            )

        return ticket_to_response(ticket)

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error getting ticket {ticket_id}: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get ticket: {str(err)}"
        )


@router.put(
    "/{ticket_id}",
    response_model=MaintenanceTicketResponse,
    summary="Update a ticket",
    description="""
    Update an existing maintenance ticket.
    
    **URL Parameters:**
    - ticket_id: The ticket's unique ID
    
    **Body Fields (all optional):**
    - status: New status (open, in_progress, resolved, closed)
    - severity: New severity (low, medium, high, critical)
    - assigned_to: Assign to a technician
    - resolution_notes: Add notes about the fix
    - description: Update the problem description
    
    **Returns:** Updated ticket
    
    **Errors:** 404 if ticket not found
    """,
)
async def update_ticket(ticket_id: int, data: MaintenanceTicketUpdate, background_tasks: BackgroundTasks):
    """
    Update an existing ticket.
    
    Flow:
    1. First check if ticket exists
    2. If not, raise 404
    3. Call model's update_ticket method
    4. If status changed to "resolved":
       - Create maintenance case (knowledge base)
       - Send Slack notification
    5. Return updated ticket
    """
    try:
        # First check if ticket exists
        existing = MaintenanceTicket.get_by_id(ticket_id)
        if not existing:
            raise HTTPException(
                status_code=404, detail=f"Ticket with ID {ticket_id} not found"
            )
        
        # Check if this is a resolution (status changing TO resolved)
        is_being_resolved = (
            data.status == "resolved" and 
            existing.status != "resolved"
        )

        # Update the ticket
        ticket = MaintenanceTicket.update_ticket(
            ticket_id=ticket_id,
            status=data.status,
            severity=data.severity,
            assigned_to=data.assigned_to,
            resolution_notes=data.resolution_notes,
            description=data.description,
        )

        logger.info(f"Maintenance ticket updated: ID={ticket_id}")
        
        # If ticket was just resolved, create case and notify
        if is_being_resolved:
            logger.info(f"Ticket #{ticket_id} resolved - creating case & sending notification")
            
            # Run in background to not block the response
            background_tasks.add_task(convert_ticket_to_case, ticket)
            background_tasks.add_task(send_ticket_slack_notification, ticket, "resolved")

        return ticket_to_response(ticket)

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error updating ticket {ticket_id}: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update ticket: {str(err)}"
        )


@router.delete(
    "/{ticket_id}",
    response_model=DeleteResponse,
    summary="Delete a ticket",
    description="""
    Delete a maintenance ticket.
    
    **URL Parameters:**
    - ticket_id: The ticket's unique ID
    
    **Returns:** Success message with deleted ID
    
    **Errors:** 404 if ticket not found
    """,
)
async def delete_ticket(ticket_id: int):
    """
    Delete a ticket by ID.
    
    Flow:
    1. Call model's delete_ticket method
    2. If False (not found), raise 404
    3. Return success message
    """
    try:
        deleted = MaintenanceTicket.delete_ticket(ticket_id)

        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"Ticket with ID {ticket_id} not found"
            )

        logger.info(f"Maintenance ticket deleted: ID={ticket_id}")

        return DeleteResponse(
            message="Ticket deleted successfully",
            deleted_id=ticket_id,
        )

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error deleting ticket {ticket_id}: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete ticket: {str(err)}"
        )
