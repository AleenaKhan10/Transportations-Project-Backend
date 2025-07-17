import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class AlertFilterUpdate(SQLModel):
    exclude: bool = Field(default=True, description="Whether to exclude this filter from alerts")


class AlertFilterCreate(AlertFilterUpdate):
    trailer_id: str = Field(index=True, description="ID of the trailer to filter alerts for")
    trip_id: str = Field(index=True, description="ID of the trip to filter alerts for")


class AlertFilter(AlertFilterCreate, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime.datetime] = Field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc), description="Timestamp when the filter was created"
    )
    updated_at: Optional[datetime.datetime] = Field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc), description="Timestamp when the filter was last updated"
    )
