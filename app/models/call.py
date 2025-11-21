"""
Call model for storing ElevenLabs conversation metadata.

This model tracks calls initiated via ElevenLabs conversational AI for driver violation calls.
Each call is uniquely identified by both call_sid (our generated identifier) and conversation_id
(ElevenLabs identifier). Call records are created proactively before the ElevenLabs API call,
allowing complete audit trail of all call attempts.

Workflow:
1. Generate call_sid before API call (format: EL_{driverId}_{timestamp})
2. Create Call record with call_sid, driver_id, status=IN_PROGRESS, conversation_id=NULL
3. Call ElevenLabs API with call_sid
4. Update Call with conversation_id from ElevenLabs response
5. Webhooks use call_sid to look up Call, then conversation_id to save transcriptions
"""

from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Session, select, Column
from sqlalchemy import Index, UniqueConstraint, DateTime, ForeignKey, Text
from enum import Enum
from db.database import engine
from db.retry import db_retry


class CallStatus(str, Enum):
    """Call status enum for tracking call lifecycle."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Call(SQLModel, table=True):
    """
    Call model representing an ElevenLabs conversational AI call.

    Attributes:
        id: Auto-incrementing primary key
        call_sid: Our generated unique identifier (format: EL_{driverId}_{timestamp})
        conversation_id: Optional ElevenLabs conversation identifier (NULL until API responds)
        driver_id: Optional foreign key to drivers table (nullable if lookup fails)
        call_start_time: Timezone-aware UTC timestamp when call initiated
        call_end_time: Optional timezone-aware UTC timestamp when call ended
        status: Current call status (in_progress, completed, failed)
        created_at: Auto-generated timezone-aware UTC timestamp
        updated_at: Auto-generated timezone-aware UTC timestamp

    Indexes:
        - idx_calls_call_sid: Fast lookup by call_sid
        - idx_calls_call_sid_status: Efficient status queries
        - idx_calls_conversation_id: Legacy lookup by conversation_id
    """
    __tablename__ = "calls"
    __table_args__ = (
        UniqueConstraint("conversation_id", name="uq_calls_conversation_id"),
        UniqueConstraint("call_sid", name="uq_calls_call_sid"),
        Index("idx_calls_conversation_id", "conversation_id"),
        Index("idx_calls_call_sid", "call_sid"),
        Index("idx_calls_call_sid_status", "call_sid", "status"),
        {"extend_existing": True}
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    call_sid: str = Field(max_length=255, nullable=False, index=True, unique=True)
    conversation_id: Optional[str] = Field(max_length=255, nullable=True, index=True, unique=True)
    driver_id: Optional[str] = Field(default=None, nullable=True)
    call_start_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    call_end_time: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    status: CallStatus = Field(default=CallStatus.IN_PROGRESS, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))

    # Post-call webhook metadata fields
    transcript_summary: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Summary of the call conversation from ElevenLabs analysis"
    )
    call_duration_seconds: Optional[int] = Field(
        default=None,
        nullable=True,
        description="Duration of the call in seconds from metadata"
    )
    cost: Optional[float] = Field(
        default=None,
        nullable=True,
        description="Cost of the call in dollars from ElevenLabs billing"
    )
    call_successful: Optional[bool] = Field(
        default=None,
        nullable=True,
        description="Boolean flag indicating if call was successful from analysis"
    )
    analysis_data: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="JSON string of full analysis results from post-call webhook"
    )
    metadata_json: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="JSON string of full metadata from post-call webhook"
    )

    @classmethod
    def get_session(cls) -> Session:
        """Get a database session."""
        return Session(engine)

    @classmethod
    @db_retry(max_retries=3)
    def create_call_with_call_sid(
        cls,
        call_sid: str,
        driver_id: str,
        call_start_time: datetime,
        status: CallStatus = CallStatus.IN_PROGRESS
    ) -> "Call":
        """
        Create a new Call record with call_sid (before calling ElevenLabs).

        This method creates the Call record proactively, before the ElevenLabs API call.
        The conversation_id will be NULL initially and updated after ElevenLabs responds.

        Args:
            call_sid: Generated call identifier (format: EL_{driverId}_{timestamp})
            driver_id: Driver ID
            call_start_time: Timezone-aware UTC datetime when call is initiated
            status: Initial status (default: IN_PROGRESS)

        Returns:
            Created Call object with conversation_id=NULL

        Raises:
            Database exceptions if creation fails after retries
        """
        with cls.get_session() as session:
            call = cls(
                call_sid=call_sid,
                conversation_id=None,  # Will be updated after ElevenLabs responds
                driver_id=driver_id,
                call_start_time=call_start_time,
                status=status
            )
            session.add(call)
            session.commit()
            session.refresh(call)
            return call

    @classmethod
    @db_retry(max_retries=3)
    def get_by_call_sid(cls, call_sid: str) -> Optional["Call"]:
        """
        Fetch a Call by call_sid.

        Args:
            call_sid: Generated call identifier

        Returns:
            Call object if found, None otherwise
        """
        with cls.get_session() as session:
            stmt = select(cls).where(cls.call_sid == call_sid)
            return session.exec(stmt).first()

    @classmethod
    @db_retry(max_retries=3)
    def update_conversation_id(
        cls,
        call_sid: str,
        conversation_id: str
    ) -> Optional["Call"]:
        """
        Update Call record with conversation_id from ElevenLabs response.

        This method is called after a successful ElevenLabs API call to populate
        the conversation_id field that was initially NULL.

        Args:
            call_sid: Generated call identifier
            conversation_id: ElevenLabs conversation identifier

        Returns:
            Updated Call object if found, None otherwise
        """
        with cls.get_session() as session:
            call = session.exec(
                select(cls).where(cls.call_sid == call_sid)
            ).first()

            if call:
                call.conversation_id = conversation_id
                call.updated_at = datetime.now(timezone.utc)
                session.add(call)
                session.commit()
                session.refresh(call)

            return call

    @classmethod
    @db_retry(max_retries=3)
    def update_status_by_call_sid(
        cls,
        call_sid: str,
        status: CallStatus,
        call_end_time: Optional[datetime] = None
    ) -> Optional["Call"]:
        """
        Update call status by call_sid.

        Used to update Call status (e.g., to FAILED if ElevenLabs API call fails,
        or to COMPLETED when call ends).

        Args:
            call_sid: Generated call identifier
            status: New status to set
            call_end_time: Optional timezone-aware UTC datetime when call ended

        Returns:
            Updated Call object if found, None otherwise
        """
        with cls.get_session() as session:
            call = session.exec(
                select(cls).where(cls.call_sid == call_sid)
            ).first()

            if call:
                call.status = status
                if call_end_time:
                    call.call_end_time = call_end_time
                call.updated_at = datetime.now(timezone.utc)
                session.add(call)
                session.commit()
                session.refresh(call)

            return call

    # Legacy methods - kept for backward compatibility
    @classmethod
    @db_retry(max_retries=3)
    def get_by_conversation_id(cls, conversation_id: str) -> Optional["Call"]:
        """
        Fetch a Call by conversation_id (legacy method).

        Args:
            conversation_id: ElevenLabs conversation identifier

        Returns:
            Call object if found, None otherwise
        """
        with cls.get_session() as session:
            stmt = select(cls).where(cls.conversation_id == conversation_id)
            return session.exec(stmt).first()

    @classmethod
    @db_retry(max_retries=3)
    def create_call(
        cls,
        conversation_id: str,
        driver_id: Optional[str],
        call_start_time: datetime
    ) -> "Call":
        """
        Create a new Call record (legacy method).

        Note: This method is deprecated. Use create_call_with_call_sid instead.

        Args:
            conversation_id: ElevenLabs conversation identifier
            driver_id: Optional driver ID (None if lookup failed)
            call_start_time: Timezone-aware UTC datetime when call started

        Returns:
            Created Call object
        """
        with cls.get_session() as session:
            call = cls(
                conversation_id=conversation_id,
                driver_id=driver_id,
                call_start_time=call_start_time,
                status=CallStatus.IN_PROGRESS
            )
            session.add(call)
            session.commit()
            session.refresh(call)
            return call

    @classmethod
    @db_retry(max_retries=3)
    def update_status(
        cls,
        conversation_id: str,
        status: CallStatus,
        call_end_time: Optional[datetime] = None
    ) -> Optional["Call"]:
        """
        Update call status by conversation_id (legacy method).

        Note: This method is deprecated. Use update_status_by_call_sid instead.

        Args:
            conversation_id: ElevenLabs conversation identifier
            status: New status to set
            call_end_time: Optional timezone-aware UTC datetime when call ended

        Returns:
            Updated Call object if found, None otherwise
        """
        with cls.get_session() as session:
            call = session.exec(
                select(cls).where(cls.conversation_id == conversation_id)
            ).first()

            if call:
                call.status = status
                if call_end_time:
                    call.call_end_time = call_end_time
                call.updated_at = datetime.now(timezone.utc)
                session.add(call)
                session.commit()
                session.refresh(call)

            return call

    @classmethod
    @db_retry(max_retries=3)
    def update_post_call_data(
        cls,
        conversation_id: str,
        call_end_time: datetime,
        transcript_summary: Optional[str] = None,
        call_duration_seconds: Optional[int] = None,
        cost: Optional[float] = None,
        call_successful: Optional[bool] = None,
        analysis_data: Optional[str] = None,
        metadata_json: Optional[str] = None
    ) -> Optional["Call"]:
        """
        Update Call record with post-call completion metadata.

        This method is called by the post-call webhook to update the Call record
        with analysis results, metadata, and completion status from ElevenLabs.

        Args:
            conversation_id: ElevenLabs conversation identifier
            call_end_time: Timezone-aware UTC datetime when call ended
            transcript_summary: Optional text summary of conversation from analysis
            call_duration_seconds: Optional duration in seconds from metadata
            cost: Optional call cost in dollars from billing
            call_successful: Optional boolean success flag from analysis
            analysis_data: Optional JSON string of full analysis object
            metadata_json: Optional JSON string of full metadata object

        Returns:
            Updated Call object if found, None otherwise
        """
        with cls.get_session() as session:
            call = session.exec(
                select(cls).where(cls.conversation_id == conversation_id)
            ).first()

            if call:
                # Update status to COMPLETED
                call.status = CallStatus.COMPLETED
                call.call_end_time = call_end_time

                # Update post-call metadata fields
                if transcript_summary is not None:
                    call.transcript_summary = transcript_summary
                if call_duration_seconds is not None:
                    call.call_duration_seconds = call_duration_seconds
                if cost is not None:
                    call.cost = cost
                if call_successful is not None:
                    call.call_successful = call_successful
                if analysis_data is not None:
                    call.analysis_data = analysis_data
                if metadata_json is not None:
                    call.metadata_json = metadata_json

                # Update timestamp
                call.updated_at = datetime.now(timezone.utc)

                session.add(call)
                session.commit()
                session.refresh(call)

            return call
