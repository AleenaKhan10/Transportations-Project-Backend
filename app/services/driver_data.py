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
    """,
)
async def make_driver_violation_call_elevenlabs(request: BatchCallRequest):
    """
    Initiate driver violation call using ElevenLabs API.

    This endpoint provides an alternative to the VAPI-based /call endpoint,
    using ElevenLabs conversational AI for outbound driver calls.
    """
    import logging
    from datetime import datetime, timezone

    logger = logging.getLogger(__name__)
    request_id = datetime.now(timezone.utc).strftime("%H%M%S%f")[:12]

    driver_id = request.drivers[0].driverId if request.drivers else "unknown"
    logger.info(f"[ENDPOINT] call-elevenlabs received request for driver {driver_id} (request_id={request_id})")
    print(f"[ENDPOINT] call-elevenlabs received at {datetime.now(timezone.utc).isoformat()} for driver {driver_id}")

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
            detail=f"Failed to process ElevenLabs call request: {str(err)}",
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
    """,
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
        if not conversation_id or not conversation_id.startswith("conv_"):
            logger.warning(
                f"[VALIDATION] Invalid conversation_id format: {conversation_id}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid conversation_id format. Expected format: conv_xxx, got: {conversation_id}",
            )

        # Additional validation: filter out test IDs
        if "test" in conversation_id.lower() or "dummy" in conversation_id.lower():
            logger.warning(
                f"[VALIDATION] Test/dummy conversation_id detected: {conversation_id}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Test/dummy conversation IDs are not allowed: {conversation_id}",
            )

        logger.info(f"[FETCH] Starting fetch for conversation: {conversation_id}")

        # Step 1: Find Call record first to avoid unnecessary API calls
        call = Call.get_by_conversation_id(conversation_id)
        if not call:
            logger.warning(
                f"[DB] No Call record found for conversation {conversation_id}"
            )
            raise HTTPException(
                status_code=404,
                detail=f"Call record not found for conversation {conversation_id}. This conversation may not belong to this system.",
            )

        logger.info(
            f"[DB] Found Call record - call_sid: {call.call_sid}, driver_id: {call.driver_id}, current_status: {call.status.value}"
        )

        # Step 2: Fetch conversation data from ElevenLabs
        logger.info(f"[API] Calling ElevenLabs API for conversation: {conversation_id}")
        conversation_data = await elevenlabs_client.get_conversation(conversation_id)

        if not conversation_data:
            logger.warning(
                f"[API] ElevenLabs returned empty data for conversation: {conversation_id}"
            )
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found in ElevenLabs",
            )

        logger.info(
            f"[API] Successfully fetched conversation data - status: {conversation_data.get('status', 'unknown')}"
        )

        # Step 3: Extract and update Call metadata
        import json

        metadata = conversation_data.get("metadata", {})
        analysis = conversation_data.get("analysis", {})

        # Extract all fields
        call_duration = metadata.get("call_duration_secs", 0)
        cost_value = (
            metadata.get("cost", 0) / 100000.0 if metadata.get("cost") else None
        )  # Convert from micro-units

        # Call successful can be boolean or string "success"/"failure"
        call_successful_raw = analysis.get("call_successful")
        if isinstance(call_successful_raw, str):
            call_successful = call_successful_raw.lower() == "success"
        else:
            call_successful = bool(call_successful_raw)

        transcript_summary = analysis.get("transcript_summary", "")

        # Extract timestamps
        start_time_unix = metadata.get("start_time_unix_secs")
        if start_time_unix:
            call_start_time = datetime.fromtimestamp(start_time_unix, tz=timezone.utc)
            call_end_time = datetime.fromtimestamp(
                start_time_unix + call_duration, tz=timezone.utc
            )
        else:
            call_start_time = call.call_start_time
            call_end_time = None

        # Determine status
        # Note: call_successful indicates whether the AI accomplished its goal,
        # NOT whether the call itself completed.
        # ElevenLabs conversation_status:
        # - "done": Call completed normally
        # - "failed": Call ended due to errors (e.g., not answered, LLM failure)
        #
        # We mark as FAILED if:
        # 1. conversation_status is "failed", OR
        # 2. call_successful is False (AI didn't accomplish goal)
        # 3. call_duration is 0 or very short (likely not answered)
        # 4. Voicemail was detected (termination_reason contains "voicemail")
        conversation_status = conversation_data.get("status", "unknown")

        # Check if call was actually answered (duration > 5 seconds as a threshold)
        call_not_answered = call_duration < 5

        # Check if voicemail was detected
        termination_reason = metadata.get("termination_reason", "")
        voicemail_detected = "voicemail" in termination_reason.lower()

        if conversation_status == "failed" or call_not_answered or call_successful is False or voicemail_detected:
            new_status = CallStatus.FAILED
            failure_reasons = []
            if conversation_status == "failed":
                failure_reasons.append(f"conversation_status={conversation_status}")
            if call_not_answered:
                failure_reasons.append(f"call_duration={call_duration}s")
            if call_successful is False:
                failure_reasons.append("call_successful=False")
            if voicemail_detected:
                failure_reasons.append(f"voicemail_detected ({termination_reason})")
            logger.info(
                f"[STATUS] Marking call as FAILED - reasons: {', '.join(failure_reasons)}"
            )
        elif conversation_status == "done":
            new_status = CallStatus.COMPLETED
        else:
            new_status = CallStatus.IN_PROGRESS

        logger.info(
            f"[METADATA] Extracted data - conversation_status: {conversation_status}, new_status: {new_status.value}, duration: {call_duration}s, cost: ${cost_value}, successful: {call_successful}, has_summary: {bool(transcript_summary)}"
        )

        # Track retry info for response
        retry_scheduled = False
        next_retry_at = None

        # Handle FAILED status - check if retry should be scheduled
        if new_status == CallStatus.FAILED:
            from models.call import RetryStatus
            from models.driver_sheduled_calls import DriverSheduledCalls

            # Check if retries are available
            if call.retry_count < call.max_retries:
                # Calculate retry time (10, 30, 60 minutes based on retry count)
                retry_delays = [10, 30, 60]
                delay_minutes = retry_delays[min(call.retry_count, len(retry_delays) - 1)]
                next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
                next_retry_count = call.retry_count + 1

                logger.info(
                    f"[RETRY] Scheduling retry {next_retry_count}/{call.max_retries} "
                    f"for call {call.call_sid} in {delay_minutes} minutes"
                )

                # Update call with retry status
                Call.mark_call_failed_with_retry(
                    call_sid=call.call_sid,
                    call_end_time=call_end_time,
                    next_retry_at=next_retry_at,
                    transcript_summary=transcript_summary,
                    call_duration_seconds=call_duration,
                    cost=cost_value,
                    call_successful=call_successful,
                    analysis_data=json.dumps(analysis),
                    metadata_json=json.dumps(metadata),
                )

                # Create scheduled call for retry using saved context from call
                driver_identifier = call.driver_name or call.driver_id

                if driver_identifier and (call.violations_json or call.reminders_json or call.custom_rules):
                    # Parse violations/reminders from JSON to comma-separated strings
                    violation_str = None
                    reminder_str = None

                    if call.violations_json:
                        try:
                            violations = json.loads(call.violations_json)
                            violation_str = ", ".join(
                                v.get("description", "") for v in violations if v.get("description")
                            )
                        except json.JSONDecodeError:
                            pass

                    if call.reminders_json:
                        try:
                            reminders = json.loads(call.reminders_json)
                            reminder_str = ", ".join(
                                r.get("description", "") for r in reminders if r.get("description")
                            )
                        except json.JSONDecodeError:
                            pass

                    DriverSheduledCalls.create_retry_schedule(
                        driver=driver_identifier,
                        violation=violation_str,
                        reminder=reminder_str,
                        custom_rule=call.custom_rules,
                        call_scheduled_date_time=next_retry_at,
                        retry_count=next_retry_count,
                        parent_call_sid=call.call_sid,
                    )
                    retry_scheduled = True
                    logger.info(
                        f"[RETRY] Created retry schedule for driver {driver_identifier}, "
                        f"parent_call_sid={call.call_sid}"
                    )
                else:
                    logger.warning(
                        f"[RETRY] Cannot schedule retry for call {call.call_sid}: "
                        f"missing driver_identifier or call context"
                    )
            else:
                # No more retries - mark as exhausted
                logger.info(
                    f"[RETRY] Call {call.call_sid} exhausted all retries "
                    f"({call.retry_count}/{call.max_retries})"
                )
                Call.mark_call_failed_exhausted(
                    call_sid=call.call_sid,
                    call_end_time=call_end_time,
                    transcript_summary=transcript_summary,
                    call_duration_seconds=call_duration,
                    cost=cost_value,
                    call_successful=call_successful,
                    analysis_data=json.dumps(analysis),
                    metadata_json=json.dumps(metadata),
                )
        else:
            # Not failed - just update metadata normally
            Call.update_conversation_metadata(
                call_sid=call.call_sid,
                status=new_status,
                call_end_time=call_end_time,
                transcript_summary=transcript_summary,
                call_duration_seconds=call_duration,
                cost=cost_value,
                call_successful=call_successful,
                analysis_data=json.dumps(analysis),
                metadata_json=json.dumps(metadata),
            )

        logger.info(
            f"[DB] Successfully updated Call {call.call_sid} with full metadata - status: {new_status.value}, "
            f"retry_scheduled: {retry_scheduled}, summary: {len(transcript_summary) if transcript_summary else 0} chars"
        )

        # Step 4: Store transcript
        transcript = conversation_data.get("transcript", [])
        transcriptions_added = 0

        # Check existing transcription count to avoid duplicates
        existing_count = CallTranscription.get_count_by_conversation_id(conversation_id)

        if existing_count > 0:
            logger.warning(
                f"Conversation {conversation_id} already has {existing_count} transcriptions. Skipping transcript storage."
            )
        else:
            for idx, message in enumerate(transcript):
                role = message.get("role", "unknown")
                # Handle null/None message text - skip empty messages
                text = message.get("message")
                if text is None or text == "":
                    logger.warning(
                        f"[TRANSCRIPT] Skipping empty message at index {idx} for conversation {conversation_id}"
                    )
                    continue

                message_time_secs = message.get("time_in_call_secs", 0)

                # Map role to speaker_type
                speaker_type = (
                    SpeakerType.AGENT if role.lower() == "agent" else SpeakerType.DRIVER
                )

                # Calculate message timestamp
                message_timestamp = (
                    call_start_time + timedelta(seconds=message_time_secs)
                    if call_start_time
                    else datetime.now(timezone.utc)
                )

                # Store transcription
                CallTranscription.create_transcription(
                    conversation_id=conversation_id,
                    speaker_type=speaker_type,
                    message_text=text,
                    timestamp=message_timestamp,
                    sequence_number=idx + 1,
                )
                transcriptions_added += 1

            logger.info(
                f"Stored {transcriptions_added} transcriptions for conversation {conversation_id}"
            )

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
            "should_stop_polling": conversation_status
            in ("done", "failed"),  # Frontend can use this to stop polling
            # Retry information
            "retry_scheduled": retry_scheduled,
            "next_retry_at": next_retry_at.isoformat() if next_retry_at else None,
            "retry_count": call.retry_count,
            "max_retries": call.max_retries,
            "conversation_data": conversation_data,
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
                detail=f"Conversation not found in ElevenLabs: {conversation_id}",
            )

        # Other errors remain 500
        logger.error(
            f"Error fetching conversation {conversation_id}: {err}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch conversation data: {error_message}",
        )
