from fastapi import APIRouter

from services.alerts.filters import router as alert_filter_router
from services.alerts.slack import router as slack_alert_router

router = APIRouter(prefix="/alerts")
router.include_router(alert_filter_router)
router.include_router(slack_alert_router)

__all__ = ["router"]