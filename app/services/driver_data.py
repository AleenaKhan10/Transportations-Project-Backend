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


# 9 . Fetch and store conversation data from ElevenLabs
@router.post(
    "/conversations/{conversation_id}/fetch",
    summary="Fetch and store conversation data from ElevenLabs",
    description="""
    Fetch complete conversation data from ElevenLabs API and update the database.

    This endpoint:
    - Retrieves conversation details from ElevenLabs API
    - Updates Call record with metadata (status, duration, timestamps)
    - Stores transcript in CallTranscription table
    - Useful for manual data retrieval or debugging

    **URL Parameters:**
    - conversation_id: ElevenLabs conversation identifier

    **Response:**
    - message: Success message
    - call_updated: Whether Call record was updated
    - transcriptions_added: Number of new transcriptions added
    - conversation_data: Full conversation data from ElevenLabs

    **Error Responses:**
    - 404: Conversation or Call not found
    - 500: API error or database error
    """
)
async def fetch_elevenlabs_conversation(conversation_id: str):
    """
    Fetch conversation data from ElevenLabs and update database.

    This endpoint is useful for:
    - Manual data retrieval
    - Debugging conversation issues
    - Backfilling missing data
    """
    try:
        from utils.elevenlabs_client import elevenlabs_client
        from models.call import Call, CallStatus
        from models.call_transcription import CallTranscription, SpeakerType
        from datetime import datetime, timezone, timedelta
        from helpers import logger

        logger.info(f"Fetching conversation data for: {conversation_id}")

        # Step 1: Fetch conversation data from ElevenLabs
        conversation_data = await elevenlabs_client.get_conversation(conversation_id)

        if not conversation_data:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found in ElevenLabs"
            )

        # Step 2: Find Call record by conversation_id
        call = Call.get_by_conversation_id(conversation_id)
        if not call:
            raise HTTPException(
                status_code=404,
                detail=f"Call record not found for conversation {conversation_id}"
            )

        # Step 3: Extract and update Call metadata
        metadata = conversation_data.get('metadata', {})
        call_duration = metadata.get('call_duration_secs', 0)
        call_successful = metadata.get('analysis', {}).get('call_successful', False)

        # Extract timestamps
        start_time_unix = metadata.get('start_time_unix_secs')
        if start_time_unix:
            call_start_time = datetime.fromtimestamp(start_time_unix, tz=timezone.utc)
            call_end_time = datetime.fromtimestamp(start_time_unix + call_duration, tz=timezone.utc)
        else:
            call_start_time = call.call_start_time
            call_end_time = None

        # Update Call status
        new_status = CallStatus.COMPLETED if call_successful else CallStatus.FAILED
        Call.update_status_by_call_sid(
            call_sid=call.call_sid,
            status=new_status,
            call_end_time=call_end_time
        )

        logger.info(f"Updated Call status to {new_status}")

        # Step 4: Store transcript
        transcript = conversation_data.get('transcript', [])
        transcriptions_added = 0

        # Check existing transcription count to avoid duplicates
        existing_count = CallTranscription.get_count_by_conversation_id(conversation_id)

        if existing_count > 0:
            logger.warning(f"Conversation {conversation_id} already has {existing_count} transcriptions. Skipping transcript storage.")
        else:
            for idx, message in enumerate(transcript):
                role = message.get('role', 'unknown')
                text = message.get('message', '')
                message_time_secs = message.get('time_in_call_secs', 0)

                # Map role to speaker_type
                speaker_type = SpeakerType.AGENT if role.lower() == 'agent' else SpeakerType.DRIVER

                # Calculate message timestamp
                message_timestamp = call_start_time + timedelta(seconds=message_time_secs) if call_start_time else datetime.now(timezone.utc)

                # Store transcription
                CallTranscription.create_transcription(
                    conversation_id=conversation_id,
                    speaker_type=speaker_type,
                    message_text=text,
                    timestamp=message_timestamp,
                    sequence_number=idx + 1
                )
                transcriptions_added += 1

            logger.info(f"Stored {transcriptions_added} transcriptions for conversation {conversation_id}")

        return {
            "message": "Conversation data fetched and stored successfully",
            "conversation_id": conversation_id,
            "call_sid": call.call_sid,
            "call_updated": True,
            "call_status": new_status.value,
            "call_duration": call_duration,
            "transcriptions_added": transcriptions_added,
            "transcriptions_total": existing_count + transcriptions_added,
            "conversation_data": conversation_data
        }

    except HTTPException:
        raise
    except Exception as err:
        from helpers import logger
        logger.error(f"Error fetching conversation {conversation_id}: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch conversation data: {str(err)}"
        )
