from fastapi import APIRouter, HTTPException
from models.driver_data import (
    DriverTripData,
    ActiveLoadTracking,
    ViolationAlertDriver,
    get_driver_summary,
    make_drivers_violation_batch_call,
    make_drivers_violation_batch_call_elevenlabs,
    generate_prompt_for_driver,
)

from models.vapi import BatchCallRequest, GeneratePromptRequest

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


# 8 . make driver violation batch call using ElevenLabs
@router.post(
    "/call-elevenlabs",
    summary="Initiate driver violation call via ElevenLabs",
    description="""
    Create an outbound driver violation call using ElevenLabs conversational AI.

    This endpoint processes driver violation data and initiates a phone call using
    ElevenLabs API instead of VAPI. It maintains the same request/response structure
    as the VAPI endpoint for compatibility.

    **Key Features:**
    - Accepts BatchCallRequest with driver violation details
    - Processes only the first driver in the drivers array
    - Normalizes phone numbers to E.164 format
    - Generates dynamic conversational prompts based on violations
    - Returns conversation_id for call tracking

    **Request Structure:**
    - callType: Type of call (e.g., "violation")
    - timestamp: ISO 8601 timestamp
    - drivers: Array of driver data (only first driver processed)

    **Response Structure:**
    - message: Success message
    - timestamp: Original request timestamp
    - driver: Driver information with normalized phone number
    - conversation_id: ElevenLabs conversation identifier
    - callSid: Twilio call SID from ElevenLabs
    - triggers_count: Number of violations processed

    **Error Responses:**
    - 400: Invalid request or no driver data provided
    - 500: Call initiation failed or server error
    """
)
async def make_driver_violation_call_elevenlabs(request: BatchCallRequest):
    """
    Initiate driver violation call using ElevenLabs API.

    This endpoint provides an alternative to the VAPI-based /call endpoint,
    using ElevenLabs conversational AI for outbound driver calls.
    """
    try:
        result = await make_drivers_violation_batch_call_elevenlabs(request)
        return result
    except HTTPException:
        # Re-raise HTTPException to preserve status codes
        raise
    except Exception as err:
        # Log general exceptions and return 500
        from helpers import logger
        logger.error(f"Error in ElevenLabs endpoint: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process ElevenLabs call request: {str(err)}"
        )
