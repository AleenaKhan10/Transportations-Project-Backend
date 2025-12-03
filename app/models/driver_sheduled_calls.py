from typing import Optional, List, Dict
from sqlmodel import Field, SQLModel, Session, select
from db import engine
import logging
from fastapi import HTTPException
import httpx
from config import settings
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class DriverSheduledCalls(SQLModel, table=True):
    __tablename__ = "driver_sheduled_calls_data"
    __table_args__ = {"extend_existing": True}

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    schedule_group_id: uuid.UUID = Field(index=True)

    driver: Optional[str] = None
    reminder: Optional[str] = None
    violation: Optional[str] = None

    call_scheduled_date_time: datetime

    status: bool = True

    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    # ---------------------------------------------------------------------
    # DB Session
    # ---------------------------------------------------------------------
    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    # ---------------------------------------------------------------------
    # GET ALL RECORDS
    # ---------------------------------------------------------------------
    @classmethod
    def get_all_sheduled_call_records(cls) -> List["DriverSheduledCalls"]:
        with cls.get_session() as session:
            statement = select(cls)
            results = session.exec(statement).all()
            return results
