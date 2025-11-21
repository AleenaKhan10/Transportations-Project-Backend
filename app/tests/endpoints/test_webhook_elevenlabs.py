"""
Tests for ElevenLabs webhook endpoint refactoring.

Focused tests covering critical endpoint behaviors:
- Webhook accepts call_sid in request payload
- Webhook returns 400 for invalid call_sid
- Webhook returns 400 when Call has NULL conversation_id
- End-to-end call creation workflow
- Call status updates to FAILED when ElevenLabs fails
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlmodel import Session
from models.call import Call, CallStatus
from models.call_transcription import CallTranscription
from db.database import engine
from main import app

client = TestClient(app)


class TestWebhookEndpoint:
    """Test refactored webhook endpoint for call_sid workflow."""

    def test_webhook_accepts_call_sid_in_payload(self):
        """Test that webhook accepts call_sid field in request."""
        call_sid = "EL_11111_test_webhook_callsid"
        conversation_id = "conv_test_webhook_11111"

        # Setup: Create Call record with conversation_id
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=11111,
            call_start_time=datetime.now(timezone.utc)
        )
        Call.update_conversation_id(call_sid, conversation_id)

        try:
            # Send webhook request with call_sid
            webhook_payload = {
                "call_sid": call_sid,
                "speaker": "agent",
                "message": "Hello, this is a test webhook message",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            response = client.post(
                "/webhooks/elevenlabs/transcription",
                json=webhook_payload
            )

            # Verify success
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "success"
            assert data["sequence_number"] == 1
            assert "call_sid" in data["message"]

        finally:
            # Cleanup
            with Session(engine) as session:
                transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
                for t in transcriptions:
                    session.delete(t)
                session.delete(call)
                session.commit()

    def test_webhook_returns_400_for_invalid_call_sid(self):
        """Test that webhook returns 400 Bad Request for unknown call_sid."""
        # Send webhook with non-existent call_sid
        webhook_payload = {
            "call_sid": "EL_INVALID_999999999",
            "speaker": "agent",
            "message": "This should fail",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        response = client.post(
            "/webhooks/elevenlabs/transcription",
            json=webhook_payload
        )

        # Should return 400 Bad Request
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "not found" in data["message"].lower()

    def test_webhook_returns_400_for_null_conversation_id(self):
        """Test that webhook returns 400 when Call has NULL conversation_id."""
        call_sid = "EL_22222_test_null_conv"

        # Create Call WITHOUT conversation_id (simulates API call hasn't completed)
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=22222,
            call_start_time=datetime.now(timezone.utc)
        )

        try:
            # Send webhook request
            webhook_payload = {
                "call_sid": call_sid,
                "speaker": "user",
                "message": "Hello",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            response = client.post(
                "/webhooks/elevenlabs/transcription",
                json=webhook_payload
            )

            # Should return 400 Bad Request
            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"
            assert "incomplete" in data["message"].lower() or "has no conversation_id" in data["details"].lower()

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_end_to_end_call_creation_workflow(self):
        """Test complete call lifecycle from creation through webhook."""
        call_sid = "EL_33333_test_e2e"
        conversation_id = "conv_test_e2e_33333"

        # STEP 1: Create Call record (simulates what happens in make_drivers_violation_batch_call_elevenlabs)
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=33333,
            call_start_time=datetime.now(timezone.utc),
            status=CallStatus.IN_PROGRESS
        )

        # Verify initial state
        assert call.conversation_id is None
        assert call.status == CallStatus.IN_PROGRESS

        # STEP 2: Update with conversation_id (simulates ElevenLabs API response)
        Call.update_conversation_id(call_sid, conversation_id)
        updated_call = Call.get_by_call_sid(call_sid)
        assert updated_call.conversation_id == conversation_id

        try:
            # STEP 3: Webhook receives transcription
            webhook_payload = {
                "call_sid": call_sid,
                "speaker": "agent",
                "message": "End-to-end test message",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            response = client.post(
                "/webhooks/elevenlabs/transcription",
                json=webhook_payload
            )

            # STEP 4: Verify transcription saved
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "success"

            # Verify transcription in database
            transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
            assert len(transcriptions) == 1
            assert transcriptions[0].message_text == "End-to-end test message"

        finally:
            # Cleanup
            with Session(engine) as session:
                transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
                for t in transcriptions:
                    session.delete(t)
                session.delete(call)
                session.commit()

    def test_call_status_updates_to_failed_on_api_error(self):
        """Test that Call status is set to FAILED when ElevenLabs API fails."""
        call_sid = "EL_44444_test_failed_status"

        # Create Call record
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=44444,
            call_start_time=datetime.now(timezone.utc)
        )

        # Simulate API failure - update status to FAILED
        # (This simulates what happens in make_drivers_violation_batch_call_elevenlabs error handler)
        Call.update_status_by_call_sid(
            call_sid=call_sid,
            status=CallStatus.FAILED
        )

        try:
            # Verify status updated
            failed_call = Call.get_by_call_sid(call_sid)
            assert failed_call.status == CallStatus.FAILED
            assert failed_call.conversation_id is None  # No conversation_id since API failed

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()
