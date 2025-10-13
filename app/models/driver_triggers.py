from typing import Optional, List, Dict
from sqlmodel import Field, SQLModel, Session, select
from db import engine
import logging
import httpx
from fastapi import HTTPException

from services.driver_triggers import DriverTriggerRequest


logger = logging.getLogger(__name__)


# -------------------------------
# DriverTripData MODEL
# -------------------------------
class DriverTriggersData(SQLModel, table=True):
    __tablename__ = "trips"
    __table_args__ = {"extend_existing": True}

    tripId: str = Field(primary_key=True, max_length=50)
    primaryDriverId: Optional[str] = Field(max_length=50, default=None)
    fuelPercent: Optional[float] = None
    outOfRoute: Optional[str] = Field(max_length=10, default=None)
    ditatSetPoint: Optional[float] = None
    tempC: Optional[float] = None
    tempF: Optional[float] = None
    etaTimeDifference: Optional[str] = Field(max_length=100, default=None)
    trlCheck: Optional[str] = Field(max_length=10, default=None)
    onTimeStatus: Optional[str] = Field(max_length=50, default=None)
    subStatusLabel: Optional[str] = Field(max_length=100, default=None)

    @classmethod
    def get_session(cls) -> Session:
        return Session(engine)

    @classmethod
    def get_trip_by_driver_id(cls, driver_id: str) -> Optional["DriverTriggersData"]:
        with cls.get_session() as session:
            statement = select(cls).where(cls.primaryDriverId == driver_id).limit(1)
            return session.exec(statement).first()
