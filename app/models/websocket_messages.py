"""
WebSocket message models for ElevenLabs call updates.

This module defines Pydantic models for WebSocket communication between
client and server for real-time call transcription and status updates.

Message Types:
- Client -> Server: SubscribeMessage, UnsubscribeMessage
- Server -> Client: SubscriptionConfirmedMessage, UnsubscribeConfirmedMessage,
                    TranscriptionMessage, CallStatusMessage, CallCompletedMessage, ErrorMessage

All server -> client messages include a 'type' field discriminator for client-side routing.
All messages use JSON format for serialization/deserialization.

Reference: agent-os/specs/2025-11-21-elevenlabs-completion-webhook-websocket/spec.md (lines 502-706)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime


# ============================================================================
# Client -> Server Messages
# ============================================================================

class SubscribeMessage(BaseModel):
    """
    Client request to subscribe to call updates.

    Client sends this message to start receiving real-time updates for a specific call.
    The identifier can be either call_sid (our identifier) or conversation_id (ElevenLabs identifier).

    Example:
        {"subscribe": "EL_driver123_1732199700"}
        {"subscribe": "abc123xyz"}

    Fields:
        subscribe: Call identifier - can be either call_sid or conversation_id

    Server Processing:
        - Auto-detect identifier type (call_sid vs conversation_id)
        - Look up Call record using Call.get_by_call_sid() or Call.get_by_conversation_id()
        - Validate Call exists
        - Add connection to subscription registry for that Call
        - Send subscription_confirmed or error message
    """
    subscribe: str = Field(..., min_length=1, description="Call identifier - call_sid or conversation_id")


class UnsubscribeMessage(BaseModel):
    """
    Client request to unsubscribe from call updates.

    Client sends this message to stop receiving updates for a specific call.

    Example:
        {"unsubscribe": "EL_driver123_1732199700"}

    Fields:
        unsubscribe: Call identifier to stop receiving updates for
    """
    unsubscribe: str = Field(..., min_length=1, description="Call identifier to unsubscribe from")


# ============================================================================
# Server -> Client Messages
# ============================================================================

class SubscriptionConfirmedMessage(BaseModel):
    """
    Server confirmation of successful subscription.

    Sent immediately after client subscribes to a call. Includes resolved
    call identifiers and current status.

    Example:
        {
            "type": "subscription_confirmed",
            "identifier": "EL_driver123_1732199700",
            "call_sid": "EL_driver123_1732199700",
            "conversation_id": "abc123xyz",
            "status": "in_progress",
            "message": "Successfully subscribed to call updates"
        }

    Fields:
        type: Message type discriminator - always "subscription_confirmed"
        identifier: Original identifier from subscribe request
        call_sid: Resolved call_sid from Call record
        conversation_id: Resolved conversation_id from Call record (may be null)
        status: Current call status (in_progress, completed, failed)
        message: Human-readable confirmation message
    """
    type: Literal["subscription_confirmed"] = Field(default="subscription_confirmed")
    identifier: str = Field(..., description="Original identifier from subscribe request")
    call_sid: str = Field(..., description="Resolved call_sid from Call record")
    conversation_id: Optional[str] = Field(None, description="Resolved conversation_id from Call record (nullable)")
    status: str = Field(..., description="Current call status (in_progress, completed, failed)")
    message: str = Field(..., description="Human-readable confirmation message")


class UnsubscribeConfirmedMessage(BaseModel):
    """
    Server confirmation of successful unsubscription.

    Sent immediately after client unsubscribes from a call.

    Example:
        {
            "type": "unsubscribe_confirmed",
            "identifier": "EL_driver123_1732199700",
            "message": "Successfully unsubscribed from call updates"
        }

    Fields:
        type: Message type discriminator - always "unsubscribe_confirmed"
        identifier: Original identifier from unsubscribe request
        message: Human-readable confirmation message
    """
    type: Literal["unsubscribe_confirmed"] = Field(default="unsubscribe_confirmed")
    identifier: str = Field(..., description="Original identifier from unsubscribe request")
    message: str = Field(..., description="Human-readable confirmation message")


class TranscriptionMessage(BaseModel):
    """
    Real-time transcription update message.

    Sent immediately after transcription webhook saves new dialogue turn to database.
    Contains speaker attribution, message text, and sequence information.

    Example:
        {
            "type": "transcription",
            "conversation_id": "abc123xyz",
            "call_sid": "EL_driver123_1732199700",
            "transcription_id": 456,
            "sequence_number": 3,
            "speaker_type": "agent",
            "message_text": "Hello, how are you doing today?",
            "timestamp": "2025-11-21T15:30:45.123456Z"
        }

    Fields:
        type: Message type discriminator - always "transcription"
        conversation_id: ElevenLabs conversation identifier
        call_sid: Our generated call identifier
        transcription_id: Database ID of transcription record
        sequence_number: Sequence number in conversation (for ordering)
        speaker_type: "agent" or "driver"
        message_text: Dialogue text
        timestamp: ISO 8601 timestamp when message occurred
    """
    type: Literal["transcription"] = Field(default="transcription")
    conversation_id: str = Field(..., description="ElevenLabs conversation identifier")
    call_sid: str = Field(..., description="Our generated call identifier")
    transcription_id: int = Field(..., description="Database ID of transcription record")
    sequence_number: int = Field(..., description="Sequence number in conversation")
    speaker_type: str = Field(..., description="Speaker type: 'agent' or 'driver'")
    message_text: str = Field(..., description="Dialogue text")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp when message occurred")


class CallStatusMessage(BaseModel):
    """
    Call status update message.

    Sent immediately after post-call webhook updates Call status.
    This is the first message in the completion sequence.

    Example:
        {
            "type": "call_status",
            "conversation_id": "abc123xyz",
            "call_sid": "EL_driver123_1732199700",
            "status": "completed",
            "call_end_time": "2025-11-21T15:35:00.000000Z"
        }

    Fields:
        type: Message type discriminator - always "call_status"
        conversation_id: ElevenLabs conversation identifier
        call_sid: Our generated call identifier
        status: New call status ("completed" or "failed")
        call_end_time: ISO 8601 timestamp when call ended (nullable)
    """
    type: Literal["call_status"] = Field(default="call_status")
    conversation_id: str = Field(..., description="ElevenLabs conversation identifier")
    call_sid: str = Field(..., description="Our generated call identifier")
    status: str = Field(..., description="New call status (completed or failed)")
    call_end_time: Optional[datetime] = Field(None, description="ISO 8601 timestamp when call ended (nullable)")


class CallCompletedMessage(BaseModel):
    """
    Complete call data message.

    Sent immediately after call_status message (second message in completion sequence).
    Contains full Call record data including all metadata fields.

    Example:
        {
            "type": "call_completed",
            "conversation_id": "abc123xyz",
            "call_sid": "EL_driver123_1732199700",
            "call_data": {
                "status": "completed",
                "driver_id": "driver123",
                "call_start_time": "2025-11-21T15:30:00.000000Z",
                "call_end_time": "2025-11-21T15:35:00.000000Z",
                "duration_seconds": 300,
                "transcript_summary": "...",
                "cost": 0.08,
                "call_successful": true,
                "analysis_data": {...},
                "metadata": {...}
            }
        }

    Fields:
        type: Message type discriminator - always "call_completed"
        conversation_id: ElevenLabs conversation identifier
        call_sid: Our generated call identifier
        call_data: Full Call record data including all metadata fields
    """
    type: Literal["call_completed"] = Field(default="call_completed")
    conversation_id: str = Field(..., description="ElevenLabs conversation identifier")
    call_sid: str = Field(..., description="Our generated call identifier")
    call_data: Dict[str, Any] = Field(..., description="Full Call record data including all metadata")


class ErrorMessage(BaseModel):
    """
    Error notification message.

    Sent when operations fail or invalid requests are received.
    Includes optional error code for programmatic handling.

    Example:
        {
            "type": "error",
            "message": "Call not found for identifier: invalid_id_123",
            "code": "CALL_NOT_FOUND"
        }

    Fields:
        type: Message type discriminator - always "error"
        message: Human-readable error description
        code: Optional error code for programmatic handling

    Common Error Codes:
        - CALL_NOT_FOUND: Identifier doesn't match any Call record
        - INVALID_IDENTIFIER: Malformed identifier format
        - AUTHENTICATION_FAILED: JWT token invalid or expired
        - SUBSCRIPTION_FAILED: Failed to subscribe to call updates
        - INVALID_MESSAGE_FORMAT: Client message doesn't match expected schema
    """
    type: Literal["error"] = Field(default="error")
    message: str = Field(..., description="Human-readable error description")
    code: Optional[str] = Field(None, description="Optional error code for programmatic handling")
