from fastapi import FastAPI
from services import (
    auth_router,
    trip_router,
    ingest_router,
    alert_router,
    drivers_router,
)
from db.database import engine
from sqlmodel import SQLModel

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI()

app.add_event_handler("startup", create_db_and_tables)

app.include_router(auth_router, tags=["auth"])
app.include_router(trip_router, tags=["trips"])
app.include_router(ingest_router, tags=["ingest"])
app.include_router(alert_router, tags=["alerts"])
app.include_router(drivers_router, tags=["drivers"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
