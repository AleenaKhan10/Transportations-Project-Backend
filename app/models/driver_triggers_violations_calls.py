from sqlmodel import SQLModel, Field, Session, select
from typing import Optional, List
from datetime import datetime
import uuid
from db import engine


class DriverTriggersViolationCalls(SQLModel, table=True):
    __tablename__ = "driver_triggers_calls"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)

    driver_id: str = Field(nullable=False)
    driver_name: str = Field(nullable=False)

    call_summary: Optional[str] = None
    call_id: Optional[str] = Field(default=None, unique=True)
    phone: Optional[str] = None
    call_duration: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    call_status: Optional[str] = None
    recording_url: Optional[str] = None

    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    call_picked_up: Optional[bool] = Field(default=False)
    ended_reason: Optional[str] = None
    transcript: Optional[str] = None

    # ----------------------------------------------------
    #  DB Session
    # ----------------------------------------------------
    @classmethod
    def get_session(cls) -> Session:
        """Create a database session."""
        return Session(engine)

    # ----------------------------------------------------
    #  CREATE
    # ----------------------------------------------------
    @classmethod
    def create_violation_data(cls, data: dict) -> "DriverTriggersViolationCalls":
        """
        Insert a new violation call record.
        `data` should be a dict containing the fields to insert.
        """
        with cls.get_session() as session:
            record = cls(**data)
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    # ----------------------------------------------------
    #  GET ALL RECORDS
    # ----------------------------------------------------
    @classmethod
    def get_all_records_violations(cls) -> List["DriverTriggersViolationCalls"]:
        """
        Return all violation call records.
        """
        with cls.get_session() as session:
            return session.exec(select(cls)).all()

    # ----------------------------------------------------
    #  GET RECORD BY ID
    # ----------------------------------------------------
    @classmethod
    def get_violation_record_by_id(
        cls, record_id: str
    ) -> Optional["DriverTriggersViolationCalls"]:
        """
        Fetch a single violation call record by UUID.
        """
        with cls.get_session() as session:
            statement = select(cls).where(cls.id == record_id)
            return session.exec(statement).first()
