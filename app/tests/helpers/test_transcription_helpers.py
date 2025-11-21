"""
Tests for refactored transcription helper functions.

Focused tests covering critical helper behaviors:
- lookup_driver_id_by_call_sid returns correct driver_id
- get_conversation_id_from_call_sid two-step lookup
- get_conversation_id_from_call_sid raises ValueError for NULL conversation_id
- generate_sequence_number with call_sid parameter
- save_transcription end-to-end with call_sid
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import Session
from models.call import Call, CallStatus
from models.call_transcription import CallTranscription, SpeakerType
from helpers.transcription_helpers import (
    lookup_driver_id_by_call_sid,
    get_conversation_id_from_call_sid,
    generate_sequence_number,
    save_transcription
)
from db.database import engine


class TestTranscriptionHelpers:
    """Test refactored helper functions for call_sid workflow."""

    def test_lookup_driver_id_by_call_sid_returns_correct_value(self):
        """Test that lookup_driver_id_by_call_sid returns correct driver_id."""
        call_sid = "EL_555_test_lookup_driver"
        driver_id = 555

        # Create test call
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=driver_id,
            call_start_time=datetime.now(timezone.utc)
        )

        try:
            # Lookup driver_id
            result = lookup_driver_id_by_call_sid(call_sid)

            # Verify correct driver_id returned
            assert result == driver_id

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_get_conversation_id_from_call_sid_two_step_lookup(self):
        """Test that get_conversation_id_from_call_sid performs two-step lookup."""
        call_sid = "EL_666_test_conv_lookup"
        conversation_id = "conv_test_666"

        # Create call with conversation_id
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=666,
            call_start_time=datetime.now(timezone.utc)
        )
        Call.update_conversation_id(call_sid, conversation_id)

        try:
            # Perform two-step lookup
            result = get_conversation_id_from_call_sid(call_sid)

            # Verify correct conversation_id returned
            assert result == conversation_id

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_get_conversation_id_raises_error_for_null_conversation_id(self):
        """Test that get_conversation_id_from_call_sid raises ValueError for NULL conversation_id."""
        call_sid = "EL_777_test_null_conv"

        # Create call WITHOUT conversation_id (API hasn't completed)
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=777,
            call_start_time=datetime.now(timezone.utc)
        )

        try:
            # Attempt lookup - should raise ValueError
            with pytest.raises(ValueError, match="has no conversation_id"):
                get_conversation_id_from_call_sid(call_sid)

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_generate_sequence_number_with_call_sid(self):
        """Test that generate_sequence_number works with call_sid parameter."""
        call_sid = "EL_888_test_seq"
        conversation_id = "conv_test_888"

        # Create call with conversation_id
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=888,
            call_start_time=datetime.now(timezone.utc)
        )
        Call.update_conversation_id(call_sid, conversation_id)

        try:
            # Generate sequence number using call_sid
            seq_num = generate_sequence_number(call_sid)

            # First sequence number should be 1
            assert seq_num == 1

            # Create a transcription
            CallTranscription.create_transcription(
                conversation_id=conversation_id,
                speaker_type=SpeakerType.AGENT,
                message_text="Test message",
                timestamp=datetime.now(timezone.utc),
                sequence_number=seq_num
            )

            # Generate next sequence number
            next_seq_num = generate_sequence_number(call_sid)

            # Should be 2
            assert next_seq_num == 2

        finally:
            # Cleanup
            with Session(engine) as session:
                # Delete transcriptions
                transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
                for t in transcriptions:
                    session.delete(t)
                # Delete call
                session.delete(call)
                session.commit()

    def test_save_transcription_end_to_end_with_call_sid(self):
        """Test save_transcription end-to-end using call_sid."""
        call_sid = "EL_999_test_save_trans"
        conversation_id = "conv_test_999"

        # Create call with conversation_id
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=999,
            call_start_time=datetime.now(timezone.utc)
        )
        Call.update_conversation_id(call_sid, conversation_id)

        try:
            # Save transcription using call_sid
            transcription_id, sequence_number = save_transcription(
                call_sid=call_sid,
                speaker="agent",
                message="Test transcription message",
                timestamp=datetime.now(timezone.utc)
            )

            # Verify transcription saved
            assert transcription_id is not None
            assert sequence_number == 1

            # Verify transcription exists in database
            transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
            assert len(transcriptions) == 1
            assert transcriptions[0].message_text == "Test transcription message"
            assert transcriptions[0].speaker_type == SpeakerType.AGENT

        finally:
            # Cleanup
            with Session(engine) as session:
                # Delete transcriptions
                transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
                for t in transcriptions:
                    session.delete(t)
                # Delete call
                session.delete(call)
                session.commit()

    def test_save_transcription_fails_for_missing_call_sid(self):
        """Test that save_transcription raises error for non-existent call_sid."""
        call_sid = "EL_NONEXISTENT_999999"

        # Attempt to save transcription with non-existent call_sid
        with pytest.raises(ValueError, match="Call record not found"):
            save_transcription(
                call_sid=call_sid,
                speaker="agent",
                message="This should fail",
                timestamp=datetime.now(timezone.utc)
            )
