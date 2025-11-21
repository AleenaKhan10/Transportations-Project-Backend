"""
Tests for Call model new methods.

Focused tests covering critical Call model behaviors:
- create_call_with_call_sid creates record with NULL conversation_id
- get_by_call_sid retrieves correct record
- update_conversation_id updates existing record
- update_status_by_call_sid updates status and call_end_time
- Timezone-aware datetime handling
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import Session
from models.call import Call, CallStatus
from db.database import engine


class TestCallModel:
    """Test new Call model methods for call_sid refactor."""

    def test_create_call_with_call_sid_has_null_conversation_id(self):
        """Test that create_call_with_call_sid creates record with NULL conversation_id."""
        call_sid = "EL_123_test_create"
        driver_id = 123
        call_start_time = datetime.now(timezone.utc)

        # Create call using new method
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=driver_id,
            call_start_time=call_start_time
        )

        try:
            # Verify fields
            assert call.call_sid == call_sid
            assert call.driver_id == driver_id
            assert call.conversation_id is None  # Should be NULL initially
            assert call.status == CallStatus.IN_PROGRESS
            assert call.call_start_time == call_start_time
            assert call.call_end_time is None

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_get_by_call_sid_retrieves_correct_record(self):
        """Test that get_by_call_sid retrieves the correct Call record."""
        call_sid = "EL_456_test_get"
        driver_id = 456

        # Create test call
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=driver_id,
            call_start_time=datetime.now(timezone.utc)
        )

        try:
            # Retrieve by call_sid
            retrieved = Call.get_by_call_sid(call_sid)

            # Verify correct record retrieved
            assert retrieved is not None
            assert retrieved.id == call.id
            assert retrieved.call_sid == call_sid
            assert retrieved.driver_id == driver_id

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_update_conversation_id_populates_field(self):
        """Test that update_conversation_id updates Call with conversation_id."""
        call_sid = "EL_789_test_update_conv"
        conversation_id = "conv_test_update_123"

        # Create call without conversation_id
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=789,
            call_start_time=datetime.now(timezone.utc)
        )

        try:
            assert call.conversation_id is None

            # Update with conversation_id
            updated = Call.update_conversation_id(call_sid, conversation_id)

            # Verify update
            assert updated is not None
            assert updated.conversation_id == conversation_id
            assert updated.call_sid == call_sid
            assert updated.updated_at > call.created_at

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_update_status_by_call_sid_changes_status(self):
        """Test that update_status_by_call_sid updates status and call_end_time."""
        call_sid = "EL_111_test_status"

        # Create call with IN_PROGRESS status
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=111,
            call_start_time=datetime.now(timezone.utc)
        )

        try:
            assert call.status == CallStatus.IN_PROGRESS
            assert call.call_end_time is None

            # Update status to COMPLETED
            call_end_time = datetime.now(timezone.utc)
            updated = Call.update_status_by_call_sid(
                call_sid=call_sid,
                status=CallStatus.COMPLETED,
                call_end_time=call_end_time
            )

            # Verify update
            assert updated is not None
            assert updated.status == CallStatus.COMPLETED
            assert updated.call_end_time == call_end_time

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_timezone_aware_datetimes(self):
        """Test that all datetime fields are timezone-aware."""
        call_sid = "EL_222_test_tz"
        call_start_time = datetime.now(timezone.utc)

        # Create call
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=222,
            call_start_time=call_start_time
        )

        try:
            # Verify timezone-aware datetimes
            assert call.call_start_time.tzinfo is not None
            assert call.created_at.tzinfo is not None
            assert call.updated_at.tzinfo is not None

            # Update with call_end_time
            call_end_time = datetime.now(timezone.utc)
            updated = Call.update_status_by_call_sid(
                call_sid=call_sid,
                status=CallStatus.COMPLETED,
                call_end_time=call_end_time
            )

            # Verify call_end_time is timezone-aware
            assert updated.call_end_time.tzinfo is not None

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_update_status_to_failed_on_api_error(self):
        """Test that status can be updated to FAILED when ElevenLabs API fails."""
        call_sid = "EL_333_test_failed"

        # Create call
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=333,
            call_start_time=datetime.now(timezone.utc)
        )

        try:
            # Simulate API failure - update status to FAILED
            updated = Call.update_status_by_call_sid(
                call_sid=call_sid,
                status=CallStatus.FAILED
            )

            # Verify status updated to FAILED
            assert updated is not None
            assert updated.status == CallStatus.FAILED
            assert updated.conversation_id is None  # No conversation_id since API failed

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()
