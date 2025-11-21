"""
Integration tests for WebSocket transcription broadcast.

Tests the integration between the transcription webhook and WebSocket broadcasting.
Ensures that transcriptions are broadcast to subscribed clients while webhook processing
succeeds even if broadcast fails.

Test Focus:
1. Webhook triggers WebSocket broadcast (happy path)
2. Webhook succeeds even if no clients subscribed
3. Webhook succeeds even if broadcast fails
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from main import app
from services.webhooks_elevenlabs import TranscriptionWebhookRequest
from models.call import Call, CallStatus


class TestTranscriptionBroadcast:
    """Test transcription webhook WebSocket broadcast integration."""

    @pytest.mark.asyncio
    async def test_transcription_webhook_triggers_websocket_broadcast(self):
        """
        Test that transcription webhook triggers WebSocket broadcast on success.

        Scenario:
        1. Valid transcription webhook request received
        2. Transcription saved to database successfully
        3. WebSocket broadcast_transcription() is called
        4. Webhook returns 201 Created success response

        Asserts:
        - Webhook returns 201 status
        - broadcast_transcription() called with correct parameters
        - Webhook succeeds (returns success response)
        """
        # Mock the save_transcription function and websocket_manager
        with patch('services.webhooks_elevenlabs.save_transcription') as mock_save, \
             patch('services.websocket_manager.websocket_manager') as mock_ws_manager:

            # Configure save_transcription mock
            mock_save.return_value = (123, 1)  # transcription_id, sequence_number

            # Configure websocket_manager mock
            mock_ws_manager.broadcast_transcription = AsyncMock()

            # Create test client
            client = TestClient(app)

            # Prepare webhook request
            webhook_payload = {
                "call_sid": "EL_testdriver_1700000000",
                "speaker": "agent",
                "message": "Hello, this is a test message"
            }

            # Send webhook request
            response = client.post("/webhooks/elevenlabs/transcription", json=webhook_payload)

            # Assert webhook succeeded
            assert response.status_code == 201
            assert response.json()["status"] == "success"
            assert response.json()["transcription_id"] == 123
            assert response.json()["sequence_number"] == 1

            # Assert broadcast_transcription was called
            assert mock_ws_manager.broadcast_transcription.called
            call_args = mock_ws_manager.broadcast_transcription.call_args[1]
            assert call_args["call_sid"] == "EL_testdriver_1700000000"
            assert call_args["transcription_id"] == 123
            assert call_args["sequence_number"] == 1
            assert call_args["speaker"] == "agent"
            assert call_args["message"] == "Hello, this is a test message"

    @pytest.mark.asyncio
    async def test_webhook_succeeds_with_no_subscribed_clients(self):
        """
        Test that webhook succeeds even if no clients are subscribed.

        Scenario:
        1. Valid transcription webhook request received
        2. Transcription saved to database successfully
        3. broadcast_transcription() executes but no clients subscribed (graceful no-op)
        4. Webhook returns 201 Created success response

        Asserts:
        - Webhook returns 201 status
        - Webhook succeeds despite no subscribers
        - No exceptions raised from broadcast
        """
        # Mock the save_transcription function and websocket_manager
        with patch('services.webhooks_elevenlabs.save_transcription') as mock_save, \
             patch('services.websocket_manager.websocket_manager') as mock_ws_manager:

            # Configure save_transcription mock
            mock_save.return_value = (456, 2)  # transcription_id, sequence_number

            # Configure websocket_manager mock to simulate no subscribers
            # broadcast_transcription succeeds but does nothing (no subscribers)
            mock_ws_manager.broadcast_transcription = AsyncMock()

            # Create test client
            client = TestClient(app)

            # Prepare webhook request
            webhook_payload = {
                "call_sid": "EL_testdriver_1700000001",
                "speaker": "user",
                "message": "I understand, thank you"
            }

            # Send webhook request
            response = client.post("/webhooks/elevenlabs/transcription", json=webhook_payload)

            # Assert webhook succeeded even with no subscribers
            assert response.status_code == 201
            assert response.json()["status"] == "success"
            assert response.json()["transcription_id"] == 456
            assert response.json()["sequence_number"] == 2

            # Assert broadcast was attempted (even though no subscribers)
            assert mock_ws_manager.broadcast_transcription.called

    @pytest.mark.asyncio
    async def test_webhook_succeeds_even_if_broadcast_fails(self):
        """
        Test that webhook succeeds even if WebSocket broadcast fails.

        Scenario:
        1. Valid transcription webhook request received
        2. Transcription saved to database successfully
        3. broadcast_transcription() raises exception
        4. Exception is caught and logged as warning
        5. Webhook returns 201 Created success response

        Asserts:
        - Webhook returns 201 status
        - Webhook succeeds despite broadcast failure
        - Exception from broadcast doesn't propagate
        - Data persistence succeeds (transcription saved)

        This ensures webhook processing is resilient to WebSocket failures.
        """
        # Mock the save_transcription function and websocket_manager
        with patch('services.webhooks_elevenlabs.save_transcription') as mock_save, \
             patch('services.websocket_manager.websocket_manager') as mock_ws_manager, \
             patch('services.webhooks_elevenlabs.logger') as mock_logger:

            # Configure save_transcription mock
            mock_save.return_value = (789, 3)  # transcription_id, sequence_number

            # Configure websocket_manager to raise exception
            mock_ws_manager.broadcast_transcription = AsyncMock(
                side_effect=Exception("WebSocket connection error")
            )

            # Create test client
            client = TestClient(app)

            # Prepare webhook request
            webhook_payload = {
                "call_sid": "EL_testdriver_1700000002",
                "speaker": "agent",
                "message": "Can you confirm your location?"
            }

            # Send webhook request
            response = client.post("/webhooks/elevenlabs/transcription", json=webhook_payload)

            # Assert webhook succeeded despite broadcast failure
            assert response.status_code == 201
            assert response.json()["status"] == "success"
            assert response.json()["transcription_id"] == 789
            assert response.json()["sequence_number"] == 3

            # Assert broadcast was attempted but failed
            assert mock_ws_manager.broadcast_transcription.called

            # Assert warning was logged about broadcast failure
            warning_calls = [call for call in mock_logger.warning.call_args_list
                           if "WebSocket broadcast failed" in str(call)]
            assert len(warning_calls) > 0, "Warning should be logged about broadcast failure"
