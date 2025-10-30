from fastapi import HTTPException
from pydantic import BaseModel
from db.test_db import vector_engine
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import Column, text
from sqlalchemy.types import UserDefinedType
from typing import Optional, List
from datetime import datetime
import requests
from config import settings


# -------------------------
# Custom Vector type
# -------------------------
class Vector(UserDefinedType):
    def get_col_spec(self):
        return "vector(1536)"  # Ensure same as pgvector extension

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if isinstance(value, list):
                return "[" + ",".join(map(str, value)) + "]"  # required pgvector format
            return value

        return process


# -------------------------
# Embedding Generator
# -------------------------
def generate_text_embedding(text: str) -> list[float]:
    """Generate vector embeddings using OpenAI API."""
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.OPEN_AI_KEY}",
    }

    payload = {
        "model": "text-embedding-3-small",
        "input": text,
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data["data"][0]["embedding"]


# -------------------------
# Request Schema
# -------------------------
class MemoryRequest(BaseModel):
    driver_id: str
    text: str


# -------------------------
# DriverMemory Model
# -------------------------
class DriverMemory(SQLModel, table=True):
    __tablename__ = "driver_memory"

    id: Optional[int] = Field(default=None, primary_key=True)
    driver_id: str
    text: str
    embedding: Optional[List[float]] = Field(sa_column=Column(Vector))
    date: Optional[datetime] = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_session(cls) -> Session:
        return Session(vector_engine)

    # Create a new memory
    @classmethod
    def create(cls, driver_id: str, text: str, embedding: List[float]):
        with cls.get_session() as session:
            memory = cls(driver_id=driver_id, text=text, embedding=embedding)
            session.add(memory)
            session.commit()
            session.refresh(memory)
            return memory

    # Store memory with generated embedding
    @classmethod
    async def add_driver_memory(cls, request: MemoryRequest):
        try:
            embedding = generate_text_embedding(request.text)
            record = cls.create(request.driver_id, request.text, embedding)
            return {
                "message": "Memory stored successfully",
                "record": {
                    "id": record.id,
                    "driver_id": record.driver_id,
                    "text": record.text,
                    "date": record.date,
                },
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # -------------------------
    # Similarity Search
    # -------------------------
    @classmethod
    def similarity_search(cls, driver_id: str, query_text: str, top_k: int = 3):
        # 1) Get embedding list of floats
        query_embedding = generate_text_embedding(query_text)
        if not query_embedding:
            raise ValueError("Failed to generate embedding")

        # 2) Build a safe vector literal: [0.1,0.2,...]
        # Use repr/formatting to avoid scientific notation issues if needed
        embedding_items = (format(x, ".18g") for x in query_embedding)
        embedding_literal = "[" + ",".join(embedding_items) + "]"

        # 3) Put the literal into SQL (cast to extensions.vector)
        sql = text(
            f"""
                SELECT
                    id,
                    driver_id,
                    text,
                    date,
                    1 - (embedding <=> '{embedding_literal}'::vector) AS similarity
                FROM driver_memory
                WHERE driver_id = :driver_id
                AND (1 - (embedding <=> '{embedding_literal}'::vector)) > 0.5
                ORDER BY embedding <=> '{embedding_literal}'::vector
                LIMIT :top_k;
                """
        )

        with cls.get_session() as session:
            # pass driver_id and top_k safely as params for the rest
            result = session.execute(sql, {"driver_id": driver_id, "top_k": top_k})
            return [dict(row._mapping) for row in result]
