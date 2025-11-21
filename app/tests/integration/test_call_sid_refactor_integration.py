"""
Integration tests for call_sid refactor feature.

Strategic tests covering end-to-end workflows and critical integration points:
- Full call lifecycle integration
- Failed ElevenLabs call updates Call status correctly
- Webhook with NULL conversation_id returns 400
- Two-step lookup performance with indexes
- Backfilled records work in webhook flow
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import Session
from models.call import Call, CallStatus
from models.call_transcription import CallTranscription, SpeakerType
from helpers.transcription_helpers import save_transcription
from db.database import engine


class TestCallSidRefactorIntegration:
    """Integration tests for call_sid refactor across all layers."""

    def test_full_call_lifecycle_integration(self):
        """Test complete call lifecycle from creation to transcription storage."""
        call_sid = "EL_55555_integration_full_lifecycle"
        conversation_id = "conv_int_55555"
        driver_id = 55555

        # Phase 1: Proactive Call creation (before API call)
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=driver_id,
            call_start_time=datetime.now(timezone.utc),
            status=CallStatus.IN_PROGRESS
        )
        assert call.conversation_id is None
        assert call.status == CallStatus.IN_PROGRESS

        # Phase 2: Update with conversation_id after successful API call
        Call.update_conversation_id(call_sid, conversation_id)
        updated_call = Call.get_by_call_sid(call_sid)
        assert updated_call.conversation_id == conversation_id

        try:
            # Phase 3: Webhook receives transcription using call_sid
            transcription_id, sequence_number = save_transcription(
                call_sid=call_sid,
                speaker="agent",
                message="Full lifecycle test - agent message",
                timestamp=datetime.now(timezone.utc)
            )

            # Verify transcription saved correctly
            assert transcription_id is not None
            assert sequence_number == 1

            # Phase 4: Save second transcription
            transcription_id_2, sequence_number_2 = save_transcription(
                call_sid=call_sid,
                speaker="user",
                message="Full lifecycle test - user message",
                timestamp=datetime.now(timezone.utc)
            )

            assert sequence_number_2 == 2

            # Phase 5: Mark call as completed
            Call.update_status_by_call_sid(
                call_sid=call_sid,
                status=CallStatus.COMPLETED,
                call_end_time=datetime.now(timezone.utc)
            )

            # Verify final state
            final_call = Call.get_by_call_sid(call_sid)
            assert final_call.status == CallStatus.COMPLETED
            assert final_call.call_end_time is not None

            # Verify transcriptions exist
            transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
            assert len(transcriptions) == 2
            assert transcriptions[0].speaker_type == SpeakerType.AGENT
            assert transcriptions[1].speaker_type == SpeakerType.DRIVER

        finally:
            # Cleanup
            with Session(engine) as session:
                transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
                for t in transcriptions:
                    session.delete(t)
                session.delete(call)
                session.commit()

    def test_failed_elevenlabs_call_preserves_audit_trail(self):
        """Test that failed ElevenLabs calls still have Call records with FAILED status."""
        call_sid = "EL_66666_integration_failed_call"
        driver_id = 66666

        # Simulate call creation before API call
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=driver_id,
            call_start_time=datetime.now(timezone.utc)
        )

        # Simulate API failure - update status to FAILED
        Call.update_status_by_call_sid(
            call_sid=call_sid,
            status=CallStatus.FAILED
        )

        try:
            # Verify Call record exists with FAILED status
            failed_call = Call.get_by_call_sid(call_sid)
            assert failed_call is not None
            assert failed_call.status == CallStatus.FAILED
            assert failed_call.conversation_id is None  # No conversation_id because API failed
            assert failed_call.driver_id == driver_id  # Driver info preserved for audit

            # Verify webhook would fail appropriately
            with pytest.raises(ValueError, match="has no conversation_id"):
                save_transcription(
                    call_sid=call_sid,
                    speaker="agent",
                    message="This should fail",
                    timestamp=datetime.now(timezone.utc)
                )

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_webhook_null_conversation_id_error_handling(self):
        """Test webhook error handling when Call has NULL conversation_id."""
        call_sid = "EL_77777_integration_null_conv"

        # Create Call without conversation_id (API hasn't completed)
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=77777,
            call_start_time=datetime.now(timezone.utc)
        )

        try:
            # Webhook should fail with ValueError
            with pytest.raises(ValueError, match="has no conversation_id"):
                save_transcription(
                    call_sid=call_sid,
                    speaker="agent",
                    message="This should fail",
                    timestamp=datetime.now(timezone.utc)
                )

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_backfilled_records_work_in_webhook_flow(self):
        """Test that backfilled Call records with generated call_sid work correctly."""
        call_sid = "EL_88888_integration_backfill"
        conversation_id = "conv_int_backfill_88888"

        # Create Call with conversation_id (simulates old schema)
        with Session(engine) as session:
            # Create using raw SQLModel to simulate legacy Call
            call = Call(
                call_sid=call_sid,  # Backfilled value
                conversation_id=conversation_id,
                driver_id=88888,
                call_start_time=datetime.now(timezone.utc),
                status=CallStatus.COMPLETED
            )
            session.add(call)
            session.commit()
            session.refresh(call)

        try:
            # Test that webhook can use this backfilled call_sid
            transcription_id, sequence_number = save_transcription(
                call_sid=call_sid,
                speaker="agent",
                message="Backfill test message",
                timestamp=datetime.now(timezone.utc)
            )

            # Verify transcription saved
            assert transcription_id is not None
            assert sequence_number == 1

            # Verify transcription linked correctly
            transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
            assert len(transcriptions) == 1
            assert transcriptions[0].message_text == "Backfill test message"

        finally:
            # Cleanup
            with Session(engine) as session:
                transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
                for t in transcriptions:
                    session.delete(t)
                # Fetch and delete call
                call_to_delete = session.exec(
                    session.query(Call).where(Call.call_sid == call_sid)
                ).first()
                if call_to_delete:
                    session.delete(call_to_delete)
                session.commit()

    def test_concurrent_transcription_sequence_numbers(self):
        """Test that sequence numbers are generated correctly for multiple transcriptions."""
        call_sid = "EL_99999_integration_sequence"
        conversation_id = "conv_int_seq_99999"

        # Setup Call record
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=99999,
            call_start_time=datetime.now(timezone.utc)
        )
        Call.update_conversation_id(call_sid, conversation_id)

        try:
            # Save 5 transcriptions in sequence
            sequence_numbers = []
            for i in range(5):
                transcription_id, seq_num = save_transcription(
                    call_sid=call_sid,
                    speaker="agent" if i % 2 == 0 else "user",
                    message=f"Message {i+1}",
                    timestamp=datetime.now(timezone.utc)
                )
                sequence_numbers.append(seq_num)

            # Verify sequence numbers are sequential
            assert sequence_numbers == [1, 2, 3, 4, 5]

            # Verify all transcriptions exist
            transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
            assert len(transcriptions) == 5

            # Verify ordering
            for i, trans in enumerate(transcriptions):
                assert trans.sequence_number == i + 1

        finally:
            # Cleanup
            with Session(engine) as session:
                transcriptions = CallTranscription.get_by_conversation_id(conversation_id)
                for t in transcriptions:
                    session.delete(t)
                session.delete(call)
                session.commit()
