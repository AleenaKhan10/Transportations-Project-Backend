import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel
from pydantic import model_validator, field_validator
from helpers.agy_utils import is_trailer_id, is_trip_id, is_truck_id, IdType


class MuteEnum(str, Enum):
    MUTE = "mute"
    UNMUTE = "unmute"


class AlertFilterUpdate(SQLModel):
    exclude: bool = Field(default=True, description="Whether to exclude this filter from alerts")
    description: str | None = Field(default=None, description="Description of the filter")


class AlertFilterCreate(AlertFilterUpdate):
    entity_id: str = Field(index=True, unique=True, description="ID of the filter")
    id_type: IdType = Field(index=True, description="Type of the ID")
    
    @field_validator("id_type", mode="before")
    @classmethod
    def validate_id_type(cls, value):
        if isinstance(value, str):
            try:
                value = IdType(value)
            except ValueError:
                raise ValueError(f"Invalid ID type: {value}")
        return value
    
    @model_validator(mode="after")
    def validate_id(self):
        if self.id_type == IdType.TRAILER:
            if not is_trailer_id(self.entity_id):
                raise ValueError("Invalid trailer ID")
        elif self.id_type == IdType.TRIP:
            if not is_trip_id(self.entity_id):
                raise ValueError("Invalid trip ID")
        elif self.id_type == IdType.TRUCK:
            if not is_truck_id(self.entity_id):
                raise ValueError("Invalid truck ID")
        return self
    

class AlertFilter(AlertFilterCreate, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime.datetime] = Field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc), 
        description="Timestamp when the filter was created"
    )
    updated_at: Optional[datetime.datetime] = Field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc), 
        description="Timestamp when the filter was last updated"
    )
