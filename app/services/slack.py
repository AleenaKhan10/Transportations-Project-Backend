import json
import time
import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, Response

router = APIRouter(prefix="/slack")


# TODO: Replace this once testing is done
SLACK_SIGNING_SECRET = "SLACK_SIGNING_SECRET"

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
        SLACK_SIGNING_SECRET.encode('utf-8'),
        base_string,
        hashlib.sha256
    ).hexdigest()

    # Compare your signature with the one from Slack
    if not hmac.compare_digest(my_signature, slack_signature):
        raise HTTPException(status_code=403, detail="Slack signature verification failed.")


@router.post("/interactive")
async def slack_interactive_endpoint(request: Request):
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
    
    payload = json.loads(payload_str)
    
    # NOTE: send the data to webhook site (testing purposes only)
    import os
    webhook_url = os.getenv("WEBHOOKSITE_URL")
    if webhook_url:
        import requests
        requests.post(webhook_url, json=payload)

    # 3. Check if the interaction is a button click in a block
    if payload.get("type") == "block_actions":
        # There can be multiple actions, but for our case, we only expect one.
        action = payload["actions"][0]
        action_id = action.get("action_id")
        value = action.get("value") # This is the entity_id (e.g., trip_id, trailer_id)

        print(f"Received action: '{action_id}' with value: '{value}'")

    #     # 4. Route the action to the appropriate business logic
    #     if action_id == "mute_trip":
    #         mute_logic(entity_type="Trip", entity_id=value)
    #     elif action_id == "mute_trailer":
    #         mute_logic(entity_type="Trailer", entity_id=value)
    #     elif action_id == "unmute_entity":
    #         unmute_logic(entity_id=value)
    #     else:
    #         # Handle unknown actions if necessary
    #         print(f"⚠️ Received unknown action_id: {action_id}")

    # # 5. Acknowledge the request with a 200 OK to Slack within 3 seconds
    return Response(status_code=200)
