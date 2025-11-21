"""
Integration tests for call completion WebSocket broadcast.

This module tests the integration between the post-call webhook and WebSocket
broadcasting for call completion events. It verifies the two-message protocol
and ensures webhook processing succeeds even when broadcast fails.

Test Focus:
- Post-call webhook triggers WebSocket broadcast
- Two-message sequence (status then data)
- Webhook succeeds even if no clients subscribed
- Webhook succeeds even if broadcast fails
- Message order is maintained

Reference:
- Spec lines 810-826 for integration details
- Spec lines 610-682 for message formats
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock, call
from fastapi import status
from fastapi.testclient import TestClient

from main import app
from models.call import Call, CallStatus
from services.websocket_manager import websocket_manager


@pytest.fixture
def mock_call():
    """Create a mock Call object with all required fields."""
    call = Mock(spec=Call)
    call.id = 1
    call.call_sid = "EL_driver123_1732199700"
    call.conversation_id = "abc123xyz"
    call.driver_id = "driver123"
    call.status = CallStatus.COMPLETED
    call.call_start_time = datetime(2025, 11, 21, 15, 30, 0, tzinfo=timezone.utc)
    call.call_end_time = datetime(2025, 11, 21, 15, 35, 0, tzinfo=timezone.utc)
    call.call_duration_seconds = 300
    call.transcript_summary = "Test call summary"
    call.cost = 0.08
    call.call_successful = True
    call.analysis_data = json.dumps({
        "call_successful": True,
        "transcript_summary": "Test call summary",
        "evaluation_results": {"criteria_1": "passed"}
    })
    call.metadata_json = json.dumps({
        "call_duration_secs": 300,
        "cost": 0.08,
        "from_number": "+14155551234",
        "to_number": "+14155555678"
    })
    return call


@pytest.fixture
def post_call_webhook_payload():
    """Create a valid post-call webhook payload."""
    return {
        "type": "post_call_transcription",
        "event_timestamp": 1732199700,
        "data": {
            "agent_id": "agent_123",
            "conversation_id": "abc123xyz",
            "status": "done",
            "transcript": [
                {
                    "role": "agent",
                    "message": "Hello, how are you?",
                    "time_in_call_secs": 0.5
                }
            ],
            "metadata": {
                "agent_id": "agent_123",
                "call_id": "twilio_call_sid",
                "start_time_unix_secs": 1732199400,
                "call_duration_secs": 300,
                "cost": 0.08,
                "from_number": "+14155551234",
                "to_number": "+14155555678"
            },
            "analysis": {
                "call_successful": True,
                "transcript_summary": "Test call summary",
                "evaluation_results": {"criteria_1": "passed"}
            }
        }
    }


@pytest.mark.asyncio
async def test_post_call_webhook_triggers_broadcast(mock_call, post_call_webhook_payload):
    """
    Test 1: Post-call webhook triggers WebSocket broadcast (happy path).

    Verify that when post-call webhook successfully updates Call record,
    it triggers the broadcast_call_completion method.
    """
    client = TestClient(app)

    # Create a real AsyncMock for broadcast_call_completion
    mock_broadcast = AsyncMock()

    with patch('models.call.Call') as MockCall:
        # Mock Call.get_by_conversation_id to return our mock call
        MockCall.get_by_conversation_id.return_value = mock_call

        # Mock Call.update_post_call_data to return updated call
        MockCall.update_post_call_data.return_value = mock_call

        # Patch websocket_manager.broadcast_call_completion in the websocket_manager module
        with patch('services.websocket_manager.websocket_manager.broadcast_call_completion', mock_broadcast):
            # Send webhook request
            response = client.post(
                "/webhooks/elevenlabs/post-call",
                json=post_call_webhook_payload
            )

            # Verify webhook succeeded
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["status"] == "success"
            assert response_data["conversation_id"] == "abc123xyz"
            assert response_data["call_sid"] == "EL_driver123_1732199700"

            # Verify broadcast_call_completion was called with correct args
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            assert call_args[1]["conversation_id"] == "abc123xyz"
            assert call_args[1]["call"] == mock_call


@pytest.mark.asyncio
async def test_two_message_sequence(mock_call):
    """
    Test 2: Two-message sequence (status then data).

    Verify that broadcast_call_completion sends two messages in correct order:
    1. CallStatusMessage with type="call_status"
    2. CallCompletedMessage with type="call_completed"
    """
    # Mock broadcast_to_call to capture messages
    messages_sent = []

    async def capture_broadcast(call, message):
        messages_sent.append(message)

    with patch.object(websocket_manager, 'broadcast_to_call', side_effect=capture_broadcast):
        # Call broadcast_call_completion
        await websocket_manager.broadcast_call_completion(
            conversation_id="abc123xyz",
            call=mock_call
        )

    # Verify two messages were sent
    assert len(messages_sent) == 2

    # Verify first message is call_status
    first_message = messages_sent[0]
    assert first_message["type"] == "call_status"
    assert first_message["conversation_id"] == "abc123xyz"
    assert first_message["call_sid"] == "EL_driver123_1732199700"
    assert "status" in first_message
    assert "call_end_time" in first_message

    # Verify second message is call_completed
    second_message = messages_sent[1]
    assert second_message["type"] == "call_completed"
    assert second_message["conversation_id"] == "abc123xyz"
    assert second_message["call_sid"] == "EL_driver123_1732199700"
    assert "call_data" in second_message

    # Verify call_data contains parsed JSON fields
    call_data = second_message["call_data"]
    assert call_data["driver_id"] == "driver123"
    assert call_data["transcript_summary"] == "Test call summary"
    assert call_data["cost"] == 0.08
    assert call_data["call_successful"] is True
    assert isinstance(call_data["analysis_data"], dict)
    assert isinstance(call_data["metadata"], dict)


@pytest.mark.asyncio
async def test_webhook_succeeds_with_no_subscribers(mock_call, post_call_webhook_payload):
    """
    Test 3: Webhook succeeds even if no clients subscribed.

    Verify that webhook processing completes successfully when broadcast
    is called but no WebSocket clients are subscribed to the call.
    """
    client = TestClient(app)

    # Create a real AsyncMock for broadcast_call_completion
    mock_broadcast = AsyncMock()

    with patch('models.call.Call') as MockCall:
        # Mock Call methods
        MockCall.get_by_conversation_id.return_value = mock_call
        MockCall.update_post_call_data.return_value = mock_call

        # Patch websocket_manager.broadcast_call_completion
        with patch('services.websocket_manager.websocket_manager.broadcast_call_completion', mock_broadcast):
            # Mock broadcast to simulate no subscribers (no error)
            mock_broadcast.return_value = None

            # Send webhook request
            response = client.post(
                "/webhooks/elevenlabs/post-call",
                json=post_call_webhook_payload
            )

            # Verify webhook succeeded
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["status"] == "success"

            # Verify broadcast was called (even though no subscribers)
            mock_broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_succeeds_when_broadcast_fails(mock_call, post_call_webhook_payload):
    """
    Test 4: Webhook succeeds even if broadcast fails.

    Verify that webhook processing completes successfully even when
    broadcast_call_completion raises an exception. The webhook should
    log the error but return 200 OK.
    """
    client = TestClient(app)

    # Create a real AsyncMock for broadcast_call_completion
    mock_broadcast = AsyncMock()

    with patch('models.call.Call') as MockCall:
        # Mock Call methods
        MockCall.get_by_conversation_id.return_value = mock_call
        MockCall.update_post_call_data.return_value = mock_call

        # Patch websocket_manager.broadcast_call_completion
        with patch('services.websocket_manager.websocket_manager.broadcast_call_completion', mock_broadcast):
            # Mock broadcast to raise exception
            mock_broadcast.side_effect = Exception("WebSocket connection error")

            # Send webhook request
            response = client.post(
                "/webhooks/elevenlabs/post-call",
                json=post_call_webhook_payload
            )

            # Verify webhook still succeeded despite broadcast failure
            assert response.status_code == status.HTTP_200_OK
            response_data = response.json()
            assert response_data["status"] == "success"
            assert response_data["conversation_id"] == "abc123xyz"

            # Verify broadcast was attempted
            mock_broadcast.assert_called_once()
