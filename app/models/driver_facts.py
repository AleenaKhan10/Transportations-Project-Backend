from typing import Optional
from datetime import datetime
from uuid import UUID

from db import engine
from helpers import logger

from sqlmodel import SQLModel, Field, Column, Text, Session, select
from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func


class DriverFacts(SQLModel, table=True):
    __tablename__ = "driver_facts"
    __table_args__ = {"schema": "dev"}

    id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=func.gen_random_uuid(),
        ),
    )

    driver_id: str = Field(nullable=False, index=True)
    caller_id: Optional[str] = Field(default=None, index=True)
    category: Optional[str] = Field(default=None, index=True)

    fact_key: str = Field(sa_column=Column(Text, nullable=False))

    fact_value: str = Field(sa_column=Column(Text, nullable=False))

    source_text: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
    )

    created_at: datetime = Field(
        sa_column=Column(
            nullable=False,
            server_default=func.now(),
        )
    )

    updated_at: datetime = Field(
        sa_column=Column(
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        )
    )

    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)

    @classmethod
    def get_all_driver_facts(cls, limit: int = 1000) -> list["DriverFacts"]:
        """Get all driver facrs"""
        with cls.get_session() as session:
            try:
                statement = select(cls).limit(limit).order_by(cls.created_at.desc())
                driver_facts = session.exec(statement).all()
                return list(driver_facts)
            except Exception as err:
                logger.error(f"Database query error: {err}", exc_info=True)
                return []
