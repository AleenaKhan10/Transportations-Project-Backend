from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse

from models.alert_filter import MuteEnum
from logic.auth.security import verify_webhook_token
from helpers.agy_utils import validate_entity_id_in_path
from logic.alerts import toggle_entity_alert, send_muted_entities


# Webhook router with static token authentication
router = APIRouter(prefix="/webhook", dependencies=[Depends(verify_webhook_token)])


@router.get("/alerts/slack/muted")
async def send_muted_entities_to_slack(channel: str):
    result = send_muted_entities(channel)
    return JSONResponse(content=result, status_code=200)

@router.get("/alerts/{mute_type}/{entity_id}")
async def mute_entity_alert(
    mute_type: MuteEnum = MuteEnum.MUTE,
    entity_id: str = Depends(validate_entity_id_in_path), 
    bt: BackgroundTasks = BackgroundTasks(),
):
    bt.add_task(toggle_entity_alert, entity_id, mute_type == MuteEnum.MUTE)
    return PlainTextResponse(f"Successfully {'muted' if mute_type == MuteEnum.MUTE else 'unmuted'} {entity_id} successfully", status_code=200)
