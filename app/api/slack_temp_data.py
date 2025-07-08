from fastapi import APIRouter
from fastapi.responses import JSONResponse
from providers.slack_temp_provider import send_slack_temp_alerts

router = APIRouter()

@router.post("/slack-temp-alerts")
async def slack_temp_alerts():
    result = send_slack_temp_alerts()
    return JSONResponse(content=result, status_code=result.get("slack_status", 200))
