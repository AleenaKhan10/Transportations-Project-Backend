from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services import (
    auth_router,
    trip_router,
    alert_router,
    drivers_router,
    webhook_router,
)
from services.users import router as users_router
from services.vapi import router as vapi_router, router_no_auth as vapi_router_no_auth
from services.reports import router as reports_router
from services.pcmiler import router as pcmiler_router
from services.slack import router as slack_router
from services.weather import router as weather_router
from services.truck_mapping import router as truck_mapping_router
from services.temp_sensor_mapping import router as temp_sensor_mapping_router
from services.trailer_unit_mapping import router as trailer_unit_mapping_router
from services.active_load_tracking import router as active_load_tracking_router
from services.violation_alerts import router as violation_alerts_router
from services.dispatched_trips import router as dispatched_trips_router
from services.driver_mapping import router as driver_mapping_router

# Import new admin routers
from services.admin_users import router as admin_users_router
from services.admin_roles import router as admin_roles_router
from services.admin_permissions import router as admin_permissions_router
from services.admin_sessions import router as admin_sessions_router
from services.admin_audit import router as admin_audit_router
from services.admin_export import router as admin_export_router

# new test router
from services.test_service import router as test_service

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

# Include existing routers
app.include_router(auth_router, tags=["auth"])
app.include_router(users_router, tags=["users"])
app.include_router(trip_router, tags=["trips"])
# app.include_router(ingest_router, tags=["ingest"])
app.include_router(alert_router, tags=["alerts"])
app.include_router(drivers_router, tags=["drivers"])
app.include_router(vapi_router, tags=["vapi"])
app.include_router(vapi_router_no_auth, tags=["vapi"])
app.include_router(reports_router, tags=["reports"])
app.include_router(pcmiler_router, tags=["pcmiler"])
app.include_router(webhook_router, tags=["webhook"])
app.include_router(slack_router, tags=["slack"])
app.include_router(weather_router, tags=["weather"])
app.include_router(truck_mapping_router, tags=["truck-mapping"])
app.include_router(temp_sensor_mapping_router, tags=["temp-sensor-mapping"])
app.include_router(trailer_unit_mapping_router, tags=["trailer-unit-mapping"])
app.include_router(active_load_tracking_router)
app.include_router(violation_alerts_router)
app.include_router(dispatched_trips_router)
app.include_router(driver_mapping_router, tags=["driver-mapping"])

# Include new admin routers
app.include_router(admin_users_router)
app.include_router(admin_roles_router)
app.include_router(admin_permissions_router)
app.include_router(admin_sessions_router)
app.include_router(admin_audit_router)
app.include_router(admin_export_router)

# test
app.include_router(test_service)

#main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
