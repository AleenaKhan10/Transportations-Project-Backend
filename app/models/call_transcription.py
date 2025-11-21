"""
CallTranscription model for storing real-time call dialogue transcriptions.

This model stores individual dialogue turns from ElevenLabs conversational AI calls.
Each transcription is linked to a Call via conversation_id and includes speaker attribution,
message content, timestamp, and sequence number for ordering.
"""

from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Session, select, func, Column
from sqlalchemy import Index, Text, DateTime
from enum import Enum
from db.database import engine
from db.retry import db_retry


class SpeakerType(str, Enum):
    """Speaker type enum for dialogue attribution."""
    AGENT = "agent"
    DRIVER = "driver"


class CallTranscription(SQLModel, table=True):
    """
    CallTranscription model representing a single dialogue turn in a call.

    Attributes:
        id: Auto-incrementing primary key
        conversation_id: Foreign key to Call.conversation_id (indexed)
        speaker_type: Speaker attribution (agent or driver)
        message_text: The actual dialogue content
        timestamp: Timezone-aware UTC timestamp when dialogue occurred
        sequence_number: Auto-generated sequence number for ordering (indexed)
        created_at: Auto-generated timezone-aware UTC timestamp
    """
    __tablename__ = "call_transcriptions"
    __table_args__ = (
        Index("idx_call_transcriptions_conversation_id", "conversation_id"),
        Index("idx_call_transcriptions_sequence_number", "sequence_number"),
        Index("idx_call_transcriptions_conversation_seq", "conversation_id", "sequence_number"),
        {"extend_existing": True}
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: str = Field(max_length=255, nullable=False, index=True, foreign_key="calls.conversation_id")
    speaker_type: SpeakerType = Field(nullable=False)
    message_text: str = Field(sa_column=Column(Text, nullable=False))  # Use Text type for long messages
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))  # Timezone-aware UTC
    sequence_number: int = Field(nullable=False, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))

    @classmethod
    def get_session(cls) -> Session:
        """Get a database session."""
        return Session(engine)

    @classmethod
    @db_retry(max_retries=3)
    def get_count_by_conversation_id(cls, conversation_id: str) -> int:
        """
        Get count of transcriptions for a given conversation.

        Args:
            conversation_id: ElevenLabs conversation identifier

        Returns:
            Number of transcriptions for this conversation
        """
        with cls.get_session() as session:
            stmt = select(func.count(cls.id)).where(cls.conversation_id == conversation_id)
            return session.exec(stmt).one()

    @classmethod
    @db_retry(max_retries=3)
    def create_transcription(
        cls,
        conversation_id: str,
        speaker_type: SpeakerType,
        message_text: str,
        timestamp: datetime,
        sequence_number: int
    ) -> "CallTranscription":
        """
        Create a new CallTranscription record.

        Args:
            conversation_id: ElevenLabs conversation identifier
            speaker_type: Speaker attribution (agent or driver)
            message_text: The actual dialogue content
            timestamp: Timezone-aware UTC datetime when dialogue occurred
            sequence_number: Sequence number for ordering

        Returns:
            Created CallTranscription object
        """
        with cls.get_session() as session:
            transcription = cls(
                conversation_id=conversation_id,
                speaker_type=speaker_type,
                message_text=message_text,
                timestamp=timestamp,
                sequence_number=sequence_number
            )
            session.add(transcription)
            session.commit()
            session.refresh(transcription)
            return transcription

    @classmethod
    @db_retry(max_retries=3)
    def get_by_conversation_id(
        cls,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List["CallTranscription"]:
        """
        Get all transcriptions for a conversation, ordered by sequence_number.

        Args:
            conversation_id: ElevenLabs conversation identifier
            limit: Optional limit on number of results

        Returns:
            List of CallTranscription objects ordered by sequence_number
        """
        with cls.get_session() as session:
            stmt = (
                select(cls)
                .where(cls.conversation_id == conversation_id)
                .order_by(cls.sequence_number.asc())
            )
            if limit:
                stmt = stmt.limit(limit)
            return session.exec(stmt).all()

    @classmethod
    @db_retry(max_retries=3)
    def get_latest_by_conversation_id(
        cls,
        conversation_id: str,
        limit: int = 10
    ) -> List["CallTranscription"]:
        """
        Get the latest N transcriptions for a conversation.

        Args:
            conversation_id: ElevenLabs conversation identifier
            limit: Number of latest transcriptions to retrieve (default 10)

        Returns:
            List of CallTranscription objects ordered by sequence_number descending
        """
        with cls.get_session() as session:
            stmt = (
                select(cls)
                .where(cls.conversation_id == conversation_id)
                .order_by(cls.sequence_number.desc())
                .limit(limit)
            )
            return session.exec(stmt).all()
