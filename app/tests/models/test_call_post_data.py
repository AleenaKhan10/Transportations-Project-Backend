"""
Tests for Call model post-call data update functionality.

Focused tests covering critical behaviors for update_post_call_data method:
- Update with all fields populated (happy path)
- Update with conversation_id not found (returns None)
- Update with partial data (nullable fields)
- Status changes to COMPLETED after update
"""

import pytest
import json
from datetime import datetime, timezone
from sqlmodel import Session
from models.call import Call, CallStatus
from db.database import engine


class TestCallPostData:
    """Test Call model update_post_call_data method."""

    def test_update_post_call_data_with_all_fields(self):
        """Test that update_post_call_data updates all metadata fields and sets status to COMPLETED."""
        call_sid = "EL_test_post_all"
        conversation_id = "conv_test_post_all_123"

        # Create call with conversation_id
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=None,
            call_start_time=datetime.now(timezone.utc)
        )
        Call.update_conversation_id(call_sid, conversation_id)

        try:
            # Prepare post-call data
            call_end_time = datetime.now(timezone.utc)
            transcript_summary = "Agent greeted driver and confirmed delivery location."
            call_duration_seconds = 145
            cost = 0.08
            call_successful = True
            analysis_data = json.dumps({
                "call_successful": True,
                "transcript_summary": transcript_summary,
                "evaluation_results": {"criteria_1": "passed"}
            })
            metadata_json = json.dumps({
                "call_duration_secs": 145,
                "cost": 0.08,
                "from_number": "+14155551234",
                "to_number": "+14155555678"
            })

            # Update with all fields
            updated = Call.update_post_call_data(
                conversation_id=conversation_id,
                call_end_time=call_end_time,
                transcript_summary=transcript_summary,
                call_duration_seconds=call_duration_seconds,
                cost=cost,
                call_successful=call_successful,
                analysis_data=analysis_data,
                metadata_json=metadata_json
            )

            # Verify all fields updated
            assert updated is not None
            assert updated.status == CallStatus.COMPLETED
            assert updated.call_end_time == call_end_time
            assert updated.transcript_summary == transcript_summary
            assert updated.call_duration_seconds == call_duration_seconds
            assert updated.cost == cost
            assert updated.call_successful == call_successful
            assert updated.analysis_data == analysis_data
            assert updated.metadata_json == metadata_json
            assert updated.updated_at > call.created_at

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_update_post_call_data_conversation_id_not_found(self):
        """Test that update_post_call_data returns None when conversation_id not found."""
        conversation_id = "conv_nonexistent_123"
        call_end_time = datetime.now(timezone.utc)

        # Attempt to update non-existent call
        updated = Call.update_post_call_data(
            conversation_id=conversation_id,
            call_end_time=call_end_time,
            transcript_summary="Test summary"
        )

        # Verify None returned
        assert updated is None

    def test_update_post_call_data_with_partial_fields(self):
        """Test that update_post_call_data works with only some fields provided (nullable)."""
        call_sid = "EL_test_post_partial"
        conversation_id = "conv_test_post_partial_456"

        # Create call
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=None,
            call_start_time=datetime.now(timezone.utc)
        )
        Call.update_conversation_id(call_sid, conversation_id)

        try:
            # Update with only some fields (others remain NULL)
            call_end_time = datetime.now(timezone.utc)
            updated = Call.update_post_call_data(
                conversation_id=conversation_id,
                call_end_time=call_end_time,
                transcript_summary="Brief summary",
                call_successful=False
                # Note: cost, call_duration_seconds, analysis_data, metadata_json not provided
            )

            # Verify partial update successful
            assert updated is not None
            assert updated.status == CallStatus.COMPLETED
            assert updated.call_end_time == call_end_time
            assert updated.transcript_summary == "Brief summary"
            assert updated.call_successful is False
            # Verify optional fields remain None
            assert updated.cost is None
            assert updated.call_duration_seconds is None
            assert updated.analysis_data is None
            assert updated.metadata_json is None

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()

    def test_update_post_call_data_changes_status_to_completed(self):
        """Test that update_post_call_data changes status from IN_PROGRESS to COMPLETED."""
        call_sid = "EL_test_post_status"
        conversation_id = "conv_test_post_status_789"

        # Create call with IN_PROGRESS status
        call = Call.create_call_with_call_sid(
            call_sid=call_sid,
            driver_id=None,
            call_start_time=datetime.now(timezone.utc)
        )
        Call.update_conversation_id(call_sid, conversation_id)

        try:
            # Verify initial status
            assert call.status == CallStatus.IN_PROGRESS
            assert call.call_end_time is None

            # Update post-call data
            call_end_time = datetime.now(timezone.utc)
            updated = Call.update_post_call_data(
                conversation_id=conversation_id,
                call_end_time=call_end_time,
                call_duration_seconds=300,
                cost=0.12
            )

            # Verify status changed to COMPLETED
            assert updated is not None
            assert updated.status == CallStatus.COMPLETED
            assert updated.call_end_time == call_end_time
            assert updated.call_end_time.tzinfo is not None  # timezone-aware

        finally:
            # Cleanup
            with Session(engine) as session:
                session.delete(call)
                session.commit()
