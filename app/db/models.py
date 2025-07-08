from typing import Optional
from sqlmodel import Field, SQLModel


class UserCreate(SQLModel):
    username: str = Field(index=True, unique=True)
    password: str

class User(UserCreate, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    is_active: bool = Field(default=True)
