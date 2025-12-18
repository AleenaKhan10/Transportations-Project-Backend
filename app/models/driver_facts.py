from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4

from db import engine
from helpers import logger

from sqlmodel import SQLModel, Field, Column, Text, Session, select
from sqlalchemy import Column, Text


class DriverFacts(SQLModel, table=True):
    __tablename__ = "driver_facts"
    __table_args__ = {"schema": "dev"}

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)

    driver_id: str = Field(nullable=False, index=True)
    caller_id: Optional[str] = Field(default=None, index=True)
    category: Optional[str] = Field(default=None, index=True)
    fact_key: str = Field(Text, nullable=False)
    fact_value: str = Field(Text, nullable=False)
    source_text: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

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
