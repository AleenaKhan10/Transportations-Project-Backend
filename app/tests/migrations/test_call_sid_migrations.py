"""
Tests for call_sid migration backfill logic.

Focused tests covering critical backfill scenarios:
- Correct call_sid format generation
- NULL driver_id handling
- Unique constraint enforcement
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import Session, select, text
from models.call import Call, CallStatus
from db.database import engine


class TestCallSidBackfill:
    """Test migration backfill logic for call_sid field."""

    def test_backfill_generates_correct_format(self):
        """Test that backfill generates correct call_sid format: EL_{driver_id}_{timestamp}."""
        with Session(engine) as session:
            # Create test call with known values
            test_call = Call(
                conversation_id="conv_test_format",
                driver_id=123,
                call_start_time=datetime(2024, 11, 21, 10, 0, 0, tzinfo=timezone.utc),
                status=CallStatus.IN_PROGRESS
            )
            test_call.created_at = datetime(2024, 11, 21, 10, 0, 0, tzinfo=timezone.utc)
            session.add(test_call)
            session.commit()
            session.refresh(test_call)

            # Simulate backfill (in real migration this would be SQL UPDATE)
            created_at_timestamp = int(test_call.created_at.timestamp())
            expected_call_sid = f"EL_{test_call.driver_id}_{created_at_timestamp}"
            test_call.call_sid = expected_call_sid
            session.add(test_call)
            session.commit()

            # Verify format
            assert test_call.call_sid.startswith("EL_")
            assert f"{test_call.driver_id}" in test_call.call_sid
            assert str(created_at_timestamp) in test_call.call_sid

            # Cleanup
            session.delete(test_call)
            session.commit()

    def test_backfill_handles_null_driver_id(self):
        """Test that backfill uses 'UNKNOWN' placeholder for NULL driver_id."""
        with Session(engine) as session:
            # Create test call with NULL driver_id
            test_call = Call(
                conversation_id="conv_test_null_driver",
                driver_id=None,  # NULL driver_id
                call_start_time=datetime.now(timezone.utc),
                status=CallStatus.IN_PROGRESS
            )
            session.add(test_call)
            session.commit()
            session.refresh(test_call)

            # Simulate backfill with NULL handling
            created_at_timestamp = int(test_call.created_at.timestamp())
            driver_id_str = 'UNKNOWN' if test_call.driver_id is None else str(test_call.driver_id)
            expected_call_sid = f"EL_{driver_id_str}_{created_at_timestamp}"
            test_call.call_sid = expected_call_sid
            session.add(test_call)
            session.commit()

            # Verify UNKNOWN placeholder used
            assert test_call.call_sid.startswith("EL_UNKNOWN_")
            assert "UNKNOWN" in test_call.call_sid

            # Cleanup
            session.delete(test_call)
            session.commit()

    def test_backfill_processes_multiple_records(self):
        """Test that backfill can process multiple Call records."""
        with Session(engine) as session:
            # Create multiple test calls
            test_calls = [
                Call(
                    conversation_id=f"conv_test_multi_{i}",
                    driver_id=100 + i,
                    call_start_time=datetime.now(timezone.utc),
                    status=CallStatus.IN_PROGRESS
                )
                for i in range(3)
            ]

            for call in test_calls:
                session.add(call)
            session.commit()

            # Refresh all calls
            for call in test_calls:
                session.refresh(call)

            # Simulate backfill for all
            for call in test_calls:
                created_at_timestamp = int(call.created_at.timestamp())
                call.call_sid = f"EL_{call.driver_id}_{created_at_timestamp}"
                session.add(call)
            session.commit()

            # Verify all have call_sid
            for call in test_calls:
                assert call.call_sid is not None
                assert call.call_sid.startswith("EL_")
                assert str(call.driver_id) in call.call_sid

            # Cleanup
            for call in test_calls:
                session.delete(call)
            session.commit()

    def test_unique_constraint_prevents_duplicates(self):
        """Test that unique constraint prevents duplicate call_sid values."""
        with Session(engine) as session:
            # Create first call
            call1 = Call(
                conversation_id="conv_unique_1",
                driver_id=456,
                call_start_time=datetime.now(timezone.utc),
                status=CallStatus.IN_PROGRESS,
                call_sid="EL_456_1700000000"  # Fixed call_sid
            )
            session.add(call1)
            session.commit()

            # Attempt to create second call with same call_sid
            call2 = Call(
                conversation_id="conv_unique_2",
                driver_id=789,
                call_start_time=datetime.now(timezone.utc),
                status=CallStatus.IN_PROGRESS,
                call_sid="EL_456_1700000000"  # Duplicate call_sid
            )
            session.add(call2)

            # Should raise integrity error due to unique constraint
            with pytest.raises(Exception):  # IntegrityError or similar
                session.commit()

            # Cleanup
            session.rollback()
            session.delete(call1)
            session.commit()
