"""
Focused tests for transcription helper functions (Business Logic Layer).

Tests cover:
1. Driver lookup returns correct driver_id for valid conversation_id
2. Driver lookup returns None for unknown conversation_id
3. Sequence number generation returns 1 for first transcription
4. Sequence number generation returns correct count + 1 for existing transcriptions
5. Speaker mapping from 'user' to 'driver'
6. Speaker mapping from 'agent' to 'agent'
7. Call initialization creates Call record on first dialogue
8. Call initialization skips creation if Call already exists
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import Session, select
from models.call import Call, CallStatus
from models.call_transcription import CallTranscription, SpeakerType
from db.database import engine
from helpers.transcription_helpers import (
    lookup_driver_id_by_conversation,
    generate_sequence_number,
    map_speaker_to_internal,
    ensure_call_exists,
    save_transcription
)


class TestDriverLookup:
    """Test driver lookup functionality."""

    def test_driver_lookup_returns_none_for_unknown_conversation(self):
        """Test that driver lookup returns None for unknown conversation_id."""
        # Query for a non-existent conversation_id
        driver_id = lookup_driver_id_by_conversation("conv_nonexistent_12345")

        # Should return None
        assert driver_id is None

    def test_driver_lookup_returns_correct_driver_id_for_valid_conversation(self):
        """Test that driver lookup returns correct driver_id for valid conversation_id."""
        with Session(engine) as session:
            # Create a Call with driver_id
            call_start = datetime.now(timezone.utc)
            call = Call(
                conversation_id="conv_driver_lookup_test",
                driver_id=999,
                call_start_time=call_start,
                status=CallStatus.IN_PROGRESS
            )
            session.add(call)
            session.commit()

        try:
            # Lookup driver_id
            driver_id = lookup_driver_id_by_conversation("conv_driver_lookup_test")

            # Should return the correct driver_id
            assert driver_id == 999
        finally:
            # Cleanup
            with Session(engine) as session:
                call = session.exec(
                    select(Call).where(Call.conversation_id == "conv_driver_lookup_test")
                ).first()
                if call:
                    session.delete(call)
                    session.commit()


class TestSequenceNumberGeneration:
    """Test sequence number generation functionality."""

    def test_sequence_number_returns_one_for_first_transcription(self):
        """Test that sequence number returns 1 for first transcription."""
        # Generate sequence number for conversation with no transcriptions
        sequence_number = generate_sequence_number("conv_seq_first")

        # Should return 1
        assert sequence_number == 1

    def test_sequence_number_increments_for_existing_transcriptions(self):
        """Test that sequence number returns correct count + 1 for existing transcriptions."""
        with Session(engine) as session:
            # Create a Call
            call_start = datetime.now(timezone.utc)
            call = Call(
                conversation_id="conv_seq_test",
                driver_id=888,
                call_start_time=call_start,
                status=CallStatus.IN_PROGRESS
            )
            session.add(call)
            session.commit()

            # Create 3 existing transcriptions
            for i in range(1, 4):
                transcription = CallTranscription(
                    conversation_id="conv_seq_test",
                    speaker_type=SpeakerType.AGENT,
                    message_text=f"Message {i}",
                    timestamp=datetime.now(timezone.utc),
                    sequence_number=i
                )
                session.add(transcription)
            session.commit()

        try:
            # Generate sequence number for next transcription
            sequence_number = generate_sequence_number("conv_seq_test")

            # Should return 4 (count of 3 existing + 1)
            assert sequence_number == 4
        finally:
            # Cleanup
            with Session(engine) as session:
                transcriptions = session.exec(
                    select(CallTranscription).where(
                        CallTranscription.conversation_id == "conv_seq_test"
                    )
                ).all()
                for t in transcriptions:
                    session.delete(t)
                session.commit()

                call = session.exec(
                    select(Call).where(Call.conversation_id == "conv_seq_test")
                ).first()
                if call:
                    session.delete(call)
                    session.commit()


class TestSpeakerMapping:
    """Test speaker mapping functionality."""

    def test_speaker_mapping_user_to_driver(self):
        """Test that 'user' maps to SpeakerType.DRIVER."""
        speaker_type = map_speaker_to_internal("user")
        assert speaker_type == SpeakerType.DRIVER

    def test_speaker_mapping_agent_to_agent(self):
        """Test that 'agent' maps to SpeakerType.AGENT."""
        speaker_type = map_speaker_to_internal("agent")
        assert speaker_type == SpeakerType.AGENT

    def test_speaker_mapping_invalid_speaker_raises_error(self):
        """Test that invalid speaker value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid speaker"):
            map_speaker_to_internal("invalid_speaker")


class TestCallInitialization:
    """Test call initialization functionality."""

    def test_call_initialization_creates_call_on_first_dialogue(self):
        """Test that call initialization creates Call record on first dialogue."""
        try:
            # Ensure call exists (should create new)
            timestamp = datetime.now(timezone.utc)
            call = ensure_call_exists("conv_init_first", timestamp)

            # Verify Call was created
            assert call is not None
            assert call.conversation_id == "conv_init_first"
            assert call.call_start_time == timestamp
            assert call.status == CallStatus.IN_PROGRESS
            assert call.driver_id is None  # No driver_id lookup for test
        finally:
            # Cleanup
            with Session(engine) as session:
                call = session.exec(
                    select(Call).where(Call.conversation_id == "conv_init_first")
                ).first()
                if call:
                    session.delete(call)
                    session.commit()

    def test_call_initialization_skips_creation_if_call_exists(self):
        """Test that call initialization skips creation if Call already exists."""
        with Session(engine) as session:
            # Create a Call manually
            call_start = datetime.now(timezone.utc)
            existing_call = Call(
                conversation_id="conv_init_exists",
                driver_id=777,
                call_start_time=call_start,
                status=CallStatus.IN_PROGRESS
            )
            session.add(existing_call)
            session.commit()
            existing_call_id = existing_call.id

        try:
            # Ensure call exists (should return existing)
            new_timestamp = datetime.now(timezone.utc)
            call = ensure_call_exists("conv_init_exists", new_timestamp)

            # Verify existing Call was returned (not created)
            assert call is not None
            assert call.id == existing_call_id
            assert call.conversation_id == "conv_init_exists"
            assert call.driver_id == 777
            assert call.call_start_time == call_start  # Original timestamp preserved
            assert call.call_start_time != new_timestamp  # Not updated
        finally:
            # Cleanup
            with Session(engine) as session:
                call = session.exec(
                    select(Call).where(Call.conversation_id == "conv_init_exists")
                ).first()
                if call:
                    session.delete(call)
                    session.commit()


class TestMainOrchestration:
    """Test main transcription save orchestration."""

    def test_save_transcription_orchestrates_full_workflow(self):
        """Test that save_transcription orchestrates the entire workflow."""
        try:
            # Save a transcription (first dialogue)
            timestamp = datetime.now(timezone.utc)
            transcription_id, sequence_number = save_transcription(
                conversation_id="conv_orchestration_test",
                speaker="agent",
                message="Hello, this is dispatch.",
                timestamp=timestamp
            )

            # Verify transcription was created
            assert transcription_id is not None
            assert sequence_number == 1

            # Verify Call was created
            with Session(engine) as session:
                call = session.exec(
                    select(Call).where(Call.conversation_id == "conv_orchestration_test")
                ).first()
                assert call is not None
                assert call.conversation_id == "conv_orchestration_test"

                # Verify transcription was created
                transcription = session.exec(
                    select(CallTranscription).where(CallTranscription.id == transcription_id)
                ).first()
                assert transcription is not None
                assert transcription.conversation_id == "conv_orchestration_test"
                assert transcription.speaker_type == SpeakerType.AGENT
                assert transcription.message_text == "Hello, this is dispatch."
                assert transcription.sequence_number == 1

            # Save another transcription (second dialogue)
            timestamp2 = datetime.now(timezone.utc)
            transcription_id2, sequence_number2 = save_transcription(
                conversation_id="conv_orchestration_test",
                speaker="user",
                message="Hi, this is the driver.",
                timestamp=timestamp2
            )

            # Verify second transcription
            assert transcription_id2 is not None
            assert sequence_number2 == 2

            with Session(engine) as session:
                transcription2 = session.exec(
                    select(CallTranscription).where(CallTranscription.id == transcription_id2)
                ).first()
                assert transcription2 is not None
                assert transcription2.speaker_type == SpeakerType.DRIVER  # 'user' mapped to 'driver'
                assert transcription2.sequence_number == 2
        finally:
            # Cleanup
            with Session(engine) as session:
                transcriptions = session.exec(
                    select(CallTranscription).where(
                        CallTranscription.conversation_id == "conv_orchestration_test"
                    )
                ).all()
                for t in transcriptions:
                    session.delete(t)
                session.commit()

                call = session.exec(
                    select(Call).where(Call.conversation_id == "conv_orchestration_test")
                ).first()
                if call:
                    session.delete(call)
                    session.commit()
