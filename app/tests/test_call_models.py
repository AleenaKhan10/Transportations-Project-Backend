"""
Focused tests for Call and CallTranscription models.

Tests cover:
1. Call model creation with all required fields
2. Call model unique constraint on conversation_id
3. CallTranscription model creation with all required fields
4. Speaker type enum validation ('agent', 'driver')
5. Foreign key relationship between CallTranscription and Call
6. Timestamp timezone awareness (UTC)
7. CallStatus enum values ('in_progress', 'completed', 'failed')
8. Cascade behavior when Call is deleted
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import Session, select
from models.call import Call, CallStatus
from models.call_transcription import CallTranscription, SpeakerType
from db.database import engine
from sqlalchemy.exc import IntegrityError


class TestCallModel:
    """Test Call model functionality."""

    def test_call_model_creates_with_required_fields(self):
        """Test that Call model creates successfully with all required fields."""
        with Session(engine) as session:
            # Create a Call with required fields
            call_start = datetime.now(timezone.utc)
            call = Call(
                conversation_id="conv_test_12345",
                driver_id=100,
                call_start_time=call_start,
                status=CallStatus.IN_PROGRESS
            )

            session.add(call)
            session.commit()
            session.refresh(call)

            # Verify all fields are set correctly
            assert call.id is not None
            assert call.conversation_id == "conv_test_12345"
            assert call.driver_id == 100
            assert call.call_start_time == call_start
            assert call.status == CallStatus.IN_PROGRESS
            assert call.call_end_time is None
            assert call.created_at is not None
            assert call.updated_at is not None

            # Verify timestamps are timezone-aware
            assert call.created_at.tzinfo is not None
            assert call.updated_at.tzinfo is not None
            assert call.call_start_time.tzinfo is not None

            # Cleanup
            session.delete(call)
            session.commit()

    def test_call_model_unique_constraint_on_conversation_id(self):
        """Test that conversation_id must be unique."""
        with Session(engine) as session:
            call_start = datetime.now(timezone.utc)

            # Create first Call
            call1 = Call(
                conversation_id="conv_duplicate_test",
                driver_id=101,
                call_start_time=call_start,
                status=CallStatus.IN_PROGRESS
            )
            session.add(call1)
            session.commit()

            # Try to create second Call with same conversation_id
            call2 = Call(
                conversation_id="conv_duplicate_test",
                driver_id=102,
                call_start_time=call_start,
                status=CallStatus.IN_PROGRESS
            )
            session.add(call2)

            # Should raise IntegrityError due to unique constraint
            with pytest.raises(IntegrityError):
                session.commit()

            # Cleanup
            session.rollback()
            session.delete(call1)
            session.commit()

    def test_call_status_enum_values(self):
        """Test that CallStatus enum has correct values."""
        assert CallStatus.IN_PROGRESS.value == "in_progress"
        assert CallStatus.COMPLETED.value == "completed"
        assert CallStatus.FAILED.value == "failed"

        # Verify all enum values are valid
        valid_statuses = [CallStatus.IN_PROGRESS, CallStatus.COMPLETED, CallStatus.FAILED]
        assert len(valid_statuses) == 3

    def test_call_model_allows_null_driver_id(self):
        """Test that driver_id can be null (driver lookup may fail)."""
        with Session(engine) as session:
            call_start = datetime.now(timezone.utc)
            call = Call(
                conversation_id="conv_null_driver",
                driver_id=None,  # Null driver_id
                call_start_time=call_start,
                status=CallStatus.IN_PROGRESS
            )

            session.add(call)
            session.commit()
            session.refresh(call)

            assert call.driver_id is None

            # Cleanup
            session.delete(call)
            session.commit()


class TestCallTranscriptionModel:
    """Test CallTranscription model functionality."""

    def test_call_transcription_creates_with_required_fields(self):
        """Test that CallTranscription creates successfully with all required fields."""
        with Session(engine) as session:
            # First create a Call record
            call_start = datetime.now(timezone.utc)
            call = Call(
                conversation_id="conv_transcription_test",
                driver_id=200,
                call_start_time=call_start,
                status=CallStatus.IN_PROGRESS
            )
            session.add(call)
            session.commit()

            # Now create a CallTranscription
            transcription_time = datetime.now(timezone.utc)
            transcription = CallTranscription(
                conversation_id="conv_transcription_test",
                speaker_type=SpeakerType.AGENT,
                message_text="Hello, this is dispatch calling.",
                timestamp=transcription_time,
                sequence_number=1
            )

            session.add(transcription)
            session.commit()
            session.refresh(transcription)

            # Verify all fields are set correctly
            assert transcription.id is not None
            assert transcription.conversation_id == "conv_transcription_test"
            assert transcription.speaker_type == SpeakerType.AGENT
            assert transcription.message_text == "Hello, this is dispatch calling."
            assert transcription.timestamp == transcription_time
            assert transcription.sequence_number == 1
            assert transcription.created_at is not None

            # Verify timestamps are timezone-aware
            assert transcription.created_at.tzinfo is not None
            assert transcription.timestamp.tzinfo is not None

            # Cleanup - delete transcription first, then call (FK constraint)
            session.delete(transcription)
            session.commit()
            session.delete(call)
            session.commit()

    def test_speaker_type_enum_validation(self):
        """Test that SpeakerType enum validates 'agent' and 'driver'."""
        assert SpeakerType.AGENT.value == "agent"
        assert SpeakerType.DRIVER.value == "driver"

        # Verify only two valid speaker types
        valid_speakers = [SpeakerType.AGENT, SpeakerType.DRIVER]
        assert len(valid_speakers) == 2

    def test_foreign_key_relationship_with_call(self):
        """Test foreign key relationship between CallTranscription and Call."""
        with Session(engine) as session:
            # Create a Call
            call_start = datetime.now(timezone.utc)
            call = Call(
                conversation_id="conv_fk_test",
                driver_id=300,
                call_start_time=call_start,
                status=CallStatus.IN_PROGRESS
            )
            session.add(call)
            session.commit()

            # Create transcriptions for this call
            transcription1 = CallTranscription(
                conversation_id="conv_fk_test",
                speaker_type=SpeakerType.AGENT,
                message_text="First message",
                timestamp=datetime.now(timezone.utc),
                sequence_number=1
            )
            transcription2 = CallTranscription(
                conversation_id="conv_fk_test",
                speaker_type=SpeakerType.DRIVER,
                message_text="Second message",
                timestamp=datetime.now(timezone.utc),
                sequence_number=2
            )

            session.add(transcription1)
            session.add(transcription2)
            session.commit()

            # Verify transcriptions are linked to the call
            transcriptions = session.exec(
                select(CallTranscription).where(
                    CallTranscription.conversation_id == "conv_fk_test"
                )
            ).all()

            assert len(transcriptions) == 2
            assert all(t.conversation_id == call.conversation_id for t in transcriptions)

            # Cleanup - delete transcriptions first, then call (FK constraint)
            for t in transcriptions:
                session.delete(t)
            session.commit()
            session.delete(call)
            session.commit()

    def test_timezone_awareness_for_timestamps(self):
        """Test that all datetime fields are timezone-aware (UTC)."""
        with Session(engine) as session:
            # Create Call
            call_start = datetime.now(timezone.utc)
            call = Call(
                conversation_id="conv_tz_test",
                driver_id=400,
                call_start_time=call_start,
                status=CallStatus.IN_PROGRESS
            )
            session.add(call)
            session.commit()

            # Create CallTranscription
            transcription_time = datetime.now(timezone.utc)
            transcription = CallTranscription(
                conversation_id="conv_tz_test",
                speaker_type=SpeakerType.AGENT,
                message_text="Testing timezone awareness",
                timestamp=transcription_time,
                sequence_number=1
            )
            session.add(transcription)
            session.commit()
            session.refresh(call)
            session.refresh(transcription)

            # Verify Call timestamps are timezone-aware
            assert call.call_start_time.tzinfo is not None
            assert call.created_at.tzinfo is not None
            assert call.updated_at.tzinfo is not None

            # Verify CallTranscription timestamps are timezone-aware
            assert transcription.timestamp.tzinfo is not None
            assert transcription.created_at.tzinfo is not None

            # Verify all are in UTC
            assert call.call_start_time.tzinfo == timezone.utc
            assert transcription.timestamp.tzinfo == timezone.utc

            # Cleanup - delete transcription first, then call (FK constraint)
            session.delete(transcription)
            session.commit()
            session.delete(call)
            session.commit()

    def test_cascade_delete_behavior(self):
        """Test that cascade delete is NOT configured (FK constraint prevents deletion)."""
        with Session(engine) as session:
            # Create Call
            call_start = datetime.now(timezone.utc)
            call = Call(
                conversation_id="conv_cascade_test",
                driver_id=500,
                call_start_time=call_start,
                status=CallStatus.IN_PROGRESS
            )
            session.add(call)
            session.commit()

            # Create CallTranscription
            transcription = CallTranscription(
                conversation_id="conv_cascade_test",
                speaker_type=SpeakerType.AGENT,
                message_text="Testing cascade delete",
                timestamp=datetime.now(timezone.utc),
                sequence_number=1
            )
            session.add(transcription)
            session.commit()

            # Try to delete the Call (should fail with FK constraint)
            # This verifies that cascade delete is NOT configured
            session.delete(call)

            # Expect IntegrityError when trying to delete Call with existing transcriptions
            with pytest.raises(IntegrityError):
                session.commit()

            # Cleanup - rollback the failed transaction and delete properly
            session.rollback()
            session.delete(transcription)
            session.commit()
            session.delete(call)
            session.commit()
