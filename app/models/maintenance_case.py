"""
MaintenanceCase model for storing historical maintenance issues with vector embeddings.

This table is used as a knowledge base for the Maintenance Agent to search
for similar past cases and provide solutions to drivers.

Schema: dev (Supabase)
Table: maintenance_cases
"""

from typing import Optional, List, Any
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Session, select, Column
from sqlalchemy import Index, DateTime, Text
from pgvector.sqlalchemy import Vector
from enum import Enum
from db.database import engine
from db.retry import db_retry


# Embedding dimensions for text-embedding-3-small model
EMBEDDING_DIMENSIONS = 1536


class CaseCategory(str, Enum):
    """Categories for maintenance cases (matches IssueType in tickets)."""

    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    TIRE = "tire"
    BRAKE = "brake"
    REEFER = "reefer"
    ENGINE = "engine"
    TRANSMISSION = "transmission"
    COOLANT = "coolant"
    OIL = "oil"
    OTHER = "other"


# =============================================================================
# DATABASE MODEL - MaintenanceCase
# =============================================================================


class MaintenanceCase(SQLModel, table=True):
    """
    MaintenanceCase model for storing resolved maintenance issues as a knowledge base.

    This table stores HISTORICAL/RESOLVED cases that can be searched using
    vector similarity to help the Maintenance Agent find relevant past solutions.

    Attributes:
        id: Auto-incrementing primary key
        driver_id: Driver who had this issue (optional - for reference)
        truck_id: Truck/vehicle ID if known
        trailer_id: Trailer ID if applicable
        issue_description: Original problem description
        solution: How the issue was resolved
        resolution_steps: Detailed steps taken to fix
        category: Type of issue (mechanical, electrical, etc.)
        source_ticket_id: Link to original MaintenanceTicket if converted
        created_by: Who created this case (maintenance_agent, admin, etc.)
        created_at: When the case was created
        resolved_at: When the issue was resolved

    Note:
        The `embedding` column (VECTOR(1536)) is managed separately via SQL
        since SQLModel/SQLAlchemy doesn't natively support pgvector types.
        Use Supabase RPC functions for vector searches.

    Indexes:
        - idx_maintenance_cases_category: Filter by issue category
        - idx_maintenance_cases_created: Sort by creation date
    """

    __tablename__ = "maintenance_cases"
    __table_args__ = (
        Index("idx_maintenance_cases_category", "category"),
        Index("idx_maintenance_cases_created", "created_at"),
        Index("idx_maintenance_cases_source_ticket", "source_ticket_id"),
        {"schema": "dev", "extend_existing": True},
    )

    # Primary Key
    id: Optional[int] = Field(default=None, primary_key=True)

    # Vehicle/Driver Reference (optional - for tracking)
    driver_id: Optional[str] = Field(
        default=None, max_length=50, nullable=True, description="Driver who had this issue"
    )
    truck_id: Optional[str] = Field(
        default=None, max_length=50, nullable=True, description="Truck ID"
    )
    trailer_id: Optional[str] = Field(
        default=None, max_length=50, nullable=True, description="Trailer ID"
    )

    # Issue Details
    issue_description: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Original problem description from driver",
    )
    solution: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="How the issue was resolved",
    )
    resolution_steps: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Detailed step-by-step resolution",
    )
    category: str = Field(
        default=CaseCategory.OTHER.value,
        max_length=50,
        nullable=False,
        description="Issue category: mechanical, electrical, tire, etc.",
    )

    # Vector Embedding for similarity search
    # This column stores the 1536-dimensional embedding from OpenAI text-embedding-3-small
    embedding: Optional[Any] = Field(
        default=None,
        sa_column=Column(Vector(EMBEDDING_DIMENSIONS), nullable=True),
        description="Vector embedding for similarity search",
    )

    # Source Tracking
    source_ticket_id: Optional[int] = Field(
        default=None,
        nullable=True,
        description="Link to original MaintenanceTicket if converted from ticket",
    )
    created_by: str = Field(
        default="maintenance_agent",
        max_length=50,
        nullable=False,
        description="Who created this case",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    resolved_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="When the issue was actually resolved",
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
    def create_case(
        cls,
        issue_description: str,
        category: str = "other",
        solution: Optional[str] = None,
        resolution_steps: Optional[str] = None,
        driver_id: Optional[str] = None,
        truck_id: Optional[str] = None,
        trailer_id: Optional[str] = None,
        source_ticket_id: Optional[int] = None,
        created_by: str = "maintenance_agent",
        resolved_at: Optional[datetime] = None,
    ) -> "MaintenanceCase":
        """
        Create a new maintenance case.

        Args:
            issue_description: Original problem description (required)
            category: Issue category (default: other)
            solution: How the issue was resolved
            resolution_steps: Detailed resolution steps
            driver_id: Optional driver ID
            truck_id: Optional truck ID
            trailer_id: Optional trailer ID
            source_ticket_id: Link to original ticket if converted
            created_by: Who created this case
            resolved_at: When the issue was resolved

        Returns:
            Created MaintenanceCase object
        """
        with cls.get_session() as session:
            case = cls(
                issue_description=issue_description,
                category=category,
                solution=solution,
                resolution_steps=resolution_steps,
                driver_id=driver_id,
                truck_id=truck_id,
                trailer_id=trailer_id,
                source_ticket_id=source_ticket_id,
                created_by=created_by,
                resolved_at=resolved_at or datetime.now(timezone.utc),
            )
            session.add(case)
            session.commit()
            session.refresh(case)
            return case

    @classmethod
    @db_retry(max_retries=3)
    def get_by_id(cls, case_id: int) -> Optional["MaintenanceCase"]:
        """
        Fetch a case by its ID.

        Args:
            case_id: The case ID

        Returns:
            MaintenanceCase object if found, None otherwise
        """
        with cls.get_session() as session:
            stmt = select(cls).where(cls.id == case_id)
            return session.exec(stmt).first()

    @classmethod
    @db_retry(max_retries=3)
    def get_all(
        cls,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List["MaintenanceCase"]:
        """
        Get all cases with optional filters and pagination.

        Args:
            category: Filter by category
            limit: Maximum number of results (default: 100)
            offset: Number of results to skip (default: 0)

        Returns:
            List of MaintenanceCase objects
        """
        with cls.get_session() as session:
            stmt = select(cls).order_by(cls.created_at.desc())

            if category:
                stmt = stmt.where(cls.category == category)

            stmt = stmt.offset(offset).limit(limit)
            results = session.exec(stmt).all()
            return list(results)

    @classmethod
    @db_retry(max_retries=3)
    def get_by_category(
        cls, category: str, limit: int = 50
    ) -> List["MaintenanceCase"]:
        """
        Get all cases for a specific category.

        Args:
            category: The issue category
            limit: Maximum number of results (default: 50)

        Returns:
            List of MaintenanceCase objects for this category
        """
        with cls.get_session() as session:
            stmt = (
                select(cls)
                .where(cls.category == category)
                .order_by(cls.created_at.desc())
                .limit(limit)
            )
            results = session.exec(stmt).all()
            return list(results)

    @classmethod
    @db_retry(max_retries=3)
    def update_case(
        cls,
        case_id: int,
        solution: Optional[str] = None,
        resolution_steps: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Optional["MaintenanceCase"]:
        """
        Update an existing case.

        Args:
            case_id: The case ID to update
            solution: New solution (optional)
            resolution_steps: New resolution steps (optional)
            category: New category (optional)

        Returns:
            Updated MaintenanceCase if found, None otherwise
        """
        with cls.get_session() as session:
            case = session.exec(select(cls).where(cls.id == case_id)).first()

            if case:
                if solution is not None:
                    case.solution = solution
                if resolution_steps is not None:
                    case.resolution_steps = resolution_steps
                if category is not None:
                    case.category = category

                session.add(case)
                session.commit()
                session.refresh(case)

            return case

    @classmethod
    @db_retry(max_retries=3)
    def delete_case(cls, case_id: int) -> bool:
        """
        Delete a case by ID.

        Args:
            case_id: The case ID to delete

        Returns:
            True if deleted, False if not found
        """
        with cls.get_session() as session:
            case = session.exec(select(cls).where(cls.id == case_id)).first()

            if case:
                session.delete(case)
                session.commit()
                return True

            return False

    @classmethod
    @db_retry(max_retries=3)
    def create_from_ticket(
        cls,
        ticket_id: int,
        issue_description: str,
        solution: str,
        category: str,
        resolution_steps: Optional[str] = None,
        driver_id: Optional[str] = None,
        truck_id: Optional[str] = None,
        trailer_id: Optional[str] = None,
    ) -> "MaintenanceCase":
        """
        Create a case from a resolved MaintenanceTicket.

        This is called when a ticket is resolved to add it to the knowledge base.

        Args:
            ticket_id: The source ticket ID
            issue_description: Problem description from ticket
            solution: Resolution notes from ticket
            category: Issue type from ticket
            resolution_steps: Optional detailed steps
            driver_id: Driver ID from ticket
            truck_id: Truck ID from ticket
            trailer_id: Trailer ID from ticket

        Returns:
            Created MaintenanceCase object
        """
        return cls.create_case(
            issue_description=issue_description,
            solution=solution,
            category=category,
            resolution_steps=resolution_steps,
            driver_id=driver_id,
            truck_id=truck_id,
            trailer_id=trailer_id,
            source_ticket_id=ticket_id,
            created_by="ticket_resolution",
            resolved_at=datetime.now(timezone.utc),
        )

    @classmethod
    @db_retry(max_retries=3)
    def get_count(cls) -> int:
        """
        Get total count of maintenance cases.

        Returns:
            Number of cases in the knowledge base
        """
        with cls.get_session() as session:
            stmt = select(cls)
            results = session.exec(stmt).all()
            return len(results)
