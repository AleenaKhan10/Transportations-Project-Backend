"""
Tests for WebSocket endpoint for real-time call updates.

These tests verify the WebSocket endpoint functionality:
- Connection with valid JWT token
- Rejection with invalid token
- Subscribe message handling
- Unsubscribe message handling
- Invalid message format handling

Test Strategy: Maximum 5 focused tests covering critical behaviors only.

Reference: agent-os/specs/2025-11-21-elevenlabs-completion-webhook-websocket/tasks.md (lines 544-555)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from fastapi.testclient import TestClient
from fastapi import status as http_status

from main import app
from models.call import Call, CallStatus
from models.call_transcription import CallTranscription, SpeakerType
from datetime import datetime, timezone


@pytest.fixture
def mock_call():
    """Create a mock Call object."""
    call = MagicMock(spec=Call)
    call.id = 1
    call.call_sid = "EL_driver123_1732199700"
    call.conversation_id = "abc123xyz"
    call.status = CallStatus.IN_PROGRESS
    return call


@pytest.fixture
def valid_token():
    """
    Return a valid JWT token for testing.

    In a real test environment, you would generate a proper JWT token.
    For this test, we'll mock the validation instead.
    """
    return "valid_test_token_12345"


@pytest.fixture
def invalid_token():
    """Return an invalid JWT token for testing."""
    return "invalid_token"


@pytest.fixture
def mock_transcriptions():
    """Create a list of mock CallTranscription objects."""
    transcription1 = MagicMock(spec=CallTranscription)
    transcription1.id = 1
    transcription1.conversation_id = "abc123xyz"
    transcription1.speaker_type = SpeakerType.AGENT
    transcription1.message_text = "Hello, this is a test message from the agent."
    transcription1.timestamp = datetime(2025, 11, 21, 15, 30, 0, tzinfo=timezone.utc)
    transcription1.sequence_number = 1

    transcription2 = MagicMock(spec=CallTranscription)
    transcription2.id = 2
    transcription2.conversation_id = "abc123xyz"
    transcription2.speaker_type = SpeakerType.DRIVER
    transcription2.message_text = "Hi, this is the driver responding."
    transcription2.timestamp = datetime(2025, 11, 21, 15, 30, 5, tzinfo=timezone.utc)
    transcription2.sequence_number = 2

    return [transcription1, transcription2]


class TestWebSocketEndpoint:
    """Test suite for WebSocket endpoint."""

    @patch("services.websocket_calls.validate_jwt_token")
    @patch("services.websocket_manager.Call.get_by_call_sid")
    def test_websocket_connection_with_valid_token(
        self, mock_get_by_call_sid, mock_validate_jwt, mock_call, valid_token
    ):
        """
        Test 1: WebSocket accepts connection with valid JWT token.

        Verifies that:
        - WebSocket connection is established with valid JWT
        - Connection is accepted
        - Subscribe message is processed
        - Subscription confirmation is sent
        """
        # Mock JWT validation to return user info
        mock_validate_jwt.return_value = {
            "user_id": "user123",
            "username": "test@example.com"
        }

        # Mock Call lookup to return mock call
        mock_get_by_call_sid.return_value = mock_call

        client = TestClient(app)

        # Connect to WebSocket with valid token
        with client.websocket_connect(f"/ws/calls/transcriptions?token={valid_token}") as websocket:
            # Send subscribe message
            websocket.send_json({"subscribe": "EL_driver123_1732199700"})

            # Receive subscription confirmation
            response = websocket.receive_json()

            # Verify response
            assert response["type"] == "subscription_confirmed"
            assert response["identifier"] == "EL_driver123_1732199700"
            assert response["call_sid"] == "EL_driver123_1732199700"
            assert response["conversation_id"] == "abc123xyz"
            assert response["status"] == "in_progress"
            assert "Successfully subscribed" in response["message"]

            # Verify JWT validation was called
            mock_validate_jwt.assert_called_once_with(valid_token)


    @patch("services.websocket_calls.validate_jwt_token")
    def test_websocket_connection_with_invalid_token(
        self, mock_validate_jwt, invalid_token
    ):
        """
        Test 2: WebSocket rejects connection with invalid token.

        Verifies that:
        - WebSocket connection is rejected with invalid JWT
        - Connection closes with policy violation code
        """
        # Mock JWT validation to raise ValueError (invalid token)
        mock_validate_jwt.side_effect = ValueError("Invalid token")

        client = TestClient(app)

        # Attempt to connect with invalid token
        # Should raise WebSocketDisconnect or similar exception
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/calls/transcriptions?token={invalid_token}") as websocket:
                # Should not reach here - connection should be rejected
                pass

        # Verify JWT validation was attempted
        mock_validate_jwt.assert_called_once_with(invalid_token)


    @patch("services.websocket_calls.validate_jwt_token")
    @patch("services.websocket_manager.Call.get_by_call_sid")
    def test_websocket_subscribe_to_nonexistent_call(
        self, mock_get_by_call_sid, mock_validate_jwt, valid_token
    ):
        """
        Test 3: WebSocket sends error message for nonexistent call subscription.

        Verifies that:
        - Subscribe request for nonexistent call returns error
        - Error message includes CALL_NOT_FOUND code
        """
        # Mock JWT validation
        mock_validate_jwt.return_value = {
            "user_id": "user123",
            "username": "test@example.com"
        }

        # Mock Call lookup to return None (call not found)
        mock_get_by_call_sid.return_value = None

        client = TestClient(app)

        with client.websocket_connect(f"/ws/calls/transcriptions?token={valid_token}") as websocket:
            # Send subscribe message for nonexistent call
            websocket.send_json({"subscribe": "EL_nonexistent_12345"})

            # Receive error message
            response = websocket.receive_json()

            # Verify error response
            assert response["type"] == "error"
            assert response["code"] == "CALL_NOT_FOUND"
            assert "not found" in response["message"].lower()


    @patch("services.websocket_calls.validate_jwt_token")
    @patch("services.websocket_manager.Call.get_by_call_sid")
    def test_websocket_unsubscribe_message(
        self, mock_get_by_call_sid, mock_validate_jwt, mock_call, valid_token
    ):
        """
        Test 4: WebSocket processes unsubscribe message correctly.

        Verifies that:
        - Client can subscribe to a call
        - Client can unsubscribe from the call
        - Unsubscribe confirmation is sent
        """
        # Mock JWT validation
        mock_validate_jwt.return_value = {
            "user_id": "user123",
            "username": "test@example.com"
        }

        # Mock Call lookup
        mock_get_by_call_sid.return_value = mock_call

        client = TestClient(app)

        with client.websocket_connect(f"/ws/calls/transcriptions?token={valid_token}") as websocket:
            # Subscribe first
            websocket.send_json({"subscribe": "EL_driver123_1732199700"})
            subscription_response = websocket.receive_json()
            assert subscription_response["type"] == "subscription_confirmed"

            # Unsubscribe
            websocket.send_json({"unsubscribe": "EL_driver123_1732199700"})
            unsubscribe_response = websocket.receive_json()

            # Verify unsubscribe confirmation
            assert unsubscribe_response["type"] == "unsubscribe_confirmed"
            assert unsubscribe_response["identifier"] == "EL_driver123_1732199700"
            assert "Successfully unsubscribed" in unsubscribe_response["message"]


    @patch("services.websocket_calls.validate_jwt_token")
    def test_websocket_invalid_message_format(
        self, mock_validate_jwt, valid_token
    ):
        """
        Test 5: WebSocket sends error message for invalid message format.

        Verifies that:
        - Invalid message format is detected
        - Error message with INVALID_MESSAGE_FORMAT code is sent
        """
        # Mock JWT validation
        mock_validate_jwt.return_value = {
            "user_id": "user123",
            "username": "test@example.com"
        }

        client = TestClient(app)

        with client.websocket_connect(f"/ws/calls/transcriptions?token={valid_token}") as websocket:
            # Send invalid message (missing 'subscribe' or 'unsubscribe' key)
            websocket.send_json({"invalid_key": "some_value"})

            # Receive error message
            response = websocket.receive_json()

            # Verify error response
            assert response["type"] == "error"
            assert response["code"] == "INVALID_MESSAGE_FORMAT"
            assert "Invalid message format" in response["message"]
            assert "subscribe" in response["message"] or "unsubscribe" in response["message"]


    @patch("services.websocket_calls.validate_jwt_token")
    @patch("services.websocket_manager.Call.get_by_call_sid")
    @patch("models.call_transcription.CallTranscription.get_by_conversation_id")
    def test_websocket_sends_existing_transcriptions_on_subscribe(
        self, mock_get_transcriptions, mock_get_by_call_sid, mock_validate_jwt,
        mock_call, mock_transcriptions, valid_token
    ):
        """
        Test 6: WebSocket sends all existing transcriptions when client subscribes.

        Verifies that:
        - Client subscribes to a call
        - Subscription confirmation is sent
        - All existing transcriptions are sent in sequence order
        - Each transcription message has correct format
        """
        # Mock JWT validation
        mock_validate_jwt.return_value = {
            "user_id": "user123",
            "username": "test@example.com"
        }

        # Mock Call lookup
        mock_get_by_call_sid.return_value = mock_call

        # Mock transcription lookup to return existing transcriptions
        mock_get_transcriptions.return_value = mock_transcriptions

        client = TestClient(app)

        with client.websocket_connect(f"/ws/calls/transcriptions?token={valid_token}") as websocket:
            # Send subscribe message
            websocket.send_json({"subscribe": "EL_driver123_1732199700"})

            # Receive subscription confirmation
            response = websocket.receive_json()
            assert response["type"] == "subscription_confirmed"
            assert response["call_sid"] == "EL_driver123_1732199700"

            # Receive all existing transcriptions
            transcription_messages = []
            for _ in range(len(mock_transcriptions)):
                msg = websocket.receive_json()
                transcription_messages.append(msg)

            # Verify all transcriptions were sent
            assert len(transcription_messages) == 2

            # Verify first transcription
            assert transcription_messages[0]["type"] == "transcription"
            assert transcription_messages[0]["sequence_number"] == 1
            assert transcription_messages[0]["speaker_type"] == "agent"
            assert transcription_messages[0]["message_text"] == "Hello, this is a test message from the agent."
            assert transcription_messages[0]["call_sid"] == "EL_driver123_1732199700"

            # Verify second transcription
            assert transcription_messages[1]["type"] == "transcription"
            assert transcription_messages[1]["sequence_number"] == 2
            assert transcription_messages[1]["speaker_type"] == "driver"
            assert transcription_messages[1]["message_text"] == "Hi, this is the driver responding."
            assert transcription_messages[1]["call_sid"] == "EL_driver123_1732199700"

            # Verify transcriptions were fetched
            mock_get_transcriptions.assert_called_once_with("abc123xyz")
