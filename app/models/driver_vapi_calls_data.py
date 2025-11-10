from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel, Field, Session, select, text
from pydantic import BaseModel

from db import engine
from helpers import logger


class DriverVapiCallsData(SQLModel, table=True):
    __tablename__ = "driver_triggers_calls"

    id: str = Field(default=None, primary_key=True)
    driver_id: str
    driver_name: str
    call_summary: Optional[str] = None
    call_id: Optional[str] = Field(default=None, unique=True)
    phone: Optional[str] = None
    call_duration: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    call_status: Optional[str] = None
    recording_url: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    call_picked_up: Optional[bool] = None
    ended_reason: Optional[str] = None
    transcript: Optional[str] = None
