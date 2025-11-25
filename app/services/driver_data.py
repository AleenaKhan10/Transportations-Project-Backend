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

        # Step 0: Validate conversation_id format
        if not conversation_id or not conversation_id.startswith('conv_'):
            logger.warning(f"[VALIDATION] Invalid conversation_id format: {conversation_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid conversation_id format. Expected format: conv_xxx, got: {conversation_id}"
            )

        # Additional validation: filter out test IDs
        if 'test' in conversation_id.lower() or 'dummy' in conversation_id.lower():
            logger.warning(f"[VALIDATION] Test/dummy conversation_id detected: {conversation_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Test/dummy conversation IDs are not allowed: {conversation_id}"
            )

        logger.info(f"[FETCH] Starting fetch for conversation: {conversation_id}")

        # Step 1: Find Call record first to avoid unnecessary API calls
        call = Call.get_by_conversation_id(conversation_id)
        if not call:
            logger.warning(f"[DB] No Call record found for conversation {conversation_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Call record not found for conversation {conversation_id}. This conversation may not belong to this system."
            )

        logger.info(f"[DB] Found Call record - call_sid: {call.call_sid}, driver_id: {call.driver_id}, current_status: {call.status.value}")

        # Step 2: Fetch conversation data from ElevenLabs
        logger.info(f"[API] Calling ElevenLabs API for conversation: {conversation_id}")
        conversation_data = await elevenlabs_client.get_conversation(conversation_id)

        if not conversation_data:
            logger.warning(f"[API] ElevenLabs returned empty data for conversation: {conversation_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found in ElevenLabs"
            )

        logger.info(f"[API] Successfully fetched conversation data - status: {conversation_data.get('status', 'unknown')}")

        # Step 3: Extract and update Call metadata
        import json

        metadata = conversation_data.get('metadata', {})
        analysis = conversation_data.get('analysis', {})

        # Extract all fields
        call_duration = metadata.get('call_duration_secs', 0)
        cost_value = metadata.get('cost', 0) / 100000.0 if metadata.get('cost') else None  # Convert from micro-units

        # Call successful can be boolean or string "success"/"failure"
        call_successful_raw = analysis.get('call_successful')
        if isinstance(call_successful_raw, str):
            call_successful = call_successful_raw.lower() == 'success'
        else:
            call_successful = bool(call_successful_raw)

        transcript_summary = analysis.get('transcript_summary', '')

        # Extract timestamps
        start_time_unix = metadata.get('start_time_unix_secs')
        if start_time_unix:
            call_start_time = datetime.fromtimestamp(start_time_unix, tz=timezone.utc)
            call_end_time = datetime.fromtimestamp(start_time_unix + call_duration, tz=timezone.utc)
        else:
            call_start_time = call.call_start_time
            call_end_time = None

        # Determine status
        conversation_status = conversation_data.get('status', 'unknown')
        if conversation_status == 'done':
            new_status = CallStatus.COMPLETED if call_successful else CallStatus.FAILED
        else:
            new_status = CallStatus.IN_PROGRESS

        logger.info(f"[METADATA] Extracted data - conversation_status: {conversation_status}, new_status: {new_status.value}, duration: {call_duration}s, cost: ${cost_value}, successful: {call_successful}, has_summary: {bool(transcript_summary)}")

        # Update Call with ALL metadata
        Call.update_conversation_metadata(
            call_sid=call.call_sid,
            status=new_status,
            call_end_time=call_end_time,
            transcript_summary=transcript_summary,
            call_duration_seconds=call_duration,
            cost=cost_value,
            call_successful=call_successful,
            analysis_data=json.dumps(analysis),
            metadata_json=json.dumps(metadata)
        )

        logger.info(f"[DB] Successfully updated Call {call.call_sid} with full metadata - status: {new_status.value}, summary: {len(transcript_summary) if transcript_summary else 0} chars")

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
            "call_successful": call_successful,
            "call_duration": call_duration,
            "transcript_summary": transcript_summary,
            "cost": cost_value,
            "transcriptions_added": transcriptions_added,
            "transcriptions_total": existing_count + transcriptions_added,
            "should_stop_polling": conversation_status == 'done',  # Frontend can use this to stop polling
            "conversation_data": conversation_data
        }

    except HTTPException:
        raise
    except Exception as err:
        from helpers import logger
        error_message = str(err)

        # Check if it's a "not found" error from ElevenLabs
        if "not found" in error_message.lower() or "404" in error_message:
            logger.warning(f"Conversation {conversation_id} not found in ElevenLabs")
            raise HTTPException(
                status_code=404,
                detail=f"Conversation not found in ElevenLabs: {conversation_id}"
            )

        # Other errors remain 500
        logger.error(f"Error fetching conversation {conversation_id}: {err}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch conversation data: {error_message}"
        )
