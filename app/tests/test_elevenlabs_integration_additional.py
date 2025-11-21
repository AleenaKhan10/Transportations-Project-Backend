# Additional strategic tests for ElevenLabs integration (5 tests)
import pytest
from unittest.mock import AsyncMock, patch
from models.vapi import BatchCallRequest, DriverData, Violations, ViolationDetail
from models.driver_data import make_drivers_violation_batch_call_elevenlabs

@pytest.mark.asyncio
async def test_phone_with_plus_prefix():
    req = BatchCallRequest(callType="v", timestamp="2025-11-20T10:00:00Z",
        drivers=[DriverData(driverId="D1", driverName="Test", phoneNumber="+14155551234",
            violations=Violations(tripId="T1", violationDetails=[ViolationDetail(type="s", description="t")]))])
    with patch("utils.elevenlabs_client.elevenlabs_client.create_outbound_call", new_callable=AsyncMock) as m, \n         patch("models.driver_data.generate_enhanced_conversational_prompt", return_value="p"), \n         patch("models.driver_data.get_trip_data_for_violations", return_value={}):
        m.return_value = {"conversation_id": "c1", "callSid": "s1"}
        await make_drivers_violation_batch_call_elevenlabs(req)
        assert m.call_args.kwargs["to_number"] == "+14155551234"

@pytest.mark.asyncio
async def test_missing_trip_id():
    req = BatchCallRequest(callType="v", timestamp="2025-11-20T10:00:00Z",
        drivers=[DriverData(driverId="D1", driverName="Test", phoneNumber="4155551234",
            violations=Violations(tripId=None, violationDetails=[ViolationDetail(type="s", description="t")]))])
    with patch("utils.elevenlabs_client.elevenlabs_client.create_outbound_call", new_callable=AsyncMock) as m, \n         patch("models.driver_data.generate_enhanced_conversational_prompt", return_value="p"), \n         patch("models.driver_data.get_trip_data_for_violations", return_value={}) as mt:
        m.return_value = {"conversation_id": "c1", "callSid": "s1"}
        await make_drivers_violation_batch_call_elevenlabs(req)
        assert mt.called

@pytest.mark.asyncio
async def test_empty_violations():
    req = BatchCallRequest(callType="v", timestamp="2025-11-20T10:00:00Z",
        drivers=[DriverData(driverId="D1", driverName="Test", phoneNumber="4155551234",
            violations=Violations(tripId="T1", violationDetails=[]))])
    with patch("utils.elevenlabs_client.elevenlabs_client.create_outbound_call", new_callable=AsyncMock) as m, \n         patch("models.driver_data.generate_enhanced_conversational_prompt", return_value="p"), \n         patch("models.driver_data.get_trip_data_for_violations", return_value={}):
        m.return_value = {"conversation_id": "c1", "callSid": "s1"}
        r = await make_drivers_violation_batch_call_elevenlabs(req)
        assert r["triggers_count"] == 0

@pytest.mark.asyncio
async def test_response_fields_complete():
    req = BatchCallRequest(callType="v", timestamp="2025-11-20T10:00:00Z",
        drivers=[DriverData(driverId="D1", driverName="Test", phoneNumber="4155551234",
            violations=Violations(tripId="T1", violationDetails=[ViolationDetail(type="s", description="t")]))])
    with patch("utils.elevenlabs_client.elevenlabs_client.create_outbound_call", new_callable=AsyncMock) as m, \n         patch("models.driver_data.generate_enhanced_conversational_prompt", return_value="p"), \n         patch("models.driver_data.get_trip_data_for_violations", return_value={}):
        m.return_value = {"conversation_id": "c1", "callSid": "s1"}
        r = await make_drivers_violation_batch_call_elevenlabs(req)
        assert all(k in r for k in ["message", "timestamp", "driver", "conversation_id", "callSid", "triggers_count"])

@pytest.mark.asyncio
async def test_trip_data_none_handling():
    req = BatchCallRequest(callType="v", timestamp="2025-11-20T10:00:00Z",
        drivers=[DriverData(driverId="D1", driverName="Test", phoneNumber="4155551234",
            violations=Violations(tripId="T1", violationDetails=[ViolationDetail(type="s", description="t")]))])
    with patch("utils.elevenlabs_client.elevenlabs_client.create_outbound_call", new_callable=AsyncMock) as m, \n         patch("models.driver_data.generate_enhanced_conversational_prompt", return_value="p"), \n         patch("models.driver_data.get_trip_data_for_violations", return_value=None):
        m.return_value = {"conversation_id": "c1", "callSid": "s1"}
        r = await make_drivers_violation_batch_call_elevenlabs(req)
        assert r["conversation_id"] == "c1"
