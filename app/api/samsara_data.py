from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from providers.samsara_provider import ingest_samsara_data
from auth.security import verify_ingestion_token

router = APIRouter()

@router.post("/ingest-samsara", dependencies=[Depends(verify_ingestion_token)])
async def ingest_samsara():
    result = ingest_samsara_data()
    return JSONResponse(content=result) 