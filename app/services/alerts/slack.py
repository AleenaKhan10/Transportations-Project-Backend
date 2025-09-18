from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from logic.alerts import send_slack_temp_alerts
from logic.auth.security import verify_static_token


router = APIRouter(prefix="/slack", dependencies=[Depends(verify_static_token)])

@router.post("/temperature")
async def slack_temp_alerts(bt: BackgroundTasks = BackgroundTasks()):
    result = send_slack_temp_alerts()
    return JSONResponse(content=result, status_code=result.get("slack_status", 200))
