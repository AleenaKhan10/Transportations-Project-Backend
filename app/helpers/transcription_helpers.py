"""
Helper functions for call transcription webhook business logic.

This module provides business logic functions for:
- Driver lookup from existing Call records using call_sid
- Two-step lookup pattern: call_sid -> Call -> conversation_id
- Sequence number generation for transcriptions
- Speaker type mapping from ElevenLabs format to internal format
- Main orchestration for saving transcriptions

All database operations use @db_retry decorator for resilience.

Refactored Workflow:
1. Webhook receives call_sid (our generated identifier)
2. Look up Call record by call_sid
3. Extract conversation_id from Call record
4. Use conversation_id to save CallTranscription
"""

from typing import Optional, Tuple
from datetime import datetime
import logging
from sqlmodel import Session, select
from db.database import engine
from db.retry import db_retry
from models.call import Call, CallStatus
from models.call_transcription import CallTranscription, SpeakerType
from logic.auth.service import make_timezone_aware

logger = logging.getLogger(__name__)


@db_retry(max_retries=3)
def lookup_driver_id_by_call_sid(call_sid: str) -> Optional[int]:
    """
    Look up driver_id for a given call_sid from Call records.

    This function implements the first step of the lookup chain:
    call_sid -> Call -> driver_id

    Args:
        call_sid: Generated call identifier (format: EL_{driverId}_{timestamp})

    Returns:
        driver_id if found, None otherwise

    Note:
        Logs a warning if driver_id is not found or is NULL.
    """
    with Session(engine) as session:
        # Query Call table for call_sid
        stmt = select(Call).where(Call.call_sid == call_sid)
        call = session.exec(stmt).first()

        if call and call.driver_id is not None:
            logger.info(f"Driver lookup successful - call_sid: {call_sid}, driver_id: {call.driver_id}")
            return call.driver_id
        else:
            logger.warning(f"Driver lookup failed - call_sid: {call_sid} not found or has null driver_id")
            return None


@db_retry(max_retries=3)
def get_conversation_id_from_call_sid(call_sid: str) -> Optional[str]:
    """
    Get conversation_id for a given call_sid.

    This function implements the two-step lookup pattern:
    call_sid -> Call -> conversation_id

    This is the critical lookup used by webhooks to translate from call_sid
    (sent by ElevenLabs in webhook) to conversation_id (used for transcriptions).

    Args:
        call_sid: Generated call identifier

    Returns:
        conversation_id if found, None otherwise

    Raises:
        ValueError: If Call record exists but has no conversation_id
            (indicates ElevenLabs call may have failed or not yet completed)

    Note:
        Returns None if Call record not found (should not happen in normal flow).
        Raises ValueError if Call exists but conversation_id is NULL
        (indicates API call failed or hasn't completed yet).
    """
    with Session(engine) as session:
        stmt = select(Call).where(Call.call_sid == call_sid)
        call = session.exec(stmt).first()

        if not call:
            logger.error(f"Call record not found for call_sid: {call_sid}")
            return None

        if not call.conversation_id:
            logger.error(f"Call record found but conversation_id is NULL for call_sid: {call_sid}")
            raise ValueError(f"Call {call_sid} has no conversation_id - ElevenLabs call may have failed")

        logger.info(f"Conversation ID lookup successful - call_sid: {call_sid}, conversation_id: {call.conversation_id}")
        return call.conversation_id


@db_retry(max_retries=3)
def generate_sequence_number(call_sid: str) -> int:
    """
    Generate the next sequence number for a transcription.

    Uses two-step lookup: call_sid -> conversation_id -> count transcriptions.

    Args:
        call_sid: Generated call identifier

    Returns:
        Next sequence number (count + 1, starting at 1 for first transcription)

    Raises:
        ValueError: If call_sid not found or has no conversation_id
    """
    # Step 1: Get conversation_id from call_sid (two-step lookup)
    conversation_id = get_conversation_id_from_call_sid(call_sid)
    if not conversation_id:
        raise ValueError(f"Cannot generate sequence number - no conversation_id for call_sid: {call_sid}")

    # Step 2: Count existing transcriptions for this conversation
    count = CallTranscription.get_count_by_conversation_id(conversation_id)
    sequence_number = count + 1
    logger.debug(f"Generated sequence number {sequence_number} for call_sid {call_sid} (conversation {conversation_id})")
    return sequence_number


def map_speaker_to_internal(speaker: str) -> SpeakerType:
    """
    Map ElevenLabs speaker format to internal SpeakerType enum.

    Mapping rules:
    - 'user' -> SpeakerType.DRIVER (ElevenLabs calls the driver 'user')
    - 'agent' -> SpeakerType.AGENT (ElevenLabs agent is our agent)

    Args:
        speaker: ElevenLabs speaker value ('user' or 'agent')

    Returns:
        SpeakerType enum value

    Raises:
        ValueError: If speaker is not 'user' or 'agent'
    """
    if speaker == "user":
        return SpeakerType.DRIVER
    elif speaker == "agent":
        return SpeakerType.AGENT
    else:
        raise ValueError(f"Invalid speaker value: {speaker}. Expected 'user' or 'agent'.")


@db_retry(max_retries=3)
def save_transcription(
    call_sid: str,  # CHANGED from conversation_id
    speaker: str,
    message: str,
    timestamp: datetime
) -> Tuple[int, int]:
    """
    Orchestrate the complete transcription save workflow.

    This function coordinates all steps using the two-step lookup pattern:
    1. Look up conversation_id from call_sid (two-step lookup)
    2. Map speaker to internal format
    3. Generate sequence number (using call_sid)
    4. Create CallTranscription record (using conversation_id as FK)
    5. Return (transcription_id, sequence_number)

    Refactored Workflow:
    - Webhook receives call_sid from ElevenLabs
    - This function translates call_sid -> conversation_id
    - CallTranscription is saved with conversation_id (FK to Call)
    - This maintains referential integrity without duplicating data

    Args:
        call_sid: Generated call identifier (from webhook)
        speaker: ElevenLabs speaker value ('user' or 'agent')
        message: The dialogue message text
        timestamp: Timezone-aware UTC datetime when dialogue occurred

    Returns:
        Tuple of (transcription_id, sequence_number)

    Raises:
        ValueError: If speaker is invalid, call_sid not found, or conversation_id is NULL
        Database exceptions: If database operations fail after retries

    Note:
        All database operations use @db_retry for resilience.
        Timezone handling uses make_timezone_aware for consistency.
    """
    logger.info(f"Starting transcription save - call_sid: {call_sid}, speaker: {speaker}")

    # Step 1: Get conversation_id from call_sid (two-step lookup)
    aware_timestamp = make_timezone_aware(timestamp)
    conversation_id = get_conversation_id_from_call_sid(call_sid)

    if not conversation_id:
        raise ValueError(f"Cannot save transcription - Call record not found for call_sid: {call_sid}")

    logger.info(f"Resolved conversation_id: {conversation_id} for call_sid: {call_sid}")

    # Step 2: Map speaker to internal format
    speaker_type = map_speaker_to_internal(speaker)

    # Step 3: Generate sequence number (uses call_sid internally)
    sequence_number = generate_sequence_number(call_sid)

    # Step 4: Create CallTranscription record (uses conversation_id as FK)
    transcription = CallTranscription.create_transcription(
        conversation_id=conversation_id,  # Foreign key to Call.conversation_id
        speaker_type=speaker_type,
        message_text=message,
        timestamp=aware_timestamp,
        sequence_number=sequence_number
    )

    logger.info(
        f"Transcription saved successfully - ID: {transcription.id}, "
        f"sequence: {sequence_number}, speaker: {speaker_type.value}, "
        f"call_sid: {call_sid}, conversation_id: {conversation_id}"
    )

    # Step 5: Return results
    return (transcription.id, sequence_number)
