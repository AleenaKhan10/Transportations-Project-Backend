from fastapi import FastAPI, Depends
from api.trailer_trip_data import router as trip_router
from api.samsara_data import router as samsara_router
from api.ditat_data import router as ditat_router
from auth import verify_token

app = FastAPI(dependencies=[Depends(verify_token)])

app.include_router(trip_router)
app.include_router(samsara_router)
app.include_router(ditat_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
