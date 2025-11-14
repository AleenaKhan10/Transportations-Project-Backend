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
    Receives events from ElevenLabs:
    - conversation.transcript → accumulates transcript
    - call.completed → updates DB with summary, transcript, duration
    """
    print(
        "-------------------------------------------------------------------------------------------"
    )
    print(request)
    try:
        body = await request.json()
        print(body)
        event = body.get("event")
        call_id = body.get("call_id") or body.get("callContextId")
        metadata = body.get("metadata", {})

        if not event:
            return {"status": "ignored_no_event"}

        # ---------------- Transcript chunk ----------------
        if event == "conversation.transcript":
            text = body.get("transcript") or ""
            CALL_TRANSCRIPTS.setdefault(call_id, "")
            CALL_TRANSCRIPTS[call_id] += text + "\n"
            return {"status": "transcript_saved"}

        # ---------------- Call completed ----------------
        elif event == "call.completed":
            summary = body.get("summary", "")
            duration = body.get("duration", 0)
            final_transcript = CALL_TRANSCRIPTS.get(call_id, "")

            update_payload = {
                "call_id": call_id,
                "call_summary": summary,
                "call_transcript": final_transcript,
                "call_duration": duration,
                "call_status": "completed",
            }

            print(
                "-------------------------------------------------------------------------------------------"
            )
            print(
                "------------------------------------------------------------------------------------------"
            )
            print("WEBHOOK RESPONSE UPDATED DATA")
            print(
                "------------------------------------------------------------------------------------------"
            )
            print(update_payload)

            # DriverTriggersViolationCalls.create_violation_data(update_payload)
            DriverTriggersViolationCalls.update_violation_by_call_id(
                call_id, update_payload
            )

            # Clean up memory
            if call_id in CALL_TRANSCRIPTS:
                del CALL_TRANSCRIPTS[call_id]

            return {"status": "saved_to_database"}

        else:
            return {"status": "ignored_event_type"}

    except Exception as e:
        import traceback

        raise HTTPException(
            status_code=500, detail=f"Webhook error: {str(e)}\n{traceback.format_exc()}"
        )
