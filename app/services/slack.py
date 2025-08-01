import json
import time
import hmac
import hashlib
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, Response

from helpers import logger
from config import settings
from logic.alerts import (
    toggle_entity_alert_and_notify,
    send_muted_entities,
    ActionValue,
    ActionId,
)


router = APIRouter(prefix="/slack")

# --- Security: Slack Request Verification ---

async def verify_slack_request(request: Request):
    """
    Verifies that the incoming request is genuinely from Slack.
    
    See: https://api.slack.com/authentication/verifying-requests-from-slack
    """
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    slack_signature = request.headers.get("X-Slack-Signature")

    if not timestamp or not slack_signature:
        raise HTTPException(status_code=403, detail="Slack signature headers not found.")

    # Prevent replay attacks
    if abs(time.time() - int(timestamp)) > 60 * 5:
        raise HTTPException(status_code=403, detail="Request timestamp is too old.")

    # Get the raw request body
    body = await request.body()
    
    # Create the signature base string
    base_string = f"v0:{timestamp}:{body.decode('utf-8')}".encode('utf-8')
    
    # Hash the base string with your signing secret
    my_signature = 'v0=' + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode('utf-8'),
        base_string,
        hashlib.sha256
    ).hexdigest()

    # Compare signature with the one from Slack
    if not hmac.compare_digest(my_signature, slack_signature):
        raise HTTPException(status_code=403, detail="Slack signature verification failed.")


@router.post("/interactions")
async def slack_interactive_endpoint(request: Request, bt: BackgroundTasks = BackgroundTasks()):
    """
    This endpoint handles all interactive components from Slack,
    such as button clicks.
    """
    # 1. Verify that the request is from Slack (CRITICAL FOR SECURITY)
    # Comment out the line below if you are testing locally with a tool like ngrok
    # and haven't set up your signing secret yet.
    # await verify_slack_request(request)

    # 2. Parse the payload from the form data
    form_data = await request.form()
    payload_str = form_data.get("payload")
    if not payload_str:
        raise HTTPException(status_code=400, detail="Payload not found.")
    
    payload: dict = json.loads(payload_str)

    # 3. Check if the interaction is a button click in a block
    if payload.get("type") == "block_actions":
        # There can be multiple actions, but for our case, we only expect one.
        action: dict = payload["actions"][0]
        action_id = ActionId.from_id(action.get("action_id"))
        value = ActionValue.from_value(action.get("value"))
        
        logger.info(f"Received action: '{action_id}' with value: '{value}'")
        
        if not action_id or not value:
            raise HTTPException(status_code=400, detail="Action ID or Value not found.")

        # 4. Route the action to the appropriate business logic
        if action_id in (ActionId.MUTE_ENTITY, ActionId.UNMUTE_ENTITY):
            bt.add_task(
                toggle_entity_alert_and_notify, 
                entity_id=value.id, 
                mute_type=value.mute_type,
                channel=value.channel,
            )
        elif action_id == ActionId.MUTED_ENTITIES:
            bt.add_task(send_muted_entities, channel=value.channel)
        else:
            # Handle unknown actions if necessary
            logger.warning(f"⚠️ Received unknown action_id: {action_id}")

    # # 5. Acknowledge the request with a 200 OK to Slack within 3 seconds
    return Response(status_code=200)
