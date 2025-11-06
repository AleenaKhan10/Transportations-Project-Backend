from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Session, select
from db import engine
from helpers import logger
import uuid


class DriverTriggersCalls(SQLModel, table=True):
    __tablename__ = "driver_triggers_calls"

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    driver_id: Optional[str]
    driver_name: Optional[str]
    call_summary: Optional[str] = None
    call_id: Optional[str] = Field(default=None, unique=True, index=True)
    phone: Optional[str] = None
    call_duration: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_session(cls) -> Session:
        """Create a database session"""
        return Session(engine)

    @classmethod
    def get_all(cls, limit: int = 1000) -> list["DriverTriggersCalls"]:
        """Get all trigger call records"""
        with cls.get_session() as session:
            try:
                statement = select(cls).limit(limit).order_by(cls.created_at.desc())
                records = session.exec(statement).all()
                return list(records)
            except Exception as err:
                logger.error(f"Database query error: {err}", exc_info=True)
                return []

    @classmethod
    def get_by_call_id(cls, call_id: str) -> Optional["DriverTriggersCalls"]:
        """Get record by call_id"""
        with cls.get_session() as session:
            try:
                statement = select(cls).where(cls.call_id == call_id)
                return session.exec(statement).first()
            except Exception as err:
                logger.error(f"Database query error: {err}", exc_info=True)
                return None
