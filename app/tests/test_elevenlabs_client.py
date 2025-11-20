"""
Focused tests for ElevenLabsClient functionality.

Tests cover:
1. Client initialization with API key
2. Successful call creation with correct payload
3. API authentication failure handling
4. Timeout handling with retry logic
5. HTTP error responses
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from utils.elevenlabs_client import ElevenLabsClient


class TestElevenLabsClientInitialization:
    """Test client initialization and configuration."""

    def test_client_initializes_with_correct_configuration(self):
        """Test that client initializes with correct base URL and agent IDs."""
        with patch("utils.elevenlabs_client.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "test_api_key_123"

            client = ElevenLabsClient()

            assert client.base_url == "https://api.elevenlabs.io/v1/convai"
            assert client.api_key == "test_api_key_123"
            assert client.AGENT_ID == "agent_5501k9czkv3qepy815bm59nt04qk"
            assert client.AGENT_PHONE_NUMBER_ID == "phnum_8401k9ndc950ewza733y8thmpbrx"
            assert client.MAX_RETRIES == 3

    def test_client_raises_error_without_api_key(self):
        """Test that client raises ValueError when API key is not configured."""
        with patch("utils.elevenlabs_client.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = ""

            with pytest.raises(ValueError, match="ELEVENLABS_API_KEY environment variable is required"):
                ElevenLabsClient()


class TestCreateOutboundCall:
    """Test create_outbound_call method functionality."""

    @pytest.mark.asyncio
    async def test_successful_call_creation(self):
        """Test successful outbound call creation with correct payload structure."""
        with patch("utils.elevenlabs_client.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "test_api_key"

            client = ElevenLabsClient()

            # Mock successful API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "conversation_id": "conv_123abc",
                "callSid": "CA123456789"
            }

            with patch("httpx.AsyncClient") as mock_async_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.post = AsyncMock(return_value=mock_response)
                mock_async_client.return_value.__aenter__.return_value = mock_client_instance

                result = await client.create_outbound_call(
                    to_number="+14155551234",
                    prompt="Test prompt",
                    transfer_to="+14155555678",
                    call_sid="test_call_sid",
                    dispatcher_name="Test Dispatcher"
                )

                # Verify response
                assert result["conversation_id"] == "conv_123abc"
                assert result["callSid"] == "CA123456789"

                # Verify API was called with correct payload
                call_args = mock_client_instance.post.call_args
                assert call_args[0][0] == "https://api.elevenlabs.io/v1/convai/twilio/outbound-call"

                payload = call_args[1]["json"]
                assert payload["agent_id"] == "agent_5501k9czkv3qepy815bm59nt04qk"
                assert payload["agent_phone_number_id"] == "phnum_8401k9ndc950ewza733y8thmpbrx"
                assert payload["to_number"] == "+14155551234"
                assert payload["conversation_initiation_client_data"]["dynamic_variables"]["prompt"] == "Test prompt"

                # Verify headers
                headers = call_args[1]["headers"]
                assert headers["xi-api-key"] == "test_api_key"
                assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_api_authentication_error(self):
        """Test handling of API authentication failure (401)."""
        with patch("utils.elevenlabs_client.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "invalid_key"

            client = ElevenLabsClient()

            # Mock 401 unauthorized response
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized: Invalid API key"

            with patch("httpx.AsyncClient") as mock_async_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.post = AsyncMock(return_value=mock_response)
                mock_async_client.return_value.__aenter__.return_value = mock_client_instance

                with pytest.raises(Exception, match="ElevenLabs API Error: 401"):
                    await client.create_outbound_call(
                        to_number="+14155551234",
                        prompt="Test prompt",
                        transfer_to="+14155555678",
                        call_sid="test_call_sid",
                        dispatcher_name="Test Dispatcher"
                    )

    @pytest.mark.asyncio
    async def test_timeout_with_retry_logic(self):
        """Test timeout handling with exponential backoff retry."""
        with patch("utils.elevenlabs_client.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "test_api_key"

            client = ElevenLabsClient()

            with patch("httpx.AsyncClient") as mock_async_client:
                mock_client_instance = AsyncMock()
                # Simulate timeout on all attempts
                mock_client_instance.post = AsyncMock(side_effect=httpx.TimeoutException("Connection timeout"))
                mock_async_client.return_value.__aenter__.return_value = mock_client_instance

                with patch("asyncio.sleep") as mock_sleep:
                    with pytest.raises(Exception, match="Unable to reach ElevenLabs API after multiple retries"):
                        await client.create_outbound_call(
                            to_number="+14155551234",
                            prompt="Test prompt",
                            transfer_to="+14155555678",
                            call_sid="test_call_sid",
                            dispatcher_name="Test Dispatcher"
                        )

                    # Verify retry logic was executed (3 attempts total)
                    assert mock_client_instance.post.call_count == 3
                    # Verify exponential backoff sleep was called (2 times: after 1st and 2nd attempts)
                    assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_server_error_response(self):
        """Test handling of server error response (500)."""
        with patch("utils.elevenlabs_client.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "test_api_key"

            client = ElevenLabsClient()

            # Mock 500 server error response
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            with patch("httpx.AsyncClient") as mock_async_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.post = AsyncMock(return_value=mock_response)
                mock_async_client.return_value.__aenter__.return_value = mock_client_instance

                with pytest.raises(Exception, match="ElevenLabs API Error: 500"):
                    await client.create_outbound_call(
                        to_number="+14155551234",
                        prompt="Test prompt",
                        transfer_to="+14155555678",
                        call_sid="test_call_sid",
                        dispatcher_name="Test Dispatcher"
                    )

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self):
        """Test that retry logic succeeds when second attempt is successful."""
        with patch("utils.elevenlabs_client.settings") as mock_settings:
            mock_settings.ELEVENLABS_API_KEY = "test_api_key"

            client = ElevenLabsClient()

            # Mock first attempt fails, second succeeds
            mock_success_response = MagicMock()
            mock_success_response.status_code = 200
            mock_success_response.json.return_value = {
                "conversation_id": "conv_retry_success",
                "callSid": "CA987654321"
            }

            with patch("httpx.AsyncClient") as mock_async_client:
                mock_client_instance = AsyncMock()
                # First call times out, second succeeds
                mock_client_instance.post = AsyncMock(
                    side_effect=[
                        httpx.TimeoutException("First timeout"),
                        mock_success_response
                    ]
                )
                mock_async_client.return_value.__aenter__.return_value = mock_client_instance

                with patch("asyncio.sleep"):
                    result = await client.create_outbound_call(
                        to_number="+14155551234",
                        prompt="Test prompt",
                        transfer_to="+14155555678",
                        call_sid="test_call_sid",
                        dispatcher_name="Test Dispatcher"
                    )

                    # Verify response from successful retry
                    assert result["conversation_id"] == "conv_retry_success"
                    assert result["callSid"] == "CA987654321"
                    # Verify retry was attempted (2 calls total)
                    assert mock_client_instance.post.call_count == 2
