from fastapi import APIRouter
from fastapi.responses import JSONResponse
from providers.ditat_provider import ingest_ditat_data

router = APIRouter()

@router.post("/ingest-ditat")
async def ingest_ditat():
    result = ingest_ditat_data()
    return JSONResponse(content=result) 