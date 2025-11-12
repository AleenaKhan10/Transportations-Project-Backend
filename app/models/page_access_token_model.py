from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel
from uuid import UUID, uuid4

class PageAccessTokens(SQLModel, table=True):
    __tablename__ = "page_access_tokens"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    page_name: str = Field(nullable=False)
    page_url: str = Field(nullable=False)
    description: Optional[str] = Field(default=None, nullable=True)  # new optional field
    category: Optional[str] = Field(default=None, nullable=True)     # new optional field
    page_access_token: Optional[str] = Field(default=None, nullable=True, unique=True)  # token can be null now
    filter: Optional[str] = Field(default=None, nullable=True)       # new filter field
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
