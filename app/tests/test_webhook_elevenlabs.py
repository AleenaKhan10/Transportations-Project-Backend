"""
Tests for ElevenLabs webhook endpoint (POST /webhooks/elevenlabs/transcription).

This test suite focuses on the webhook endpoint that receives and stores
real-time call transcription data from ElevenLabs.

Test Coverage:
1. Successful transcription save returns 201 Created
2. Response includes transcription_id and sequence_number
3. Missing required field returns 400 Bad Request
4. Invalid speaker value returns 400 Bad Request
5. Invalid timestamp format returns 400 Bad Request
6. Database connection failure returns 500 Internal Server Error
7. First dialogue creates Call record with correct call_start_time
8. Subsequent dialogues do not create duplicate Call records
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError
from main import app
from models.call import Call, CallStatus
from models.call_transcription import CallTranscription, SpeakerType
from db.database import engine
from sqlmodel import Session, delete

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    """Clean up database before and after each test."""
    with Session(engine) as session:
        # Delete all test data
        session.exec(delete(CallTranscription))
        session.exec(delete(Call))
        session.commit()

    yield

    with Session(engine) as session:
        # Clean up after test
        session.exec(delete(CallTranscription))
        session.exec(delete(Call))
        session.commit()


class TestWebhookTranscriptionEndpoint:
    """Test suite for POST /webhooks/elevenlabs/transcription endpoint."""

    def test_successful_transcription_save_returns_201(self):
        """Test that a valid request returns 201 Created with correct response data."""
        payload = {
            "conversation_id": "test-conv-001",
            "speaker": "agent",
            "message": "Hello, this is a test message from the agent.",
            "timestamp": "2025-01-15T10:30:00Z"
        }

        response = client.post("/webhooks/elevenlabs/transcription", json=payload)

        assert response.status_code == 201
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "message" in response_data
        assert "transcription_id" in response_data
        assert "sequence_number" in response_data
        assert isinstance(response_data["transcription_id"], int)
        assert isinstance(response_data["sequence_number"], int)
        assert response_data["sequence_number"] == 1  # First transcription

    def test_response_includes_transcription_id_and_sequence_number(self):
        """Test that response includes both transcription_id and sequence_number."""
        payload = {
            "conversation_id": "test-conv-002",
            "speaker": "user",
            "message": "This is a driver response.",
            "timestamp": "2025-01-15T10:31:00Z"
        }

        response = client.post("/webhooks/elevenlabs/transcription", json=payload)

        assert response.status_code == 201
        response_data = response.json()
        assert "transcription_id" in response_data
        assert "sequence_number" in response_data

        # Verify transcription was actually saved to database
        with Session(engine) as session:
            transcription = session.get(CallTranscription, response_data["transcription_id"])
            assert transcription is not None
            assert transcription.sequence_number == response_data["sequence_number"]

    def test_missing_required_field_returns_400(self):
        """Test that missing required fields return 400 Bad Request."""
        # Test missing conversation_id
        payload = {
            "speaker": "agent",
            "message": "Hello",
            "timestamp": "2025-01-15T10:30:00Z"
        }
        response = client.post("/webhooks/elevenlabs/transcription", json=payload)
        assert response.status_code == 422  # FastAPI validation error

        # Test missing speaker
        payload = {
            "conversation_id": "test-conv-003",
            "message": "Hello",
            "timestamp": "2025-01-15T10:30:00Z"
        }
        response = client.post("/webhooks/elevenlabs/transcription", json=payload)
        assert response.status_code == 422

        # Test missing message
        payload = {
            "conversation_id": "test-conv-003",
            "speaker": "agent",
            "timestamp": "2025-01-15T10:30:00Z"
        }
        response = client.post("/webhooks/elevenlabs/transcription", json=payload)
        assert response.status_code == 422

        # Test missing timestamp
        payload = {
            "conversation_id": "test-conv-003",
            "speaker": "agent",
            "message": "Hello"
        }
        response = client.post("/webhooks/elevenlabs/transcription", json=payload)
        assert response.status_code == 422

    def test_invalid_speaker_value_returns_400(self):
        """Test that invalid speaker values return 422 Unprocessable Entity (FastAPI validation)."""
        payload = {
            "conversation_id": "test-conv-004",
            "speaker": "invalid_speaker",
            "message": "This should fail",
            "timestamp": "2025-01-15T10:30:00Z"
        }

        response = client.post("/webhooks/elevenlabs/transcription", json=payload)

        # FastAPI returns 422 for Pydantic validation errors
        assert response.status_code == 422
        response_data = response.json()
        # Pydantic validation error format
        assert "detail" in response_data

    def test_invalid_timestamp_format_returns_400(self):
        """Test that invalid timestamp formats return 422 Unprocessable Entity (FastAPI validation)."""
        payload = {
            "conversation_id": "test-conv-005",
            "speaker": "agent",
            "message": "Test message",
            "timestamp": "not-a-valid-timestamp"
        }

        response = client.post("/webhooks/elevenlabs/transcription", json=payload)

        # FastAPI returns 422 for Pydantic validation errors
        assert response.status_code == 422
        response_data = response.json()
        # Pydantic validation error format
        assert "detail" in response_data

    @patch('helpers.transcription_helpers.Session')
    def test_database_connection_failure_returns_500(self, mock_session):
        """Test that database connection failures return 500 Internal Server Error."""
        # Mock database connection failure
        mock_session.side_effect = OperationalError("Connection failed", None, None)

        payload = {
            "conversation_id": "test-conv-006",
            "speaker": "agent",
            "message": "This should trigger database error",
            "timestamp": "2025-01-15T10:30:00Z"
        }

        response = client.post("/webhooks/elevenlabs/transcription", json=payload)

        assert response.status_code == 500
        response_data = response.json()
        assert response_data["status"] == "error"

    def test_first_dialogue_creates_call_record(self):
        """Test that first dialogue creates a Call record with correct call_start_time."""
        conversation_id = "test-conv-007"
        timestamp = "2025-01-15T10:30:00Z"

        payload = {
            "conversation_id": conversation_id,
            "speaker": "agent",
            "message": "This is the first dialogue",
            "timestamp": timestamp
        }

        response = client.post("/webhooks/elevenlabs/transcription", json=payload)

        assert response.status_code == 201

        # Verify Call record was created
        with Session(engine) as session:
            call = Call.get_by_conversation_id(conversation_id)
            assert call is not None
            assert call.conversation_id == conversation_id
            assert call.status == CallStatus.IN_PROGRESS
            assert call.call_start_time is not None
            # Verify call_start_time matches the first dialogue timestamp
            expected_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            assert call.call_start_time.replace(microsecond=0) == expected_time.replace(microsecond=0)

    def test_subsequent_dialogues_no_duplicate_call_records(self):
        """Test that subsequent dialogues do not create duplicate Call records."""
        conversation_id = "test-conv-008"

        # First dialogue
        payload1 = {
            "conversation_id": conversation_id,
            "speaker": "agent",
            "message": "First message",
            "timestamp": "2025-01-15T10:30:00Z"
        }
        response1 = client.post("/webhooks/elevenlabs/transcription", json=payload1)
        assert response1.status_code == 201
        assert response1.json()["sequence_number"] == 1

        # Get the Call ID after first dialogue
        with Session(engine) as session:
            call1 = Call.get_by_conversation_id(conversation_id)
            call_id_1 = call1.id
            call_start_time_1 = call1.call_start_time

        # Second dialogue
        payload2 = {
            "conversation_id": conversation_id,
            "speaker": "user",
            "message": "Second message",
            "timestamp": "2025-01-15T10:31:00Z"
        }
        response2 = client.post("/webhooks/elevenlabs/transcription", json=payload2)
        assert response2.status_code == 201
        assert response2.json()["sequence_number"] == 2

        # Third dialogue
        payload3 = {
            "conversation_id": conversation_id,
            "speaker": "agent",
            "message": "Third message",
            "timestamp": "2025-01-15T10:32:00Z"
        }
        response3 = client.post("/webhooks/elevenlabs/transcription", json=payload3)
        assert response3.status_code == 201
        assert response3.json()["sequence_number"] == 3

        # Verify only ONE Call record exists with same ID and call_start_time
        with Session(engine) as session:
            call2 = Call.get_by_conversation_id(conversation_id)
            assert call2.id == call_id_1  # Same Call ID
            assert call2.call_start_time == call_start_time_1  # Same start time

            # Verify all 3 transcriptions exist
            transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
            assert len(transcriptions) == 3
            assert transcriptions[0].sequence_number == 1
            assert transcriptions[1].sequence_number == 2
            assert transcriptions[2].sequence_number == 3
