"""
Tests for ElevenLabs post-call webhook endpoint (POST /webhooks/elevenlabs/post-call).

This test suite focuses on the post-call webhook endpoint that receives and stores
post-call completion metadata and analysis results from ElevenLabs.

Test Coverage:
1. Successful post_call_transcription webhook processing returns 200 OK
2. Successful call_initiation_failure webhook processing returns 200 OK
3. Invalid webhook payload structure returns 400 Bad Request
4. Call not found for conversation_id returns 404 Not Found
5. Database error handling returns 500 Internal Server Error
6. Timestamp conversion to timezone-aware UTC datetime
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError
from main import app
from models.call import Call, CallStatus
from models.call_transcription import CallTranscription
from db.database import engine
from sqlmodel import Session, delete
import json

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    """Clean up database before and after each test."""
    with Session(engine) as session:
        # Delete all test data (transcriptions first due to FK constraint)
        session.exec(delete(CallTranscription))
        session.exec(delete(Call))
        session.commit()

    yield

    with Session(engine) as session:
        # Clean up after test (transcriptions first due to FK constraint)
        session.exec(delete(CallTranscription))
        session.exec(delete(Call))
        session.commit()


class TestPostCallWebhookEndpoint:
    """Test suite for POST /webhooks/elevenlabs/post-call endpoint."""

    def test_successful_post_call_transcription_webhook_returns_200(self):
        """Test that a valid post_call_transcription webhook returns 200 OK with completion data."""
        # Create a Call record first
        call_start_time = datetime.now(timezone.utc)
        call = Call.create_call_with_call_sid(
            call_sid="EL_test_driver_1234567890",
            driver_id=None,  # Use None to avoid FK constraint
            call_start_time=call_start_time
        )
        # Update with conversation_id
        Call.update_conversation_id(
            call_sid="EL_test_driver_1234567890",
            conversation_id="test-conv-001"
        )

        # Post-call webhook payload
        payload = {
            "type": "post_call_transcription",
            "event_timestamp": 1732200000,  # Unix timestamp
            "data": {
                "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
                "conversation_id": "test-conv-001",
                "status": "done",
                "transcript": [
                    {
                        "role": "agent",
                        "message": "Hello, how are you?",
                        "time_in_call_secs": 0.5
                    },
                    {
                        "role": "user",
                        "message": "I'm good, thanks!",
                        "time_in_call_secs": 3.2
                    }
                ],
                "metadata": {
                    "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
                    "call_id": "twilio_call_sid",
                    "start_time_unix_secs": 1732199700,
                    "call_duration_secs": 145,
                    "cost": 0.08,
                    "from_number": "+14155551234",
                    "to_number": "+14155555678"
                },
                "analysis": {
                    "call_successful": True,
                    "transcript_summary": "Agent greeted the driver and confirmed delivery location.",
                    "evaluation_results": {
                        "criteria_1": "passed",
                        "criteria_2": "passed"
                    }
                }
            }
        }

        response = client.post("/webhooks/elevenlabs/post-call", json=payload)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["message"] == "Call completion data processed successfully"
        assert response_data["conversation_id"] == "test-conv-001"
        assert response_data["call_sid"] == "EL_test_driver_1234567890"
        assert response_data["call_status"] == "completed"

        # Verify Call record was updated with post-call data
        updated_call = Call.get_by_conversation_id("test-conv-001")
        assert updated_call is not None
        assert updated_call.status == CallStatus.COMPLETED
        assert updated_call.call_end_time is not None
        assert updated_call.transcript_summary == "Agent greeted the driver and confirmed delivery location."
        assert updated_call.call_duration_seconds == 145
        assert updated_call.cost == 0.08
        assert updated_call.call_successful is True
        assert updated_call.analysis_data is not None
        assert updated_call.metadata_json is not None

    def test_successful_call_initiation_failure_webhook_returns_200(self):
        """Test that a valid call_initiation_failure webhook returns 200 OK and sets status to FAILED."""
        # Create a Call record first
        call_start_time = datetime.now(timezone.utc)
        call = Call.create_call_with_call_sid(
            call_sid="EL_test_driver_failed",
            driver_id=None,  # Use None to avoid FK constraint
            call_start_time=call_start_time
        )
        # Update with conversation_id
        Call.update_conversation_id(
            call_sid="EL_test_driver_failed",
            conversation_id="test-conv-failed-001"
        )

        # Call initiation failure webhook payload
        payload = {
            "type": "call_initiation_failure",
            "event_timestamp": 1732200000,
            "data": {
                "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
                "conversation_id": "test-conv-failed-001",
                "status": "failed",
                "error_message": "Phone number unreachable",
                "metadata": {
                    "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
                    "call_duration_secs": 0,
                    "cost": 0.0,
                    "from_number": "+14155551234",
                    "to_number": "+14155555678"
                }
            }
        }

        response = client.post("/webhooks/elevenlabs/post-call", json=payload)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["message"] == "Call failure data processed successfully"
        assert response_data["conversation_id"] == "test-conv-failed-001"
        assert response_data["call_sid"] == "EL_test_driver_failed"
        assert response_data["call_status"] == "failed"

        # Verify Call record status was updated to FAILED
        updated_call = Call.get_by_conversation_id("test-conv-failed-001")
        assert updated_call is not None
        assert updated_call.status == CallStatus.FAILED
        assert updated_call.call_end_time is not None

    def test_invalid_webhook_payload_returns_400(self):
        """Test that invalid webhook payload structure returns 400 Bad Request."""
        # Missing conversation_id
        payload = {
            "type": "post_call_transcription",
            "event_timestamp": 1732200000,
            "data": {
                "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
                "status": "done"
                # Missing conversation_id
            }
        }

        response = client.post("/webhooks/elevenlabs/post-call", json=payload)

        assert response.status_code == 422  # Pydantic validation error

    def test_conversation_id_not_found_returns_404(self):
        """Test that Call not found for conversation_id returns 404 Not Found."""
        payload = {
            "type": "post_call_transcription",
            "event_timestamp": 1732200000,
            "data": {
                "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
                "conversation_id": "nonexistent-conv-id",
                "status": "done",
                "metadata": {
                    "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
                    "call_duration_secs": 100,
                    "cost": 0.05,
                    "from_number": "+14155551234",
                    "to_number": "+14155555678"
                },
                "analysis": {
                    "call_successful": True,
                    "transcript_summary": "Test summary"
                }
            }
        }

        response = client.post("/webhooks/elevenlabs/post-call", json=payload)

        assert response.status_code == 404
        response_data = response.json()
        assert response_data["status"] == "error"
        assert "Call not found for conversation_id" in response_data["message"]
        assert "nonexistent-conv-id" in response_data["message"]

    def test_database_error_returns_500(self):
        """Test that database connection error returns 500 Internal Server Error."""
        # Create a Call record first
        call_start_time = datetime.now(timezone.utc)
        call = Call.create_call_with_call_sid(
            call_sid="EL_test_driver_db_error",
            driver_id=None,  # Use None to avoid FK constraint
            call_start_time=call_start_time
        )
        Call.update_conversation_id(
            call_sid="EL_test_driver_db_error",
            conversation_id="test-conv-db-error"
        )

        payload = {
            "type": "post_call_transcription",
            "event_timestamp": 1732200000,
            "data": {
                "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
                "conversation_id": "test-conv-db-error",
                "status": "done",
                "metadata": {
                    "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
                    "call_duration_secs": 100,
                    "cost": 0.05,
                    "from_number": "+14155551234",
                    "to_number": "+14155555678"
                },
                "analysis": {
                    "call_successful": True,
                    "transcript_summary": "Test summary"
                }
            }
        }

        # Mock database error in update_post_call_data
        with patch('models.call.Call.update_post_call_data', side_effect=OperationalError("Mock DB error", None, None)):
            response = client.post("/webhooks/elevenlabs/post-call", json=payload)

        assert response.status_code == 500
        response_data = response.json()
        assert response_data["status"] == "error"
        assert "Database error" in response_data["message"] or "Internal server error" in response_data["message"]

    def test_timestamp_conversion_to_timezone_aware_datetime(self):
        """Test that event_timestamp (Unix timestamp) is correctly converted to timezone-aware UTC datetime."""
        # Create a Call record first
        call_start_time = datetime.now(timezone.utc)
        call = Call.create_call_with_call_sid(
            call_sid="EL_test_driver_timestamp",
            driver_id=None,  # Use None to avoid FK constraint
            call_start_time=call_start_time
        )
        Call.update_conversation_id(
            call_sid="EL_test_driver_timestamp",
            conversation_id="test-conv-timestamp"
        )

        # Use a specific Unix timestamp for verification
        test_timestamp = 1732200000  # 2024-11-21 14:13:20 UTC
        expected_datetime = datetime.fromtimestamp(test_timestamp, tz=timezone.utc)

        payload = {
            "type": "post_call_transcription",
            "event_timestamp": test_timestamp,
            "data": {
                "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
                "conversation_id": "test-conv-timestamp",
                "status": "done",
                "metadata": {
                    "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
                    "call_duration_secs": 100,
                    "cost": 0.05,
                    "from_number": "+14155551234",
                    "to_number": "+14155555678"
                },
                "analysis": {
                    "call_successful": True,
                    "transcript_summary": "Test summary"
                }
            }
        }

        response = client.post("/webhooks/elevenlabs/post-call", json=payload)

        assert response.status_code == 200

        # Verify call_end_time is timezone-aware and matches expected datetime
        updated_call = Call.get_by_conversation_id("test-conv-timestamp")
        assert updated_call is not None
        assert updated_call.call_end_time is not None
        assert updated_call.call_end_time.tzinfo is not None  # Timezone-aware
        assert updated_call.call_end_time.tzinfo == timezone.utc
        # Allow small time difference due to processing
        time_diff = abs((updated_call.call_end_time - expected_datetime).total_seconds())
        assert time_diff < 2  # Within 2 seconds
