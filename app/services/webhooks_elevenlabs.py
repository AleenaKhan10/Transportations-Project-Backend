"""
ElevenLabs webhook endpoints for receiving real-time call transcription data.

This module implements public webhook endpoints (no authentication) for:
- Receiving completed dialogue turns from ElevenLabs conversational AI
- Storing transcriptions with speaker attribution and sequencing
- Using call_sid (our identifier) for two-step lookup pattern

Refactored Workflow:
1. Webhook receives call_sid from ElevenLabs (echoed back from our create_outbound_call request)
2. Look up Call record by call_sid
3. Extract conversation_id from Call record
4. Save CallTranscription with conversation_id as foreign key

Error Handling Strategy:
- Return 400 Bad Request for validation errors or missing call_sid
- Return 400 Bad Request if Call exists but has no conversation_id
- Return 500 Internal Server Error for database/unexpected errors
- Never return 200 OK on failure (allows ElevenLabs to retry)
"""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import logging
from sqlalchemy.exc import OperationalError, DisconnectionError

from helpers.transcription_helpers import save_transcription
from logic.auth.service import make_timezone_aware

logger = logging.getLogger(__name__)

# Router with no authentication (public endpoint for performance)
router = APIRouter(prefix="/webhooks/elevenlabs", tags=["webhooks"])


class TranscriptionWebhookRequest(BaseModel):
    """
    Request model for ElevenLabs transcription webhook.

    Fields:
        call_sid: Our generated call identifier (format: EL_{driverId}_{timestamp})
        speaker: Speaker attribution - 'agent' or 'user' (required)
        message: The dialogue message text (required)

    Note:
        - ElevenLabs echoes back the call_sid we provide in create_outbound_call request
        - Timestamp is automatically generated server-side when webhook is received
        - This allows us to track calls from initiation through completion
    """
    call_sid: str = Field(..., min_length=1, description="Generated call identifier (format: EL_{driverId}_{timestamp})")
    speaker: str = Field(..., description="Speaker attribution - 'agent' or 'user'")
    message: str = Field(..., min_length=1, description="The dialogue message text")

    @validator('speaker')
    def validate_speaker(cls, v):
        """Validate that speaker is either 'agent' or 'user'."""
        if v not in ['agent', 'user']:
            raise ValueError("speaker must be 'agent' or 'user'")
        return v


class TranscriptionWebhookSuccessResponse(BaseModel):
    """
    Success response model for transcription webhook.

    Fields:
        status: Always 'success' for successful operations
        message: Human-readable success message
        transcription_id: Database ID of created transcription
        sequence_number: Sequence number of this transcription in the conversation
    """
    status: str = "success"
    message: str
    transcription_id: int
    sequence_number: int


class TranscriptionWebhookErrorResponse(BaseModel):
    """
    Error response model for transcription webhook.

    Fields:
        status: Always 'error' for failed operations
        message: Human-readable error message
        details: Optional additional error details
    """
    status: str = "error"
    message: str
    details: Optional[str] = None


@router.post(
    "/transcription",
    status_code=status.HTTP_201_CREATED,
    response_model=TranscriptionWebhookSuccessResponse,
    responses={
        201: {
            "description": "Transcription saved successfully",
            "model": TranscriptionWebhookSuccessResponse
        },
        400: {
            "description": "Invalid request data or call_sid not found",
            "model": TranscriptionWebhookErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": TranscriptionWebhookErrorResponse
        }
    }
)
async def receive_transcription(request: TranscriptionWebhookRequest):
    """
    Receive and store real-time call transcription data from ElevenLabs.

    This endpoint is called by ElevenLabs for each completed dialogue turn.
    It handles:
    - Two-step lookup: call_sid -> Call -> conversation_id
    - Speaker mapping from ElevenLabs format to internal format
    - Sequence number generation
    - Transcription storage
    - Automatic timestamp generation (server-side)

    Refactored Flow:
    1. Receive call_sid from ElevenLabs webhook
    2. Auto-generate timestamp (server-side UTC)
    3. Look up Call record by call_sid (may fail if Call not found)
    4. Extract conversation_id from Call (may fail if NULL)
    5. Save CallTranscription with conversation_id FK
    6. Return success with transcription_id and sequence_number

    ElevenLabs guarantees sequential webhook calls per conversation,
    so no concurrency control is needed.

    Args:
        request: Validated webhook request with call_sid, speaker, message

    Returns:
        201 Created: TranscriptionWebhookSuccessResponse with transcription_id and sequence_number
        400 Bad Request: Invalid speaker or call_sid not found/incomplete
        500 Internal Server Error: Database connection failure or unexpected error

    Note:
        This is a public endpoint with no authentication (optimized for performance).
        Errors never return 200 OK to allow ElevenLabs to retry failed saves.
        Timestamp is automatically generated server-side when webhook is received.
    """
    logger.info("=" * 100)
    logger.info(f"ElevenLabs Transcription Webhook - Received request for call_sid: {request.call_sid}")
    logger.info(f"Speaker: {request.speaker} | Message length: {len(request.message)} chars")
    logger.info("=" * 100)

    try:
        # Auto-generate timestamp (server-side UTC)
        from datetime import timezone as tz
        timestamp_dt = datetime.now(tz.utc)
        logger.info(f"Auto-generated timestamp: {timestamp_dt.isoformat()}")

        # Call save_transcription orchestration function (now uses call_sid)
        try:
            transcription_id, sequence_number = save_transcription(
                call_sid=request.call_sid,
                speaker=request.speaker,
                message=request.message,
                timestamp=timestamp_dt
            )
        except ValueError as lookup_err:
            # Call record not found or has NULL conversation_id
            logger.error(f"Call lookup failed for call_sid {request.call_sid}: {str(lookup_err)}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "message": f"Call record not found or incomplete for call_sid: {request.call_sid}",
                    "details": str(lookup_err)
                }
            )

        logger.info(f"Transcription saved successfully - ID: {transcription_id}, Sequence: {sequence_number}")
        logger.info("=" * 100)

        return TranscriptionWebhookSuccessResponse(
            status="success",
            message=f"Transcription saved successfully for call_sid {request.call_sid}",
            transcription_id=transcription_id,
            sequence_number=sequence_number
        )

    except ValueError as e:
        # Invalid speaker value or other validation error
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "error",
                "message": "Invalid request data",
                "details": str(e)
            }
        )

    except (OperationalError, DisconnectionError) as e:
        # Database connection failure
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Database connection error. Please retry.",
                "details": "Database temporarily unavailable"
            }
        )

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error processing transcription: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Internal server error. Please retry.",
                "details": str(e)
            }
        )
