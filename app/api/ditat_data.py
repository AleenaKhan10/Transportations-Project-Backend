from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from providers.ditat_provider import ingest_ditat_data
from auth.security import verify_ingestion_token

router = APIRouter()

@router.post("/ingest-ditat", dependencies=[Depends(verify_ingestion_token)])
async def ingest_ditat():
    result = ingest_ditat_data()
    return JSONResponse(content=result) 