from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from logic.auth.security import verify_static_token
from logic.ingest import ingest_ditat_data, ingest_trailer_temp_data, ingest_trailer_stats_data


router = APIRouter(prefix="/ingest", dependencies=[Depends(verify_static_token)])

@router.post("/ditat", dependencies=[Depends(verify_static_token)])
async def ingest_ditat():
    result = ingest_ditat_data()
    return JSONResponse(content=result) 

@router.post("/samsara", dependencies=[Depends(verify_static_token)])
async def ingest_samsara_temp():
    
    result = {
        "trailer_temp": ingest_trailer_temp_data(),
        "trailer_stats": ingest_trailer_stats_data(),
    }
    return JSONResponse(content=result) 
