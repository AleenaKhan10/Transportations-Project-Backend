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

from fastapi import APIRouter, Request, status, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Union, Dict, Any, List
from datetime import datetime
import logging
import json
import hmac
import hashlib
import os
import time
from sqlalchemy.exc import OperationalError, DisconnectionError

from helpers.transcription_helpers import save_transcription
from logic.auth.service import make_timezone_aware
from config import settings

logger = logging.getLogger(__name__)

# Router with no authentication (public endpoint for performance)
# NOTE: We now use HMAC signature validation for security
router = APIRouter(prefix="/webhooks/elevenlabs", tags=["webhooks"])


async def validate_elevenlabs_signature(request: Request):
    """
    Validate the ElevenLabs HMAC signature header.
    """
    signature_header = request.headers.get("elevenlabs-signature")
    if not signature_header:
        logger.warning("Missing ElevenLabs-Signature header")
        raise HTTPException(status_code=401, detail="Missing signature header")

    secret = settings.ELEVENLABS_WEBHOOK_SECRET
    if not secret:
        logger.error("ELEVENLABS_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        parts = signature_header.split(",")
        timestamp_part = next((p for p in parts if p.startswith("t=")), None)
        signature_part = next((p for p in parts if p.startswith("v0=")), None)

        if not timestamp_part or not signature_part:
             raise ValueError("Invalid header format")

        timestamp = timestamp_part[2:]
        signature = signature_part[3:]

        # Validate timestamp (prevent replay attacks > 30 mins)
        request_time = int(timestamp)
        current_time = int(time.time())
        if current_time - request_time > 1800: # 30 minutes
             raise ValueError("Request expired")

        # Validate signature
        body = await request.body()
        payload = f"{timestamp}.{body.decode('utf-8')}"
        
        mac = hmac.new(
            key=secret.encode("utf-8"),
            msg=payload.encode("utf-8"),
            digestmod=hashlib.sha256
        )
        expected_signature = mac.hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
             raise ValueError("Invalid signature")

    except Exception as e:
        logger.warning(f"Signature validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    return True


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

        # Broadcast transcription to subscribed WebSocket clients
        try:
            from services.websocket_manager import websocket_manager
            await websocket_manager.broadcast_transcription(
                call_sid=request.call_sid,
                transcription_id=transcription_id,
                sequence_number=sequence_number,
                speaker=request.speaker,
                message=request.message,
                timestamp=timestamp_dt
            )
        except Exception as e:
            # Log warning but don't fail the webhook
            logger.warning(f"WebSocket broadcast failed (non-critical): {str(e)}")
            # Webhook still succeeds even if broadcast fails
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


# ============================================================================
# Post-Call Webhook Models
# ============================================================================


class TranscriptTurn(BaseModel):
    """
    Model for a single dialogue turn in the transcript.

    Fields:
        role: Speaker role - 'agent' or 'user'
        message: The dialogue message text
        time_in_call_secs: Timestamp of message in seconds from call start
    """
    role: str
    message: str
    time_in_call_secs: float


class TranscriptionMetadata(BaseModel):
    """Metadata for successful transcription webhooks."""
    start_time_unix_secs: int
    call_duration_secs: int
    cost: float
    deletion_settings: Optional[Dict[str, Any]] = None
    feedback: Optional[Dict[str, Any]] = None
    authorization_method: Optional[str] = None
    charging: Optional[Dict[str, Any]] = None
    termination_reason: Optional[str] = None


class FailureMetadataBody(BaseModel):
    """Body of failure metadata (Twilio or SIP details)."""
    # Common fields or flexible dict
    sip_status_code: Optional[int] = None
    error_reason: Optional[str] = None
    call_sid: Optional[str] = None
    CallSid: Optional[str] = None
    CallStatus: Optional[str] = None


class FailureMetadata(BaseModel):
    """Metadata for call initiation failure."""
    type: str  # "twilio" or "sip"
    body: Dict[str, Any]


class PostCallAnalysis(BaseModel):
    """
    Analysis results for a completed call from ElevenLabs.

    Fields:
        call_successful: Boolean indicating if call was successful
        transcript_summary: Text summary of the conversation
        evaluation_criteria_results: Optional dictionary of evaluation criteria results
        data_collection_results: Optional dictionary of data collection results
    """
    call_successful: Optional[bool] = None
    transcript_summary: Optional[str] = None
    evaluation_criteria_results: Optional[Dict[str, Any]] = None
    data_collection_results: Optional[Dict[str, Any]] = None


class PostCallData(BaseModel):
    """
    Data payload for post-call webhook from ElevenLabs.
    """
    agent_id: str
    conversation_id: str = Field(..., min_length=1, description="ElevenLabs conversation identifier")
    status: Optional[str] = None # "done" for success, may be missing for failure? Doc says status is in data for transcription.
    
    # Transcription specific
    transcript: Optional[list[TranscriptTurn]] = None
    analysis: Optional[PostCallAnalysis] = None
    conversation_initiation_client_data: Optional[Dict[str, Any]] = None
    
    # Failure specific
    failure_reason: Optional[str] = None
    
    # Polymorphic metadata
    metadata: Optional[Union[TranscriptionMetadata, FailureMetadata]] = None
    
    # Future compatibility
    has_audio: Optional[bool] = None
    has_user_audio: Optional[bool] = None
    has_response_audio: Optional[bool] = None

    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        """Validate that conversation_id is not empty."""
        if not v or not v.strip():
            raise ValueError("conversation_id must not be empty")
        return v.strip()


class PostCallWebhookRequest(BaseModel):
    """
    Request model for ElevenLabs post-call webhook.

    Fields:
        type: Webhook type - 'post_call_transcription' or 'call_initiation_failure'
        event_timestamp: Unix timestamp when event occurred
        data: Webhook payload data

    Note:
        - ElevenLabs sends this webhook when a call completes or fails to initiate
        - Timestamp is Unix epoch seconds
        - Data structure varies based on webhook type
    """
    type: str = Field(..., description="Webhook type")
    event_timestamp: int = Field(..., description="Unix timestamp when event occurred")
    data: PostCallData

    @validator('type')
    def validate_type(cls, v):
        """Validate that webhook type is supported."""
        valid_types = ['post_call_transcription', 'call_initiation_failure', 'post_call_audio']
        if v not in valid_types:
            raise ValueError(f"type must be one of {valid_types}, got '{v}'")
        return v


class PostCallSuccessResponse(BaseModel):
    """
    Success response model for post-call webhook.

    Fields:
        status: Always 'success' for successful operations
        message: Human-readable success message
        conversation_id: ElevenLabs conversation identifier
        call_sid: Our generated call identifier
        call_status: Final call status (completed or failed)
    """
    status: str = "success"
    message: str
    conversation_id: str
    call_sid: str
    call_status: str


class PostCallErrorResponse(BaseModel):
    """
    Error response model for post-call webhook.

    Fields:
        status: Always 'error' for failed operations
        message: Human-readable error message
        details: Optional additional error details
    """
    status: str = "error"
    message: str
    details: Optional[str] = None


# ============================================================================
# Post-Call Webhook Endpoint
# ============================================================================


@router.post(
    "/post-call",
    status_code=status.HTTP_200_OK,
    response_model=PostCallSuccessResponse,
    responses={
        200: {
            "description": "Call completion data processed successfully",
            "model": PostCallSuccessResponse
        },
        400: {
            "description": "Invalid request data or conversation_id not found",
            "model": PostCallErrorResponse
        },
        404: {
            "description": "Call record not found for conversation_id",
            "model": PostCallErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": PostCallErrorResponse
        }
    }
)
async def receive_post_call(
    request: PostCallWebhookRequest,
    _auth: bool = Depends(validate_elevenlabs_signature)
):
    """
    Receive and process post-call completion webhook from ElevenLabs.

    This endpoint is called by ElevenLabs when a call completes or fails to initiate.
    It handles:
    - Webhook type detection and routing (post_call_transcription or call_initiation_failure)
    - Conversation ID lookup and validation
    - Metadata extraction and parsing from webhook payload
    - Call status update to COMPLETED with post-call metadata
    - Structured logging throughout processing

    Processing Flow:
    1. Detect webhook type from request.type field
    2. Extract conversation_id from request.data.conversation_id
    3. Look up Call record by conversation_id
    4. Route to appropriate handler based on webhook type:
       - post_call_transcription: Extract metadata and analysis, update Call with completion data
       - call_initiation_failure: Update Call status to FAILED
    5. Convert event_timestamp to timezone-aware UTC datetime
    6. Parse and serialize analysis and metadata to JSON strings
    7. Call Call.update_post_call_data() with all extracted fields
    8. Return success response with conversation_id, call_sid, and status

    Args:
        request: Validated post-call webhook request with type, timestamp, and data

    Returns:
        200 OK: PostCallSuccessResponse with conversation_id, call_sid, call_status
        400 Bad Request: Invalid payload structure or missing conversation_id
        404 Not Found: Call record not found for conversation_id
        500 Internal Server Error: Database connection failure or JSON parsing error

    Note:
        This is a public endpoint with no authentication (ElevenLabs webhook).
        Errors never return 200 OK to enable ElevenLabs retry mechanism.
        Supports both successful completion and failure webhooks.
    """
    logger.info("=" * 100)
    logger.info(f"ElevenLabs Post-Call Webhook - Received request")
    logger.info(f"Webhook Type: {request.type} | Event Timestamp: {request.event_timestamp}")
    logger.info(f"Conversation ID: {request.data.conversation_id} | Status: {request.data.status}")
    logger.info("=" * 100)

    try:
        # Extract conversation_id for Call lookup
        conversation_id = request.data.conversation_id
        if not conversation_id:
            logger.error("Missing conversation_id in webhook payload")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "message": "Invalid webhook payload",
                    "details": "Missing required field: conversation_id"
                }
            )

        # Look up Call record by conversation_id
        from models.call import Call
        call = Call.get_by_conversation_id(conversation_id)
        if not call:
            logger.error(f"Call not found for conversation_id: {conversation_id}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": "error",
                    "message": f"Call not found for conversation_id: {conversation_id}",
                    "details": "No Call record exists with this conversation_id"
                }
            )

        logger.info(f"Call found - ID: {call.id}, call_sid: {call.call_sid}, current status: {call.status}")

        # Route based on webhook type
        if request.type == "call_initiation_failure":
            # Handle call initiation failure
            logger.info("Processing call_initiation_failure webhook")

            # Convert event_timestamp to timezone-aware UTC datetime
            from datetime import timezone as tz
            call_end_time = datetime.fromtimestamp(request.event_timestamp, tz=tz.utc)
            call_end_time = make_timezone_aware(call_end_time)

            # Update Call status to FAILED
            from models.call import CallStatus
            updated_call = Call.update_status(
                conversation_id=conversation_id,
                status=CallStatus.FAILED,
                call_end_time=call_end_time
            )

            if not updated_call:
                logger.error(f"Failed to update Call status for conversation_id: {conversation_id}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": "error",
                        "message": "Failed to update Call record",
                        "details": "Database update operation failed"
                    }
                )

            logger.info(f"Call status updated to FAILED - Reason: {request.data.failure_reason}")
            logger.info("=" * 100)

            return PostCallSuccessResponse(
                status="success",
                message="Call failure data processed successfully",
                conversation_id=conversation_id,
                call_sid=call.call_sid,
                call_status="failed"
            )

        elif request.type == "post_call_transcription":
            # Handle successful call completion
            logger.info("Processing post_call_transcription webhook")

            # Convert event_timestamp to timezone-aware UTC datetime for call_end_time
            from datetime import timezone as tz
            call_end_time = datetime.fromtimestamp(request.event_timestamp, tz=tz.utc)
            call_end_time = make_timezone_aware(call_end_time)
            logger.info(f"Call end time: {call_end_time.isoformat()}")

            # Extract metadata fields (with None checks)
            call_duration_seconds = None
            cost = None
            if request.data.metadata and isinstance(request.data.metadata, TranscriptionMetadata):
                call_duration_seconds = request.data.metadata.call_duration_secs
                cost = request.data.metadata.cost
                logger.info(f"Metadata - Duration: {call_duration_seconds}s, Cost: ${cost}")

            # Extract analysis fields (with None checks)
            call_successful = None
            transcript_summary = None
            if request.data.analysis:
                call_successful = request.data.analysis.call_successful
                transcript_summary = request.data.analysis.transcript_summary
                logger.info(f"Analysis - Successful: {call_successful}, Summary length: {len(transcript_summary) if transcript_summary else 0} chars")

            # Serialize analysis_data and metadata_json to JSON strings
            analysis_data = None
            metadata_json = None

            if request.data.analysis:
                try:
                    analysis_data = json.dumps(request.data.analysis.dict())
                    logger.info(f"Serialized analysis_data: {len(analysis_data)} chars")
                except Exception as e:
                    logger.warning(f"Failed to serialize analysis_data: {str(e)}")

            if request.data.metadata:
                try:
                    metadata_json = json.dumps(request.data.metadata.dict())
                    logger.info(f"Serialized metadata_json: {len(metadata_json)} chars")
                except Exception as e:
                    logger.warning(f"Failed to serialize metadata_json: {str(e)}")

            # Update Call with post-call data
            logger.info(f"Updating Call with post-call data for conversation_id: {conversation_id}")
            updated_call = Call.update_post_call_data(
                conversation_id=conversation_id,
                call_end_time=call_end_time,
                transcript_summary=transcript_summary,
                call_duration_seconds=call_duration_seconds,
                cost=cost,
                call_successful=call_successful,
                analysis_data=analysis_data,
                metadata_json=metadata_json
            )

            if not updated_call:
                logger.error(f"Failed to update Call with post-call data for conversation_id: {conversation_id}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "status": "error",
                        "message": "Failed to update Call record with post-call data",
                        "details": "Database update operation failed"
                    }
                )

            logger.info(f"Call updated successfully - Status: COMPLETED, ID: {updated_call.id}")

            # Broadcast call completion to subscribed WebSocket clients
            try:
                from services.websocket_manager import websocket_manager
                await websocket_manager.broadcast_call_completion(
                    conversation_id=conversation_id,
                    call=updated_call
                )
            except Exception as e:
                # Log warning but don't fail the webhook
                logger.warning(f"WebSocket broadcast failed (non-critical): {str(e)}")
                # Webhook still succeeds even if broadcast fails
            logger.info("=" * 100)

            return PostCallSuccessResponse(
                status="success",
                message="Call completion data processed successfully",
                conversation_id=conversation_id,
                call_sid=call.call_sid,
                call_status="completed"
            )

        elif request.type == "post_call_audio":
            # Handle audio webhook (minimal processing for now)
            logger.info("Received post_call_audio webhook - Logging only")
            return PostCallSuccessResponse(
                status="success",
                message="Audio webhook received",
                conversation_id=conversation_id,
                call_sid=call.call_sid,
                call_status=call.status
            )

        else:
            # Unknown webhook type
            logger.error(f"Unknown webhook type: {request.type}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "message": f"Unknown webhook type: {request.type}",
                    "details": "Supported types: post_call_transcription, call_initiation_failure, post_call_audio"
                }
            )

    except ValueError as e:
        # Validation error or invalid data
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
                "message": "Database error while processing webhook",
                "details": "Database temporarily unavailable"
            }
        )

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error processing post-call webhook: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Internal server error. Please retry.",
                "details": str(e)
            }
        )
