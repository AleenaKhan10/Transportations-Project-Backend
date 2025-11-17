from fastapi import APIRouter, HTTPException, Request
from models.driver_data import (
    DriverTripData,
    ActiveLoadTracking,
    ViolationAlertDriver,
    get_driver_summary,
    make_drivers_violation_batch_call,
    generate_prompt_for_driver,
)

from models.vapi import BatchCallRequest, GeneratePromptRequest
from models.driver_triggers_violations_calls import DriverTriggersViolationCalls
from datetime import datetime, timezone

# Router with prefix + tags
router = APIRouter(prefix="/driver_data", tags=["driver_data"])


# 1. Return all trips
@router.get("/trips")
def get_all_trips():
    trips = DriverTripData.get_all()
    return {
        "message": "Trips fetched successfully",
        "data": trips,
    }


@router.get("/trips/{trip_id}")
def get_by_trip(trip_id):
    trips = DriverTripData.get_by_trip(trip_id)
    return {
        "message": "Trips fetched successfully",
        "data": trips,
    }


# 2. Return all active load tracking
@router.get("/active-loads")
def get_all_active_loads():
    loads = ActiveLoadTracking.get_all()
    return {
        "message": "Active load tracking fetched successfully",
        "data": loads,
    }


# 3. Return combined data by driver_id
@router.get("/{driver_id}")
def get_driver_combined(driver_id: str):
    result = get_driver_summary(driver_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No trip/active load found for this driver",
        )
    return result


# 4 . Return combined data by driver_id
@router.get("/violation/{trip_id}")
def get_driver_combined(trip_id: str):
    result = ViolationAlertDriver.get_by_trip_id(trip_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No trip/active load found for this driver",
        )
    return result


# 5 . Return combined data by driver_id
@router.get("/load/{trip_id}")
def get_driver_combined(trip_id: str):
    result = ActiveLoadTracking.get_by_trip(trip_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No trip/active load found for this driver",
        )
    return result


# 6 . make driver violation batch call
@router.post("/call")
async def make_driver_violation_call(request: BatchCallRequest):
    result = await make_drivers_violation_batch_call(request)
    return result


# 7 . generate prompt for driver based on triggers
@router.post("/generate-prompt")
async def generate_prompt(request: GeneratePromptRequest):
    """
    Generate a prompt for a driver based on phone number and triggers.
    This endpoint pulls all relevant driver data and generates a prompt
    but does NOT send it to any external API - just returns the prompt.
    """
    result = await generate_prompt_for_driver(request)
    return result


# ----------------- Webhook to receive ElevenLabs events -----------------
CALL_TRANSCRIPTS = {}


@router.post("/call/webhook")
async def elevenlabs_call_webhook(request: Request):
    """
    Handles ElevenLabs post-call webhook:
    - Extracts conversation_id (your call_id)
    - Extracts full transcript (array of messages)
    - Extracts summary & call duration
    - Updates DB by call_id
    """
    try:
        body = await request.json()
        print("---- ElevenLabs Webhook Received ----")
        print(body)
        print("---- BODY ENDS ----")

        # ----------------------------
        # VALIDATE ROOT STRUCTURE
        # ----------------------------
        event_type = body.get("type")  # e.g. "post_call_transcription"
        data = body.get("data", {})

        if not data:
            return {"status": "ignored_no_data"}

        # ----------------------------
        # EXTRACT IMPORTANT FIELDS
        # ----------------------------
        call_id = data.get("conversation_id")  # This will act as our Call ID
        transcript_list = data.get("transcript", [])
        metadata = data.get("metadata", {})

        call_duration = metadata.get("call_duration_secs", 0)
        # Call SID
        call_sid = metadata.get("phone_call", {}).get("call_sid")
        # Transcript Summary
        call_summary = metadata.get("analysis", {}).get("transcript_summary")
        # Call Status
        call_status = metadata.get("analysis", {}).get("call_successful")
        # Ended Reason
        termination_reason = metadata.get("termination_reason", {})
        # Call Start Time
        unix_start = metadata.get("start_time_unix_secs", {})
        # Call End Time Time
        unix_end = metadata.get("start_time_unix_secs", {}) + call_duration

        # Convert UNIX seconds → UTC datetime
        call_start_time = datetime.fromtimestamp(unix_start, tz=timezone.utc)
        call_end_time = datetime.fromtimestamp(unix_end, tz=timezone.utc)
        print("---- Call Sid ----")
        print(call_sid)

        # ----------------------------
        # FORMAT FULL TRANSCRIPT TEXT
        # ----------------------------
        full_transcript = ""
        for msg in transcript_list:
            role = msg.get("role", "unknown")
            text = msg.get("message") or ""
            full_transcript += f"{role.upper()}: {text}\n"

        # ----------------------------
        # BUILD PAYLOAD FOR DATABASE
        # ----------------------------
        update_payload = {
            "call_summary": call_summary,
            "transcript": full_transcript,
            "call_duration": call_duration,
            "call_status": call_status,
            "call_picked_up": True,
            "ended_reason": termination_reason,
            "started_at": call_start_time,
            "ended_at": call_end_time,
        }

        print("---- FINAL UPDATE PAYLOAD ----")
        print(update_payload)

        # ----------------------------
        # UPDATE IN DATABASE
        # ----------------------------
        DriverTriggersViolationCalls.update_violation_by_call_id(
            call_sid, update_payload
        )

        return {"status": "saved_to_database"}

    except Exception as e:
        import traceback

        raise HTTPException(
            status_code=500,
            detail=f"Webhook parsing error: {str(e)}\n{traceback.format_exc()}",
        )
