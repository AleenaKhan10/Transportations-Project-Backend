from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4

class DriverPrompts(SQLModel, table=True):
    __tablename__ = "driver_prompts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    prompt_name: Optional[str] = Field(default=None, nullable=True)  # TEXT NULL
    condition_true_prompt: Optional[str] = Field(default=None, nullable=True)
    condition_false_prompt: Optional[str] = Field(default=None, nullable=True)
    description: Optional[str] = Field(default=None, nullable=True)
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
