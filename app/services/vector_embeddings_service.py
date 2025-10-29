from fastapi import APIRouter, HTTPException
from models import vector_embeddings

router = APIRouter(prefix="/vector_embeddings", tags=["vector_embeddings"])


@router.post("/add-memory")
async def add_memory(request: vector_embeddings.MemoryRequest):
    """
    Generate embeddings using OpenAI and store them in Supabase.
    """
    try:
        return await vector_embeddings.DriverMemory.add_driver_memory(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embed")
async def create_call_embeddings(request: vector_embeddings.MemoryRequest):
    """
    Generate only embeddings (without storing).
    """
    try:
        result = vector_embeddings.generate_text_embedding(request.text)
        return {"message": "Embedding generated successfully", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/driver-memory")
def get_all_memory():
    """Retrieve all stored driver memory records"""
    return vector_embeddings.DriverMemory.get_all()


@router.post("/driver-memory/search")
def search_driver_memory(request: vector_embeddings.MemoryRequest):
    """
    Perform similarity search to find related driver memories.
    """
    return vector_embeddings.DriverMemory.similarity_search(
        driver_id=request.driver_id, query_text=request.text
    )
