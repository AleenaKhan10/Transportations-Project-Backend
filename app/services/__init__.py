from services.auth import router as auth_router
from services.trips import router as trip_router
from services.alerts import router as alert_router
from services.ingest import router as ingest_router
from services.drivers import router as drivers_router
from services.webhook import router as webhook_router

__all__ = [
    "auth_router",
    "trip_router",
    "alert_router",
    "ingest_router",
    "drivers_router",
    "webhook_router",
]
