from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services import ingest_router
from db.database import engine
from sqlmodel import SQLModel

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Create separate FastAPI app for ingest service
app = FastAPI(
    title="AGY Ingest Service", 
    version="1.0.0",
    description="Dedicated service for data ingestion operations"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_event_handler("startup", create_db_and_tables)

# Include only the ingest router
app.include_router(ingest_router, tags=["ingest"])

# # Health check endpoint for the ingest service
# @ingest_app.get("/health")
# async def health_check():
#     return {"status": "healthy", "service": "ingest"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ingest_app:ingest_app", host="0.0.0.0", port=8000, reload=True)