from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel
from uuid import UUID, uuid4

class PageAccessTokens(SQLModel, table=True):
    __tablename__ = "page_access_tokens"

    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    page_name: str = Field(nullable=False)
    page_url: str = Field(nullable=False)
    page_access_token: str = Field(nullable=False, unique=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
