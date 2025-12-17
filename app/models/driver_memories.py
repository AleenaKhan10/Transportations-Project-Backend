from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, Text, Session, select
from db import engine
from helpers import logger
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from pgvector.sqlalchemy import Vector


class DriverMemoriesResponse(SQLModel):
    """Response schema for DriverMemories - excludes embedding field (numpy array)"""
    id: Optional[UUID] = None
    driver_id: str
    caller_id: Optional[str] = None
    trip_id: Optional[str] = None
    category: Optional[str] = None
    summary: str
    raw_exchange: Optional[str] = None
    importance: str = "normal"
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    source_message_id: Optional[str] = None


class DriverMemories(SQLModel, table=True):
    __tablename__ = "driver_memories"
    __table_args__ = {"schema": "dev"}  # ✅ REQUIRED

    id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            primary_key=True,
        ),
    )

    driver_id: str = Field(nullable=False, index=True)
    caller_id: Optional[str] = Field(default=None)
    trip_id: Optional[str] = Field(default=None)

    category: Optional[str] = Field(default=None, index=True)

    summary: str = Field(sa_column=Column(Text, nullable=False))

    raw_exchange: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
    )

    # pgvector embedding
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(Vector(), nullable=True),
    )

    importance: str = Field(
        default="normal",
        nullable=False,
    )

    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(nullable=True),
    )

    expires_at: Optional[datetime] = Field(default=None)
    source_message_id: Optional[str] = Field(default=None)

    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)

    @classmethod
    def get_all_driver_memories(cls, limit: int = 1000) -> list["DriverMemories"]:
        """Get all driver memories"""
        with cls.get_session() as session:
            try:
                statement = select(cls).limit(limit).order_by(cls.created_at.desc())
                memories = session.exec(statement).all()
                return list(memories)
            except Exception as err:
                logger.error(f"Database query error: {err}", exc_info=True)
                return []
