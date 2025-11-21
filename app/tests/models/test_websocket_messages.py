"""
Tests for WebSocket message models.

This module contains focused tests for WebSocket message serialization/deserialization.
Tests verify that messages parse from JSON correctly and serialize to expected format.

Test Coverage:
1. SubscribeMessage parsing from JSON (client -> server)
2. TranscriptionMessage serialization to JSON (server -> client)
3. ErrorMessage with code field (server -> client)

Reference: agent-os/specs/2025-11-21-elevenlabs-completion-webhook-websocket/spec.md
"""

import pytest
from datetime import datetime, timezone
from models.websocket_messages import (
    SubscribeMessage,
    TranscriptionMessage,
    ErrorMessage,
)


def test_subscribe_message_parsing():
    """Test SubscribeMessage parsing from JSON (client -> server)."""
    # Test with call_sid identifier
    json_data = {"subscribe": "EL_driver123_1732199700"}
    message = SubscribeMessage(**json_data)
    assert message.subscribe == "EL_driver123_1732199700"

    # Test with conversation_id identifier
    json_data = {"subscribe": "abc123xyz"}
    message = SubscribeMessage(**json_data)
    assert message.subscribe == "abc123xyz"

    # Test that empty string fails validation
    with pytest.raises(ValueError):
        SubscribeMessage(subscribe="")


def test_transcription_message_serialization():
    """Test TranscriptionMessage serialization to JSON (server -> client)."""
    # Create message with all required fields
    timestamp = datetime(2025, 11, 21, 15, 30, 45, 123456, tzinfo=timezone.utc)
    message = TranscriptionMessage(
        conversation_id="abc123xyz",
        call_sid="EL_driver123_1732199700",
        transcription_id=456,
        sequence_number=3,
        speaker_type="agent",
        message_text="Hello, how are you doing today?",
        timestamp=timestamp
    )

    # Serialize to dict (JSON-compatible)
    data = message.model_dump()

    # Verify all fields present with correct values
    assert data["type"] == "transcription"
    assert data["conversation_id"] == "abc123xyz"
    assert data["call_sid"] == "EL_driver123_1732199700"
    assert data["transcription_id"] == 456
    assert data["sequence_number"] == 3
    assert data["speaker_type"] == "agent"
    assert data["message_text"] == "Hello, how are you doing today?"
    assert data["timestamp"] == timestamp

    # Verify type field is automatically set
    assert "type" in data
    assert data["type"] == "transcription"


def test_error_message_with_code():
    """Test ErrorMessage with optional code field (server -> client)."""
    # Test with code field
    message = ErrorMessage(
        message="Call not found for identifier: invalid_id_123",
        code="CALL_NOT_FOUND"
    )
    data = message.model_dump()
    assert data["type"] == "error"
    assert data["message"] == "Call not found for identifier: invalid_id_123"
    assert data["code"] == "CALL_NOT_FOUND"

    # Test without code field (optional)
    message = ErrorMessage(message="Generic error occurred")
    data = message.model_dump()
    assert data["type"] == "error"
    assert data["message"] == "Generic error occurred"
    assert data["code"] is None

    # Verify type field is automatically set
    assert "type" in data
    assert data["type"] == "error"
