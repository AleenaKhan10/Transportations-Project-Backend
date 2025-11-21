import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from models.vapi import BatchCallRequest, DriverData, Violations, ViolationDetail
from models.driver_data import make_drivers_violation_batch_call_elevenlabs
from fastapi import HTTPException


class TestElevenLabsBatchCall:
    """
    Test suite for ElevenLabs batch call function.
    Focused tests for critical batch call behaviors.
    """

    @pytest.fixture
    def sample_batch_request(self):
        """Create a sample BatchCallRequest for testing."""
        return BatchCallRequest(
            callType="violation",
            timestamp="2025-11-20T10:00:00Z",
            drivers=[
                DriverData(
                    driverId="DR001",
                    driverName="John Doe",
                    phoneNumber="4155551234",
                    violations=Violations(
                        tripId="TRIP123",
                        violationDetails=[
                            ViolationDetail(
                                type="speeding",
                                description="Driver exceeded speed limit"
                            )
                        ]
                    ),
                    customRules=None
                )
            ]
        )

    @pytest.mark.asyncio
    async def test_phone_normalization_without_country_code(self, sample_batch_request):
        """Test phone number normalization for numbers without country code."""
        # Mock ElevenLabs client call
        mock_response = {
            "conversation_id": "conv_123",
            "callSid": "CA123456"
        }

        with patch('utils.elevenlabs_client.elevenlabs_client.create_outbound_call', new_callable=AsyncMock) as mock_call, \
             patch('models.driver_data.generate_enhanced_conversational_prompt', return_value="Test prompt"), \
             patch('models.driver_data.get_trip_data_for_violations', return_value={}):

            mock_call.return_value = mock_response

            result = await make_drivers_violation_batch_call_elevenlabs(sample_batch_request)

            # Verify phone number was normalized to E.164 format
            call_kwargs = mock_call.call_args.kwargs
            assert call_kwargs["to_number"] == "+14155551234", "Phone should be normalized to +14155551234"

            # Verify response structure
            assert result["driver"]["phoneNumber"] == "+14155551234"

    @pytest.mark.asyncio
    async def test_phone_normalization_with_country_code(self, sample_batch_request):
        """Test phone number normalization for numbers already with country code."""
        # Modify phone number to include country code
        sample_batch_request.drivers[0].phoneNumber = "14155551234"

        mock_response = {
            "conversation_id": "conv_123",
            "callSid": "CA123456"
        }

        with patch('utils.elevenlabs_client.elevenlabs_client.create_outbound_call', new_callable=AsyncMock) as mock_call, \
             patch('models.driver_data.generate_enhanced_conversational_prompt', return_value="Test prompt"), \
             patch('models.driver_data.get_trip_data_for_violations', return_value={}):

            mock_call.return_value = mock_response

            result = await make_drivers_violation_batch_call_elevenlabs(sample_batch_request)

            # Verify phone number was normalized correctly
            call_kwargs = mock_call.call_args.kwargs
            assert call_kwargs["to_number"] == "+14155551234", "Phone should be normalized to +14155551234"

    @pytest.mark.asyncio
    async def test_single_driver_processing(self):
        """Test that only the first driver is processed from drivers array."""
        # Create request with multiple drivers
        multi_driver_request = BatchCallRequest(
            callType="violation",
            timestamp="2025-11-20T10:00:00Z",
            drivers=[
                DriverData(
                    driverId="DR001",
                    driverName="John Doe",
                    phoneNumber="4155551234",
                    violations=Violations(
                        tripId="TRIP123",
                        violationDetails=[
                            ViolationDetail(type="speeding", description="Speeding violation")
                        ]
                    )
                ),
                DriverData(
                    driverId="DR002",
                    driverName="Jane Smith",
                    phoneNumber="4155555678",
                    violations=Violations(
                        tripId="TRIP456",
                        violationDetails=[
                            ViolationDetail(type="fatigue", description="Fatigue violation")
                        ]
                    )
                )
            ]
        )

        mock_response = {
            "conversation_id": "conv_123",
            "callSid": "CA123456"
        }

        with patch('utils.elevenlabs_client.elevenlabs_client.create_outbound_call', new_callable=AsyncMock) as mock_call, \
             patch('models.driver_data.generate_enhanced_conversational_prompt', return_value="Test prompt"), \
             patch('models.driver_data.get_trip_data_for_violations', return_value={}):

            mock_call.return_value = mock_response

            result = await make_drivers_violation_batch_call_elevenlabs(multi_driver_request)

            # Verify only first driver was processed
            assert result["driver"]["driverId"] == "DR001"
            assert result["driver"]["driverName"] == "John Doe"

            # Verify client was called only once
            assert mock_call.call_count == 1

    @pytest.mark.asyncio
    async def test_empty_drivers_array_raises_error(self):
        """Test that empty drivers array raises HTTPException."""
        empty_request = BatchCallRequest(
            callType="violation",
            timestamp="2025-11-20T10:00:00Z",
            drivers=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            await make_drivers_violation_batch_call_elevenlabs(empty_request)

        assert exc_info.value.status_code == 400
        assert "No driver data provided" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_prompt_generation_integration(self, sample_batch_request):
        """Test that prompt generation is integrated correctly with violation data."""
        mock_prompt = "Hello John Doe, this is about your speeding violation on TRIP123"
        mock_response = {
            "conversation_id": "conv_123",
            "callSid": "CA123456"
        }

        with patch('utils.elevenlabs_client.elevenlabs_client.create_outbound_call', new_callable=AsyncMock) as mock_call, \
             patch('models.driver_data.generate_enhanced_conversational_prompt', return_value=mock_prompt) as mock_prompt_gen, \
             patch('models.driver_data.get_trip_data_for_violations', return_value={"some": "data"}):

            mock_call.return_value = mock_response

            result = await make_drivers_violation_batch_call_elevenlabs(sample_batch_request)

            # Verify prompt generation was called
            assert mock_prompt_gen.called

            # Verify prompt was passed to ElevenLabs client
            call_kwargs = mock_call.call_args.kwargs
            assert call_kwargs["prompt"] == mock_prompt, "Generated prompt should be passed to client"

    @pytest.mark.asyncio
    async def test_successful_response_structure(self, sample_batch_request):
        """Test that successful response includes all required fields."""
        mock_response = {
            "conversation_id": "conv_abc123",
            "callSid": "CA987654321"
        }

        with patch('utils.elevenlabs_client.elevenlabs_client.create_outbound_call', new_callable=AsyncMock) as mock_call, \
             patch('models.driver_data.generate_enhanced_conversational_prompt', return_value="Test prompt"), \
             patch('models.driver_data.get_trip_data_for_violations', return_value={}):

            mock_call.return_value = mock_response

            result = await make_drivers_violation_batch_call_elevenlabs(sample_batch_request)

            # Verify response structure
            assert "message" in result
            assert "timestamp" in result
            assert "driver" in result
            assert "conversation_id" in result
            assert "callSid" in result
            assert "triggers_count" in result

            # Verify specific values
            assert result["conversation_id"] == "conv_abc123"
            assert result["callSid"] == "CA987654321"
            assert result["driver"]["driverId"] == "DR001"
            assert result["driver"]["driverName"] == "John Doe"
            assert result["triggers_count"] == 1

    @pytest.mark.asyncio
    async def test_error_handling_client_exception(self, sample_batch_request):
        """Test error handling when ElevenLabs client raises an exception."""
        with patch('utils.elevenlabs_client.elevenlabs_client.create_outbound_call', new_callable=AsyncMock) as mock_call, \
             patch('models.driver_data.generate_enhanced_conversational_prompt', return_value="Test prompt"), \
             patch('models.driver_data.get_trip_data_for_violations', return_value={}):

            mock_call.side_effect = Exception("Network error: Unable to reach API")

            with pytest.raises(HTTPException) as exc_info:
                await make_drivers_violation_batch_call_elevenlabs(sample_batch_request)

            # Verify appropriate error response
            assert exc_info.value.status_code == 500
            assert "Failed to initiate ElevenLabs call" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_prompt_generation_with_trip_data(self, sample_batch_request):
        """Test prompt generation with trip data integration."""
        mock_trip_data = {
            "destination": "Los Angeles",
            "current_location": "San Francisco",
            "miles_remaining": 380.5
        }
        mock_prompt = "Prompt with trip data"
        mock_response = {
            "conversation_id": "conv_123",
            "callSid": "CA123456"
        }

        with patch('utils.elevenlabs_client.elevenlabs_client.create_outbound_call', new_callable=AsyncMock) as mock_call, \
             patch('models.driver_data.generate_enhanced_conversational_prompt', return_value=mock_prompt) as mock_prompt_gen, \
             patch('models.driver_data.get_trip_data_for_violations', return_value=mock_trip_data) as mock_trip_fetch:

            mock_call.return_value = mock_response

            result = await make_drivers_violation_batch_call_elevenlabs(sample_batch_request)

            # Verify trip data was fetched
            assert mock_trip_fetch.called
            trip_fetch_args = mock_trip_fetch.call_args
            assert trip_fetch_args[1]["trip_id"] == "TRIP123"
            assert trip_fetch_args[1]["driver_id"] == "DR001"

            # Verify prompt generation received trip data
            prompt_gen_args = mock_prompt_gen.call_args
            assert prompt_gen_args[1]["trip_data"] == mock_trip_data
