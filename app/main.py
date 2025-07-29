from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services import (
    auth_router,
    trip_router,
    ingest_router,
    alert_router,
    drivers_router,
)
from services.vapi import router as vapi_router, router_no_auth as vapi_router_no_auth
from services.reports import router as reports_router
from services.pcmiler import router as pcmiler_router
from db.database import engine
from sqlmodel import SQLModel

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI(title="AGY Intelligence Hub", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_event_handler("startup", create_db_and_tables)

app.include_router(auth_router, tags=["auth"])
app.include_router(trip_router, tags=["trips"])
app.include_router(ingest_router, tags=["ingest"])
app.include_router(alert_router, tags=["alerts"])
app.include_router(drivers_router, tags=["drivers"])
app.include_router(vapi_router, tags=["vapi"])
app.include_router(vapi_router_no_auth, tags=["vapi"])
app.include_router(reports_router, tags=["reports"])
app.include_router(pcmiler_router, tags=["pcmiler"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
