from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import PlainTextResponse

from models.alert_filter import MuteEnum
from logic.alerts import toggle_entity_alert
from logic.auth.security import verify_webhook_token
from helpers.agy_utils import validate_entity_id_in_path


# Webhook router with static token authentication
router = APIRouter(prefix="/webhook", dependencies=[Depends(verify_webhook_token)])


@router.get("/alerts/{mute_type}/{entity_id}")
async def mute_entity_alert(
    mute_type: MuteEnum = MuteEnum.MUTE,
    entity_id: str = Depends(validate_entity_id_in_path), 
    bt: BackgroundTasks = BackgroundTasks(),
):
    bt.add_task(toggle_entity_alert, entity_id, mute_type == MuteEnum.MUTE)
    return PlainTextResponse(f"Successfully {'muted' if mute_type == MuteEnum.MUTE else 'unmuted'} {entity_id} successfully", status_code=200)
