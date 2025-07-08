from fastapi import FastAPI
from api.trailer_trip_data import router as trip_router
from api.samsara_data import router as samsara_router
from api.ditat_data import router as ditat_router
from auth.router import router as auth_router
from db.database import engine
from sqlmodel import SQLModel

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI()

app.add_event_handler("startup", create_db_and_tables)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(trip_router)
app.include_router(samsara_router)
app.include_router(ditat_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
