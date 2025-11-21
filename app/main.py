from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from config import settings
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
from services.driver_prompt_service import router as driver_prompt_router


# Import new admin routers
from services.admin_users import router as admin_users_router
from services.admin_roles import router as admin_roles_router
from services.admin_permissions import router as admin_permissions_router
from services.admin_sessions import router as admin_sessions_router
from services.admin_audit import router as admin_audit_router
from services.admin_export import router as admin_export_router


# new test router
from services.test_service import router as test_service

# new data apis
from services.driver_data import router as drive_data

# from services.driver_triggers import router as driver_triggers
from services.driver_triggers import router as driver_triggers
from services.page_access_token_service import router as page_access_token
from services.webhooks_elevenlabs import router as webhooks_elevenlabs_router
from services.calls import router as calls_router

from db.database import engine
from sqlmodel import SQLModel


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# Initialize Sentry/GlitchTip for error tracking
def before_send(event, hint):
    """
    Filter events before sending to Sentry.
    Only capture critical errors and API failures, ignore minor issues.
    """
    # Get the exception if available
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        # Ignore common HTTP exceptions that aren't real errors
        ignored_exceptions = [
            "HTTPException",  # FastAPI's HTTPException for expected errors
            "RequestValidationError",  # Pydantic validation errors (user input errors)
            "ValidationError",  # General validation errors
        ]

        if exc_type.__name__ in ignored_exceptions:
            return None

    # Only capture errors with severity level of 'error' or higher
    if event.get("level") in ["error", "fatal"]:
        return event

    return None


# Only initialize Sentry if DSN is configured
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        before_send=before_send,
        # Capture unhandled exceptions
        send_default_pii=False,  # Don't send personally identifiable information
        attach_stacktrace=True,  # Always attach stack traces
        # Performance monitoring
        enable_tracing=True,
    )


app = FastAPI(title="AGY Intelligence Hub", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_event_handler("startup", create_db_and_tables)


# Global exception handler to catch unhandled API errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions and send them to Sentry.
    This ensures critical API failures are tracked.
    """
    # Capture the exception in Sentry
    if settings.SENTRY_DSN:
        sentry_sdk.capture_exception(exc)

    # Return a generic error response to the client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. The error has been logged and will be investigated.",
            "error_type": type(exc).__name__,
        },
    )


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
app.include_router(drive_data)
app.include_router(driver_triggers)
app.include_router(page_access_token)
app.include_router(driver_prompt_router)

# ElevenLabs webhooks and call management
app.include_router(webhooks_elevenlabs_router)
app.include_router(calls_router)


# main
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
