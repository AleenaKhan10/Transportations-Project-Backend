from typing import Optional
from pydantic import BaseModel


class ETARequest(BaseModel):
    origin: str
    destination: str
    departureTime: Optional[str] = None