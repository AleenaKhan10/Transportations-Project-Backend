from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models import vector_embeddings


class TextRequest(BaseModel):
    text: str


router = APIRouter(prefix="/vector_embeddings", tags=["vector_embeddings"])


@router.post("/embed")
async def create_call_embeddings(request: TextRequest):
    """
    Endpoint to generate and store text embeddings in Supabase.
    """
    try:
        result = vector_embeddings.generate_text_embedding(request.text)
        return {"message": "Embedding stored successfully", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/driver-memory")
def get_all_memory():
    return vector_embeddings.DriverMemory.get_all()
