"""
Focused tests for ElevenLabs FastAPI endpoint.

Tests cover:
1. Endpoint accepts BatchCallRequest and returns proper response
2. Request validation and error handling
3. Error response format when batch call fails
4. Successful call response structure
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from main import app
from models.vapi import BatchCallRequest, DriverData, Violations, ViolationDetail


class TestElevenLabsEndpoint:
    """Test suite for /driver_data/call-elevenlabs endpoint."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def valid_payload(self):
        """Create valid BatchCallRequest payload."""
        return {
            "callType": "violation",
            "timestamp": "2025-11-20T10:00:00Z",
            "drivers": [
                {
                    "driverId": "DR001",
                    "driverName": "John Doe",
                    "phoneNumber": "4155551234",
                    "violations": {
                        "tripId": "TRIP123",
                        "violationDetails": [
                            {
                                "type": "speeding",
                                "description": "Driver exceeded speed limit"
                            }
                        ]
                    },
                    "customRules": None
                }
            ]
        }

    def test_endpoint_accepts_valid_request(self, client, valid_payload):
        """Test endpoint accepts valid BatchCallRequest and returns 200."""
        mock_response = {
            "message": "Call initiated successfully via ElevenLabs",
            "timestamp": "2025-11-20T10:00:00Z",
            "driver": {
                "driverId": "DR001",
                "driverName": "John Doe",
                "phoneNumber": "+14155551234"
            },
            "conversation_id": "conv_123abc",
            "callSid": "CA987654321",
            "triggers_count": 1
        }

        with patch('services.driver_data.make_drivers_violation_batch_call_elevenlabs', new_callable=AsyncMock) as mock_batch_call:
            mock_batch_call.return_value = mock_response

            response = client.post("/driver_data/call-elevenlabs", json=valid_payload)

            assert response.status_code == 200
            result = response.json()
            assert result["message"] == "Call initiated successfully via ElevenLabs"
            assert result["conversation_id"] == "conv_123abc"
            assert result["driver"]["driverId"] == "DR001"

    def test_endpoint_returns_proper_response_structure(self, client, valid_payload):
        """Test endpoint returns response with all required fields."""
        mock_response = {
            "message": "Call initiated successfully via ElevenLabs",
            "timestamp": "2025-11-20T10:00:00Z",
            "driver": {
                "driverId": "DR001",
                "driverName": "John Doe",
                "phoneNumber": "+14155551234"
            },
            "conversation_id": "conv_xyz789",
            "callSid": "CA123456789",
            "triggers_count": 2
        }

        with patch('services.driver_data.make_drivers_violation_batch_call_elevenlabs', new_callable=AsyncMock) as mock_batch_call:
            mock_batch_call.return_value = mock_response

            response = client.post("/driver_data/call-elevenlabs", json=valid_payload)

            assert response.status_code == 200
            result = response.json()

            # Verify all required fields are present
            assert "message" in result
            assert "timestamp" in result
            assert "driver" in result
            assert "conversation_id" in result
            assert "callSid" in result
            assert "triggers_count" in result

            # Verify driver sub-fields
            assert "driverId" in result["driver"]
            assert "driverName" in result["driver"]
            assert "phoneNumber" in result["driver"]

    def test_endpoint_validation_rejects_invalid_payload(self, client):
        """Test endpoint rejects invalid payload with 422 validation error."""
        invalid_payload = {
            "callType": "violation",
            # Missing required timestamp field
            "drivers": []
        }

        response = client.post("/driver_data/call-elevenlabs", json=invalid_payload)

        assert response.status_code == 422
        result = response.json()
        assert "detail" in result

    def test_endpoint_handles_batch_call_http_exception(self, client, valid_payload):
        """Test endpoint handles HTTPException from batch call function."""
        from fastapi import HTTPException

        with patch('services.driver_data.make_drivers_violation_batch_call_elevenlabs', new_callable=AsyncMock) as mock_batch_call:
            # Simulate HTTPException from business logic
            mock_batch_call.side_effect = HTTPException(status_code=400, detail="No driver data provided")

            response = client.post("/driver_data/call-elevenlabs", json=valid_payload)

            # HTTPException should be re-raised with original status code
            assert response.status_code == 400
            result = response.json()
            assert result["detail"] == "No driver data provided"

    def test_endpoint_handles_general_exception(self, client, valid_payload):
        """Test endpoint handles general exceptions with 500 error."""
        with patch('services.driver_data.make_drivers_violation_batch_call_elevenlabs', new_callable=AsyncMock) as mock_batch_call:
            # Simulate unexpected error
            mock_batch_call.side_effect = Exception("Unexpected error occurred")

            response = client.post("/driver_data/call-elevenlabs", json=valid_payload)

            # General exception should return 500
            assert response.status_code == 500
            result = response.json()
            assert "detail" in result

    def test_endpoint_with_multiple_violations(self, client):
        """Test endpoint with request containing multiple violations."""
        payload = {
            "callType": "violation",
            "timestamp": "2025-11-20T11:30:00Z",
            "drivers": [
                {
                    "driverId": "DR002",
                    "driverName": "Jane Smith",
                    "phoneNumber": "4155555678",
                    "violations": {
                        "tripId": "TRIP456",
                        "violationDetails": [
                            {
                                "type": "speeding",
                                "description": "Exceeded speed limit"
                            },
                            {
                                "type": "fatigue",
                                "description": "Driving while fatigued"
                            }
                        ]
                    }
                }
            ]
        }

        mock_response = {
            "message": "Call initiated successfully via ElevenLabs",
            "timestamp": "2025-11-20T11:30:00Z",
            "driver": {
                "driverId": "DR002",
                "driverName": "Jane Smith",
                "phoneNumber": "+14155555678"
            },
            "conversation_id": "conv_multi_violations",
            "callSid": "CA555666777",
            "triggers_count": 2
        }

        with patch('services.driver_data.make_drivers_violation_batch_call_elevenlabs', new_callable=AsyncMock) as mock_batch_call:
            mock_batch_call.return_value = mock_response

            response = client.post("/driver_data/call-elevenlabs", json=payload)

            assert response.status_code == 200
            result = response.json()
            assert result["triggers_count"] == 2
            assert result["driver"]["driverName"] == "Jane Smith"

    def test_endpoint_empty_drivers_array(self, client):
        """Test endpoint with empty drivers array returns 400."""
        payload = {
            "callType": "violation",
            "timestamp": "2025-11-20T10:00:00Z",
            "drivers": []
        }

        from fastapi import HTTPException

        with patch('services.driver_data.make_drivers_violation_batch_call_elevenlabs', new_callable=AsyncMock) as mock_batch_call:
            mock_batch_call.side_effect = HTTPException(status_code=400, detail="No driver data provided")

            response = client.post("/driver_data/call-elevenlabs", json=payload)

            assert response.status_code == 400
            result = response.json()
            assert "No driver data provided" in result["detail"]
