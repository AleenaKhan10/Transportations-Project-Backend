"""
Call management endpoints for ElevenLabs conversational AI calls.

This module provides endpoints for:
- Fetching active/completed calls
- Retrieving call details
- Getting real-time transcripts
- Fetching conversation summaries
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from models.call import Call, CallStatus
from models.call_transcription import CallTranscription, SpeakerType
from helpers import logger

router = APIRouter(prefix="/calls", tags=["calls"])


# Response Models
class TranscriptMessage(BaseModel):
    """Single transcript message."""

    role: str  # "agent" or "driver"
    text: str
    timestamp: str
    sequence_number: int


class CallResponse(BaseModel):
    """Call response model."""

    call_sid: str
    conversation_id: Optional[str]
    driver_id: Optional[str]
    trip_id: Optional[str]
    status: str
    call_start_time: str
    call_end_time: Optional[str]
    duration_seconds: Optional[int]
    transcript_summary: Optional[str]
    call_duration_seconds: Optional[int]
    cost: Optional[float]
    call_successful: Optional[bool]
    created_at: str
    updated_at: str


class CallWithTranscriptResponse(BaseModel):
    """Call response with transcript."""

    call_sid: str
    conversation_id: Optional[str]
    driver_id: Optional[str]
    status: str
    call_start_time: str
    call_end_time: Optional[str]
    duration_seconds: Optional[int]
    transcript_summary: Optional[str]
    call_duration_seconds: Optional[int]
    cost: Optional[float]
    call_successful: Optional[bool]
    transcript: List[TranscriptMessage]
    transcript_count: int


# Endpoints


@router.get(
    "",
    response_model=List[CallResponse],
    summary="List all calls with optional filters",
    description="""
    Retrieve a list of calls with optional filtering.

    **Query Parameters:**
    - status: Filter by call status (in_progress, completed, failed)
    - driver_id: Filter by driver ID
    - limit: Maximum number of results (default: 100)

    **Response:**
    List of call records with basic metadata (no transcripts)
    """,
)
async def list_calls(
    status: Optional[str] = Query(
        None, description="Filter by status: in_progress, completed, failed"
    ),
    driver_id: Optional[str] = Query(None, description="Filter by driver ID"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
):
    """
    List all calls with optional filtering.
    Use this endpoint to get active calls for the live view.
    """
    try:
        from sqlmodel import Session, select, or_
        from db.database import engine

        with Session(engine) as session:
            # Build query
            stmt = select(Call).order_by(Call.created_at.desc()).limit(limit)

            # Apply filters
            if status:
                stmt = stmt.where(Call.status == status)
            if driver_id:
                stmt = stmt.where(Call.driver_id == driver_id)

            calls = session.exec(stmt).all()

            # Convert to response model
            result = []
            for call in calls:
                duration = None
                if call.call_start_time and call.call_end_time:
                    duration = int(
                        (call.call_end_time - call.call_start_time).total_seconds()
                    )

                result.append(
                    CallResponse(
                        call_sid=call.call_sid,
                        conversation_id=call.conversation_id,
                        driver_id=call.driver_id,
                        status=call.status.value,
                        call_start_time=call.call_start_time.isoformat(),
                        call_end_time=(
                            call.call_end_time.isoformat()
                            if call.call_end_time
                            else None
                        ),
                        duration_seconds=duration,
                        transcript_summary=call.transcript_summary,
                        call_duration_seconds=call.call_duration_seconds,
                        cost=call.cost,
                        call_successful=call.call_successful,
                        created_at=call.created_at.isoformat(),
                        updated_at=call.updated_at.isoformat(),
                        trip_id=call.trip_id,
                    )
                )
            # TEST

            return result

    except Exception as err:
        logger.error(f"Error listing calls: {str(err)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list calls: {str(err)}")


@router.get(
    "/active",
    response_model=List[CallResponse],
    summary="Get all active (in-progress) calls",
    description="""
    Retrieve all calls that are currently in progress.

    **Use Case:** Live calls view in frontend

    **Response:**
    List of active call records
    """,
)
async def get_active_calls():
    """
    Get all active calls.
    Shorthand for /calls?status=in_progress
    """
    try:
        from sqlmodel import Session, select
        from db.database import engine

        with Session(engine) as session:
            stmt = (
                select(Call)
                .where(Call.status == CallStatus.IN_PROGRESS)
                .order_by(Call.call_start_time.desc())
            )
            calls = session.exec(stmt).all()

            result = []
            for call in calls:
                duration = None
                if call.call_start_time:
                    duration = int(
                        (
                            datetime.utcnow()
                            - call.call_start_time.replace(tzinfo=None)
                        ).total_seconds()
                    )

                result.append(
                    CallResponse(
                        call_sid=call.call_sid,
                        conversation_id=call.conversation_id,
                        driver_id=call.driver_id,
                        status=call.status.value,
                        call_start_time=call.call_start_time.isoformat(),
                        call_end_time=(
                            call.call_end_time.isoformat()
                            if call.call_end_time
                            else None
                        ),
                        duration_seconds=duration,
                        transcript_summary=call.transcript_summary,
                        call_duration_seconds=call.call_duration_seconds,
                        cost=call.cost,
                        call_successful=call.call_successful,
                        created_at=call.created_at.isoformat(),
                        updated_at=call.updated_at.isoformat(),
                    )
                )

            return result

    except Exception as err:
        logger.error(f"Error fetching active calls: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch active calls: {str(err)}"
        )


@router.get(
    "/{call_sid}",
    response_model=CallResponse,
    summary="Get call details by call_sid",
    description="""
    Retrieve detailed information about a specific call.

    **URL Parameters:**
    - call_sid: The call session identifier

    **Response:**
    Call record with metadata (no transcript - use /transcript endpoint)
    """,
)
async def get_call_details(call_sid: str):
    """
    Get details for a specific call.
    """
    try:
        call = Call.get_by_call_sid(call_sid)

        if not call:
            raise HTTPException(status_code=404, detail=f"Call {call_sid} not found")

        duration = None
        if call.call_start_time and call.call_end_time:
            duration = int((call.call_end_time - call.call_start_time).total_seconds())

        return CallResponse(
            call_sid=call.call_sid,
            conversation_id=call.conversation_id,
            driver_id=call.driver_id,
            status=call.status.value,
            call_start_time=call.call_start_time.isoformat(),
            call_end_time=(
                call.call_end_time.isoformat() if call.call_end_time else None
            ),
            duration_seconds=duration,
            transcript_summary=call.transcript_summary,
            call_duration_seconds=call.call_duration_seconds,
            cost=call.cost,
            call_successful=call.call_successful,
            created_at=call.created_at.isoformat(),
            updated_at=call.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error fetching call {call_sid}: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch call details: {str(err)}"
        )


@router.get(
    "/{call_sid}/transcript",
    response_model=List[TranscriptMessage],
    summary="Get real-time transcript for a call",
    description="""
    Retrieve the transcript for a specific call.

    **URL Parameters:**
    - call_sid: The call session identifier

    **Query Parameters:**
    - limit: Maximum number of messages to return (default: all)

    **Response:**
    List of transcript messages ordered by sequence number

    **Use Case:**
    - Poll this endpoint every 2-3 seconds for real-time updates
    - Display transcript in live calls view
    """,
)
async def get_call_transcript(
    call_sid: str,
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Limit number of messages"
    ),
):
    """
    Get transcript for a call.
    Returns all transcript messages ordered by sequence.
    """
    try:
        # Get call to find conversation_id
        call = Call.get_by_call_sid(call_sid)

        if not call:
            raise HTTPException(status_code=404, detail=f"Call {call_sid} not found")

        if not call.conversation_id:
            # Call exists but no conversation_id yet (API call may have failed)
            return []

        # Fetch transcriptions
        transcriptions = CallTranscription.get_by_conversation_id(
            conversation_id=call.conversation_id, limit=limit
        )

        # Convert to response model
        result = []
        for trans in transcriptions:
            result.append(
                TranscriptMessage(
                    role=(
                        "agent" if trans.speaker_type == SpeakerType.AGENT else "driver"
                    ),
                    text=trans.message_text,
                    timestamp=trans.timestamp.isoformat(),
                    sequence_number=trans.sequence_number,
                )
            )

        return result

    except HTTPException:
        raise
    except Exception as err:
        logger.error(
            f"Error fetching transcript for {call_sid}: {str(err)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch transcript: {str(err)}"
        )


@router.get(
    "/{call_sid}/full",
    response_model=CallWithTranscriptResponse,
    summary="Get call with full transcript",
    description="""
    Retrieve call details with complete transcript in a single request.

    **URL Parameters:**
    - call_sid: The call session identifier

    **Response:**
    Call record with embedded transcript

    **Use Case:**
    - Fetch complete call data for display
    - Avoid making separate requests for call + transcript
    """,
)
async def get_call_with_transcript(call_sid: str):
    """
    Get call details with full transcript.
    Convenience endpoint that combines /calls/{call_sid} and /calls/{call_sid}/transcript
    """
    try:
        call = Call.get_by_call_sid(call_sid)

        if not call:
            raise HTTPException(status_code=404, detail=f"Call {call_sid} not found")

        duration = None
        if call.call_start_time and call.call_end_time:
            duration = int((call.call_end_time - call.call_start_time).total_seconds())

        # Fetch transcript if conversation_id exists
        transcript_messages = []
        if call.conversation_id:
            transcriptions = CallTranscription.get_by_conversation_id(
                call.conversation_id
            )
            for trans in transcriptions:
                transcript_messages.append(
                    TranscriptMessage(
                        role=(
                            "agent"
                            if trans.speaker_type == SpeakerType.AGENT
                            else "driver"
                        ),
                        text=trans.message_text,
                        timestamp=trans.timestamp.isoformat(),
                        sequence_number=trans.sequence_number,
                    )
                )

        return CallWithTranscriptResponse(
            call_sid=call.call_sid,
            conversation_id=call.conversation_id,
            driver_id=call.driver_id,
            status=call.status.value,
            call_start_time=call.call_start_time.isoformat(),
            call_end_time=(
                call.call_end_time.isoformat() if call.call_end_time else None
            ),
            duration_seconds=duration,
            transcript_summary=call.transcript_summary,
            call_duration_seconds=call.call_duration_seconds,
            cost=call.cost,
            call_successful=call.call_successful,
            transcript=transcript_messages,
            transcript_count=len(transcript_messages),
        )

    except HTTPException:
        raise
    except Exception as err:
        logger.error(
            f"Error fetching call with transcript {call_sid}: {str(err)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch call with transcript: {str(err)}"
        )
