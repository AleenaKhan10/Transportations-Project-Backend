"""
Integration tests for call transcription webhook feature.

These tests verify critical end-to-end workflows and integration points
that are not covered by unit tests in Task Groups 1-3.

Test Coverage:
1. Timezone consistency across complete workflow
2. Concurrent conversations dont interfere  
3. Long message handling
4. Multiple sequential dialogues
5. Driver lookup with null handling
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, delete
from main import app
from models.call import Call, CallStatus
from models.call_transcription import CallTranscription, SpeakerType
from db.database import engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    """Clean up database before and after each test."""
    with Session(engine) as session:
        session.exec(delete(CallTranscription))
        session.exec(delete(Call))
        session.commit()
    yield
    with Session(engine) as session:
        session.exec(delete(CallTranscription))
        session.exec(delete(Call))
        session.commit()


class TestIntegrationTranscriptionWebhook:
    """Integration tests for complete transcription webhook workflows."""

    def test_timezone_consistency_across_complete_workflow(self):
        """Test timezone preservation through complete workflow."""
        conversation_id = "test-timezone-integration"
        timestamp_str = "2025-01-15T14:30:45.123456Z"
        expected_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        
        payload = {
            "conversation_id": conversation_id,
            "speaker": "agent",
            "message": "Testing timezone preservation",
            "timestamp": timestamp_str
        }
        
        response = client.post("/webhooks/elevenlabs/transcription", json=payload)
        assert response.status_code == 201
        
        transcription_id = response.json()["transcription_id"]
        
        with Session(engine) as session:
            call = Call.get_by_conversation_id(conversation_id)
            assert call is not None
            assert call.call_start_time.tzinfo == timezone.utc
            assert abs((call.call_start_time - expected_timestamp).total_seconds()) < 1
            
            transcription = session.get(CallTranscription, transcription_id)
            assert transcription is not None
            assert transcription.timestamp.tzinfo == timezone.utc
            assert abs((transcription.timestamp - expected_timestamp).total_seconds()) < 1

    def test_concurrent_conversations_dont_interfere(self):
        """Test multiple concurrent conversations maintain independent state."""
        base_time = datetime.now(timezone.utc)
        
        conversations = {
            "conv-A": [
                {"speaker": "agent", "message": "Conv A - Message 1", "offset": 0},
                {"speaker": "user", "message": "Conv A - Message 2", "offset": 2},
            ],
            "conv-B": [
                {"speaker": "agent", "message": "Conv B - Message 1", "offset": 1},
                {"speaker": "user", "message": "Conv B - Message 2", "offset": 3},
            ],
        }
        
        for conv_id, messages in conversations.items():
            for msg in messages:
                timestamp = (base_time + timedelta(seconds=msg["offset"])).isoformat()
                payload = {
                    "conversation_id": conv_id,
                    "speaker": msg["speaker"],
                    "message": msg["message"],
                    "timestamp": timestamp
                }
                response = client.post("/webhooks/elevenlabs/transcription", json=payload)
                assert response.status_code == 201
        
        with Session(engine) as session:
            transcriptions_a = CallTranscription.get_by_conversation_id("conv-A")
            assert len(transcriptions_a) == 2
            assert [t.sequence_number for t in transcriptions_a] == [1, 2]
            
            transcriptions_b = CallTranscription.get_by_conversation_id("conv-B")
            assert len(transcriptions_b) == 2
            assert [t.sequence_number for t in transcriptions_b] == [1, 2]

    def test_long_message_handling_text_field(self):
        """Test Text field handles very long dialogue messages."""
        conversation_id = "test-long-message"
        long_message = "This is a very long message. " * 300
        assert len(long_message) > 9000
        
        payload = {
            "conversation_id": conversation_id,
            "speaker": "agent",
            "message": long_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        response = client.post("/webhooks/elevenlabs/transcription", json=payload)
        assert response.status_code == 201
        
        transcription_id = response.json()["transcription_id"]
        
        with Session(engine) as session:
            transcription = session.get(CallTranscription, transcription_id)
            assert transcription is not None
            assert len(transcription.message_text) == len(long_message)

    def test_realistic_conversation_flow(self):
        """Test realistic conversation flow simulating a real driver call."""
        conversation_id = "test-realistic"
        base_time = datetime.now(timezone.utc)
        
        conversation_flow = [
            {"speaker": "agent", "message": "Hello, this is dispatch.", "offset": 0},
            {"speaker": "user", "message": "Yes, this is John.", "offset": 5},
            {"speaker": "agent", "message": "We detected a hard braking event.", "offset": 8},
            {"speaker": "user", "message": "A car cut me off suddenly.", "offset": 15},
        ]
        
        for i, dialogue in enumerate(conversation_flow, start=1):
            timestamp = (base_time + timedelta(seconds=dialogue["offset"])).isoformat()
            payload = {
                "conversation_id": conversation_id,
                "speaker": dialogue["speaker"],
                "message": dialogue["message"],
                "timestamp": timestamp
            }
            
            response = client.post("/webhooks/elevenlabs/transcription", json=payload)
            assert response.status_code == 201
            assert response.json()["sequence_number"] == i
        
        with Session(engine) as session:
            transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
            assert len(transcriptions) == 4
            assert [t.sequence_number for t in transcriptions] == [1, 2, 3, 4]

    def test_driver_lookup_with_null_handling(self):
        """Test driver lookup integration with graceful null handling."""
        conversation_id = "test-unknown-driver"
        
        payload = {
            "conversation_id": conversation_id,
            "speaker": "agent",
            "message": "Testing unknown driver handling.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        response = client.post("/webhooks/elevenlabs/transcription", json=payload)
        assert response.status_code == 201
        
        with Session(engine) as session:
            call = Call.get_by_conversation_id(conversation_id)
            assert call is not None
            assert call.driver_id is None
            assert call.status == CallStatus.IN_PROGRESS
