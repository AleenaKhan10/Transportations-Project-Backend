
from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Session, select, Column
from sqlalchemy import Index, DateTime, Text
from enum import Enum
from pydantic import BaseModel
from db.database import engine
from db.retry import db_retry


class TicketSeverity(str, Enum):
    """Ticket severity levels for prioritization."""

    LOW = "low"  # Minor issue, can wait
    MEDIUM = "medium"  # Normal priority
    HIGH = "high"  # Needs attention soon
    CRITICAL = "critical"  # Safety issue, immediate attention


class TicketStatus(str, Enum):
    """Ticket lifecycle status."""

    OPEN = "open"  # New ticket, unassigned
    IN_PROGRESS = "in_progress"  # Someone is working on it
    RESOLVED = "resolved"  # Issue fixed
    CLOSED = "closed"  # Ticket closed (resolved or not applicable)


class IssueType(str, Enum):
    """Type of maintenance issue."""

    MECHANICAL = "mechanical"  # Engine, transmission, general mechanical
    ELECTRICAL = "electrical"  # Wiring, lights, electrical systems
    TIRE = "tire"  # Flat tire, tire wear, tire pressure
    BRAKE = "brake"  # Brake pads, brake lines, ABS
    REEFER = "reefer"  # Refrigeration unit (cold trucks)
    ENGINE = "engine"  # Engine-specific issues
    TRANSMISSION = "transmission"  # Transmission issues
    COOLANT = "coolant"  # Overheating, coolant leaks
    OIL = "oil"  # Oil leaks, oil pressure
    OTHER = "other"  # Anything else


# =============================================================================
# DATABASE MODEL - MaintenanceTicket
# =============================================================================


class MaintenanceTicket(SQLModel, table=True):
    """
    MaintenanceTicket model representing a driver's maintenance issue.

    Attributes:
        id: Auto-incrementing primary key
        driver_id: Driver who reported the issue (required)
        driver_name: Driver's name for display
        truck_id: Truck/vehicle ID if known
        trailer_id: Trailer ID if applicable
        issue_type: Category of the issue (mechanical, electrical, etc.)
        description: Detailed description of the problem
        severity: Priority level (low, medium, high, critical)
        status: Current status (open, in_progress, resolved, closed)
        created_by: Who created the ticket (usually "maintenance_agent")
        assigned_to: Maintenance staff assigned to this ticket
        call_sid: Link to the Call record that created this ticket
        conversation_id: ElevenLabs conversation ID
        resolution_notes: Notes about how the issue was resolved
        created_at: When the ticket was created
        updated_at: When the ticket was last updated

    Indexes:
        - idx_maintenance_tickets_driver_id: Fast lookup by driver
        - idx_maintenance_tickets_status: Filter by status
        - idx_maintenance_tickets_severity: Filter by severity
        - idx_maintenance_tickets_truck_id: Lookup by truck
    """

    __tablename__ = "maintenance_tickets"
    __table_args__ = (
        Index("idx_maintenance_tickets_driver_id", "driver_id"),
        Index("idx_maintenance_tickets_status", "status"),
        Index("idx_maintenance_tickets_severity", "severity"),
        Index("idx_maintenance_tickets_truck_id", "truck_id"),
        Index("idx_maintenance_tickets_call_sid", "call_sid"),
        {"schema": "dev", "extend_existing": True},
    )

    # Primary Key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Driver & Vehicle Information
    driver_id: str = Field(max_length=50, nullable=False, index=True)
    driver_name: Optional[str] = Field(
        default=None, max_length=255, nullable=True, description="Driver's full name"
    )
    truck_id: Optional[str] = Field(
        default=None, max_length=50, nullable=True, index=True
    )
    trailer_id: Optional[str] = Field(default=None, max_length=50, nullable=True)

    # Issue Details
    issue_type: str = Field(
        max_length=50, nullable=False, description="Type of maintenance issue"
    )
    description: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Detailed description of the issue",
    )
    severity: str = Field(
        default=TicketSeverity.MEDIUM.value,
        max_length=20,
        nullable=False,
        description="Priority level: low, medium, high, critical",
    )
    status: str = Field(
        default=TicketStatus.OPEN.value,
        max_length=20,
        nullable=False,
        description="Ticket status: open, in_progress, resolved, closed",
    )

    # Assignment & Source
    created_by: str = Field(
        default="maintenance_agent",
        max_length=50,
        nullable=False,
        description="Who created this ticket",
    )
    assigned_to: Optional[str] = Field(
        default=None,
        max_length=50,
        nullable=True,
        description="Maintenance staff assigned to this ticket",
    )

    # Call Linking (for tracking source)
    call_sid: Optional[str] = Field(
        default=None,
        max_length=100,
        nullable=True,
        description="Link to the Call record (EL_{driverId}_{timestamp})",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        max_length=100,
        nullable=True,
        description="ElevenLabs conversation ID",
    )

    # Resolution
    resolution_notes: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Notes about how the issue was resolved",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # =========================================================================
    # CLASS METHODS - Database Operations
    # =========================================================================

    @classmethod
    def get_session(cls) -> Session:
        """Get a database session."""
        return Session(engine)

    @classmethod
    @db_retry(max_retries=3)
    def create_ticket(
        cls,
        driver_id: str,
        issue_type: str,
        description: str,
        driver_name: Optional[str] = None,
        truck_id: Optional[str] = None,
        trailer_id: Optional[str] = None,
        severity: str = "medium",
        call_sid: Optional[str] = None,
        conversation_id: Optional[str] = None,
        created_by: str = "maintenance_agent",
    ) -> "MaintenanceTicket":
        """
        Create a new maintenance ticket.

        Args:
            driver_id: Driver ID (required)
            issue_type: Type of issue (mechanical, electrical, etc.)
            description: Detailed description of the problem
            driver_name: Optional driver name for display
            truck_id: Optional truck ID
            trailer_id: Optional trailer ID
            severity: Priority level (default: medium)
            call_sid: Optional link to Call record
            conversation_id: Optional ElevenLabs conversation ID
            created_by: Who created the ticket (default: maintenance_agent)

        Returns:
            Created MaintenanceTicket object

        Raises:
            Database exceptions if creation fails after retries
        """
        with cls.get_session() as session:
            ticket = cls(
                driver_id=driver_id,
                driver_name=driver_name,
                truck_id=truck_id,
                trailer_id=trailer_id,
                issue_type=issue_type,
                description=description,
                severity=severity,
                status=TicketStatus.OPEN.value,
                created_by=created_by,
                call_sid=call_sid,
                conversation_id=conversation_id,
            )
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            return ticket

    @classmethod
    @db_retry(max_retries=3)
    def get_by_id(cls, ticket_id: int) -> Optional["MaintenanceTicket"]:
        """
        Fetch a ticket by its ID.

        Args:
            ticket_id: The ticket ID

        Returns:
            MaintenanceTicket object if found, None otherwise
        """
        with cls.get_session() as session:
            stmt = select(cls).where(cls.id == ticket_id)
            return session.exec(stmt).first()

    @classmethod
    @db_retry(max_retries=3)
    def get_all(
        cls,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        driver_id: Optional[str] = None,
        truck_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List["MaintenanceTicket"]:
        """
        Get all tickets with optional filters and pagination.

        Args:
            status: Filter by status (open, in_progress, resolved, closed)
            severity: Filter by severity (low, medium, high, critical)
            driver_id: Filter by driver ID
            truck_id: Filter by truck ID
            limit: Maximum number of results (default: 100)
            offset: Number of results to skip (default: 0)

        Returns:
            List of MaintenanceTicket objects
        """
        with cls.get_session() as session:
            stmt = select(cls).order_by(cls.created_at.desc())

            # Apply filters
            if status:
                stmt = stmt.where(cls.status == status)
            if severity:
                stmt = stmt.where(cls.severity == severity)
            if driver_id:
                stmt = stmt.where(cls.driver_id == driver_id)
            if truck_id:
                stmt = stmt.where(cls.truck_id == truck_id)

            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)

            results = session.exec(stmt).all()
            return list(results)

    @classmethod
    @db_retry(max_retries=3)
    def update_ticket(
        cls,
        ticket_id: int,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        assigned_to: Optional[str] = None,
        resolution_notes: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional["MaintenanceTicket"]:
        """
        Update an existing ticket.

        Args:
            ticket_id: The ticket ID to update
            status: New status (optional)
            severity: New severity (optional)
            assigned_to: Assign to someone (optional)
            resolution_notes: Add resolution notes (optional)
            description: Update description (optional)

        Returns:
            Updated MaintenanceTicket if found, None otherwise
        """
        with cls.get_session() as session:
            ticket = session.exec(select(cls).where(cls.id == ticket_id)).first()

            if ticket:
                if status is not None:
                    ticket.status = status
                if severity is not None:
                    ticket.severity = severity
                if assigned_to is not None:
                    ticket.assigned_to = assigned_to
                if resolution_notes is not None:
                    ticket.resolution_notes = resolution_notes
                if description is not None:
                    ticket.description = description

                ticket.updated_at = datetime.now(timezone.utc)
                session.add(ticket)
                session.commit()
                session.refresh(ticket)

            return ticket

    @classmethod
    @db_retry(max_retries=3)
    def delete_ticket(cls, ticket_id: int) -> bool:
        """
        Delete a ticket by ID.

        Args:
            ticket_id: The ticket ID to delete

        Returns:
            True if deleted, False if not found
        """
        with cls.get_session() as session:
            ticket = session.exec(select(cls).where(cls.id == ticket_id)).first()

            if ticket:
                session.delete(ticket)
                session.commit()
                return True

            return False

    @classmethod
    @db_retry(max_retries=3)
    def get_by_call_sid(cls, call_sid: str) -> Optional["MaintenanceTicket"]:
        """
        Fetch a ticket by the originating call_sid.

        Args:
            call_sid: The Call record's call_sid

        Returns:
            MaintenanceTicket object if found, None otherwise
        """
        with cls.get_session() as session:
            stmt = select(cls).where(cls.call_sid == call_sid)
            return session.exec(stmt).first()

    @classmethod
    @db_retry(max_retries=3)
    def get_open_tickets_count(cls) -> int:
        """
        Get count of open tickets (for dashboard stats).

        Returns:
            Number of tickets with status=OPEN
        """
        with cls.get_session() as session:
            stmt = select(cls).where(cls.status == TicketStatus.OPEN.value)
            results = session.exec(stmt).all()
            return len(results)

    @classmethod
    @db_retry(max_retries=3)
    def get_tickets_by_driver(
        cls, driver_id: str, limit: int = 50
    ) -> List["MaintenanceTicket"]:
        """
        Get all tickets for a specific driver.

        Args:
            driver_id: The driver's ID
            limit: Maximum number of results (default: 50)

        Returns:
            List of MaintenanceTicket objects for this driver
        """
        with cls.get_session() as session:
            stmt = (
                select(cls)
                .where(cls.driver_id == driver_id)
                .order_by(cls.created_at.desc())
                .limit(limit)
            )
            results = session.exec(stmt).all()
            return list(results)


