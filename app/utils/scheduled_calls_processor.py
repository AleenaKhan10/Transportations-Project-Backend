"""
Scheduled Calls Processor

This module handles the automatic processing of scheduled driver calls.
It uses APScheduler to periodically check for due scheduled calls and
triggers them via the ElevenLabs API.
"""

import logging
import uuid as uuid_module
from datetime import datetime, timezone
from typing import List, Optional, Set
import httpx
from sqlmodel import Session, select

from db import engine
from models.driver_sheduled_calls import DriverSheduledCalls
from models.drivers import Driver
from models.trips import Trip
from config import settings
from utils.call_logger import (
    log_call_trigger,
    log_scheduled_call_processing,
)

logger = logging.getLogger(__name__)

# Track processed call IDs within a single run to prevent duplicates
_processing_lock: Set[str] = set()


class ScheduledCallsProcessor:
    """Processes scheduled driver calls when they are due."""

    def __init__(self):
        self.api_base_url = settings.CLOUD_RUN_URL or "http://localhost:8000"

    def get_due_calls(self) -> List[DriverSheduledCalls]:
        """
        Get all scheduled calls that are ready for processing.
        Returns records where status is True (active).

        Uses SELECT FOR UPDATE with SKIP LOCKED to prevent duplicate processing
        across multiple scheduler instances/workers.
        """
        with Session(engine) as session:
            # Use raw SQL with FOR UPDATE SKIP LOCKED for proper locking
            # This ensures that if another process is processing a record,
            # this query will skip it instead of waiting or reading it
            from sqlalchemy import text

            # First, find and lock the records, then immediately mark them as processing
            # This atomic operation prevents race conditions
            statement = select(DriverSheduledCalls).where(
                DriverSheduledCalls.status == True
            ).with_for_update(skip_locked=True)

            results = session.exec(statement).all()
            logger.info(f"[SCHEDULER] Found {len(results)} active scheduled calls (with lock)")

            # Immediately mark all found records as processing within the same transaction
            for record in results:
                record.status = False
                session.add(record)

            session.commit()

            # Refresh all records to get updated state
            for record in results:
                session.refresh(record)

            return list(results)

    def get_driver_info(self, driver_name: str) -> Optional[Driver]:
        """
        Get driver information from the driversdirectory table.
        Searches by firstName + lastName combination.
        """
        # Split the name into parts
        name_parts = driver_name.strip().split(" ", 1)
        first_name = name_parts[0] if len(name_parts) > 0 else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        with Session(engine) as session:
            # Search by firstName and lastName
            statement = select(Driver).where(
                Driver.firstName == first_name, Driver.lastName == last_name
            )
            result = session.exec(statement).first()

            if result:
                return result

            # Fallback: try searching by driverId in case it's actually an ID
            return Driver.get_by_id(driver_name)

    def get_active_trip_for_driver(self, driver_id: str) -> Optional[Trip]:
        """
        Get the active trip for a driver by checking substatus.

        Active substatus values:
        - 'en route to pickup', 'en route to pick up', 'loading',
        - 'en route to delivery', 'en route to waypoint', 'unloading'

        Returns the active trip or None if no active trip found.
        """
        try:
            active_trip = Trip.get_active_trip_by_driver_id(driver_id)
            if active_trip:
                logger.info(
                    f"[SCHEDULER] Found active trip {active_trip.tripId} for driver {driver_id} "
                    f"with substatus: {active_trip.subStatusLabel}"
                )
            else:
                logger.info(f"[SCHEDULER] No active trip found for driver {driver_id}")
            return active_trip
        except Exception as e:
            logger.error(
                f"[SCHEDULER] Error getting active trip for driver {driver_id}: {str(e)}",
                exc_info=True,
            )
            return None

    def build_payload(
        self, scheduled_call: DriverSheduledCalls, driver: Driver, trip_id: Optional[str] = None
    ) -> dict:
        """
        Build the API payload for the call-elevenlabs endpoint.

        Maps violations and reminders to violationDetails with appropriate types.
        Includes trip_id, custom_rules, retry tracking, and parent_call_sid in the payload.
        """
        violation_details = []

        # Process violations (comma-separated string)
        if scheduled_call.violation:
            violations = [
                v.strip() for v in scheduled_call.violation.split(",") if v.strip()
            ]
            for v in violations:
                violation_details.append({"type": "VIOLATION", "description": v})

        # Process reminders (comma-separated string)
        if scheduled_call.reminder:
            reminders = [
                r.strip() for r in scheduled_call.reminder.split(",") if r.strip()
            ]
            for r in reminders:
                violation_details.append({"type": "REMINDER", "description": r})

        # Build driver name
        driver_name = f"{driver.firstName or ''} {driver.lastName or ''}".strip()
        if not driver_name:
            driver_name = driver.driverId

        # Get custom rules from scheduled call
        custom_rules = scheduled_call.custom_rule or ""

        payload = {
            "callType": "violation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trip_id": trip_id or "",  # Pass trip_id at root level
            "retry_count": scheduled_call.retry_count,  # Pass retry count for tracking
            "parent_call_sid": scheduled_call.parent_call_sid,  # Link to original call
            "drivers": [
                {
                    "driverId": driver.driverId,
                    "driverName": driver_name,
                    "phoneNumber": driver.phoneNumber or "",
                    "customRules": custom_rules,  # Pass custom rules
                    "violations": {"tripId": trip_id or "", "violationDetails": violation_details},
                }
            ],
        }

        logger.info(
            f"[SCHEDULER] Built payload for driver {driver.driverId} with trip_id: {trip_id}, "
            f"custom_rules: {custom_rules[:50] if custom_rules else 'None'}..., "
            f"retry_count: {scheduled_call.retry_count}, parent_call_sid: {scheduled_call.parent_call_sid}"
        )

        return payload

    async def trigger_call(self, payload: dict, run_id: str = "") -> bool:
        """
        Trigger the call-elevenlabs API endpoint.
        Returns True if successful, False otherwise.
        """
        url = f"{self.api_base_url}/driver_data/call-elevenlabs"
        driver_id = payload['drivers'][0]['driverId']

        logger.info(f"[SCHEDULER] About to trigger call for driver {driver_id} to {url} (run_id={run_id})")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"[SCHEDULER] Sending POST request for driver {driver_id} (run_id={run_id})")
                response = await client.post(url, json=payload)

                if response.status_code == 200:
                    logger.info(
                        f"[SCHEDULER] Successfully triggered call for driver {driver_id} (run_id={run_id})"
                    )
                    return True
                else:
                    logger.error(
                        f"[SCHEDULER] Failed to trigger call. Status: {response.status_code}, Response: {response.text} (run_id={run_id})"
                    )
                    return False

        except Exception as e:
            logger.error(f"[SCHEDULER] Error triggering call: {str(e)} (run_id={run_id})", exc_info=True)
            return False

    def mark_as_processing(self, record_id) -> bool:
        """
        Mark a scheduled call as being processed by setting status to False.
        This prevents duplicate processing if the scheduler runs again before
        the call is fully processed and deleted.
        """
        try:
            with Session(engine) as session:
                record = session.get(DriverSheduledCalls, record_id)
                if record:
                    record.status = False
                    session.add(record)
                    session.commit()
                    logger.info(f"[SCHEDULER] Marked scheduled call {record_id} as processing (status=False)")
                    return True
                return False
        except Exception as e:
            logger.error(f"[SCHEDULER] Error marking call {record_id} as processing: {str(e)}")
            return False

    def delete_scheduled_call(self, record_id) -> bool:
        """Delete a scheduled call record after successful processing."""
        return DriverSheduledCalls.delete_record_by_id(record_id)

    async def process_due_calls(self):
        """
        Main processing function called by the scheduler.
        Processes all due scheduled calls.
        """
        global _processing_lock

        # Generate unique run ID for this scheduler execution
        run_id = str(uuid_module.uuid4())[:8]

        logger.info(f"[SCHEDULER] Starting scheduled calls processing... (run_id={run_id})")

        try:
            due_calls = self.get_due_calls()

            if not due_calls:
                logger.info(f"[SCHEDULER] No due calls to process (run_id={run_id})")
                return

            logger.info(f"[SCHEDULER] Processing {len(due_calls)} calls (run_id={run_id})")

            for scheduled_call in due_calls:
                try:
                    # Check if this call is already being processed in memory (safety check)
                    call_id_str = str(scheduled_call.id)
                    if call_id_str in _processing_lock:
                        logger.warning(
                            f"[SCHEDULER] Call {scheduled_call.id} is already being processed in memory, skipping (run_id={run_id})"
                        )
                        continue

                    # Add to in-memory lock as additional safety
                    _processing_lock.add(call_id_str)
                    logger.info(f"[SCHEDULER] Processing call {scheduled_call.id} (run_id={run_id})")

                    is_retry = scheduled_call.retry_count > 0

                    # Note: status was already set to False in get_due_calls() atomically
                    # No need to call mark_as_processing again

                    # Log to call logger for file tracking
                    log_scheduled_call_processing(
                        schedule_id=str(scheduled_call.id),
                        driver=scheduled_call.driver,
                        status=scheduled_call.status,
                        retry_count=scheduled_call.retry_count,
                        parent_call_sid=scheduled_call.parent_call_sid,
                        action="PROCESSING_START",
                    )

                    logger.info(
                        f"[SCHEDULER] Processing scheduled call {scheduled_call.id} for driver {scheduled_call.driver}"
                        f"{' (RETRY #{}'.format(scheduled_call.retry_count) + ', parent=' + str(scheduled_call.parent_call_sid) + ')' if is_retry else ''}"
                    )

                    # Get driver information
                    driver = self.get_driver_info(scheduled_call.driver)

                    if not driver:
                        logger.warning(
                            f"[SCHEDULER] Driver not found: {scheduled_call.driver}. Skipping call."
                        )
                        # Still delete the record to avoid repeated attempts
                        self.delete_scheduled_call(scheduled_call.id)
                        continue

                    if not driver.phoneNumber:
                        logger.warning(
                            f"[SCHEDULER] Driver {scheduled_call.driver} has no phone number. Skipping call."
                        )
                        self.delete_scheduled_call(scheduled_call.id)
                        continue

                    # Get active trip for the driver (filter by substatus)
                    active_trip = self.get_active_trip_for_driver(driver.driverId)
                    trip_id = active_trip.tripId if active_trip else None

                    if trip_id:
                        logger.info(
                            f"[SCHEDULER] Using active trip {trip_id} for driver {driver.driverId}"
                        )
                    else:
                        logger.info(
                            f"[SCHEDULER] No active trip found for driver {driver.driverId}, proceeding without trip_id"
                        )

                    # Build payload with trip_id and custom_rules
                    payload = self.build_payload(scheduled_call, driver, trip_id)

                    # Check if there's anything to say - either violations/reminders OR custom_rule
                    has_violation_details = bool(payload["drivers"][0]["violations"]["violationDetails"])
                    has_custom_rules = bool(payload["drivers"][0].get("customRules", "").strip())

                    if not has_violation_details and not has_custom_rules:
                        logger.warning(
                            f"[SCHEDULER] No violations, reminders, or custom rules for scheduled call {scheduled_call.id}. Skipping."
                        )
                        self.delete_scheduled_call(scheduled_call.id)
                        continue

                    logger.info(
                        f"[SCHEDULER] Payload has violationDetails: {has_violation_details}, customRules: {has_custom_rules}"
                    )

                    # Log call trigger
                    log_call_trigger(
                        source="SCHEDULER",
                        driver=driver.driverId,
                        retry_count=scheduled_call.retry_count,
                        parent_call_sid=scheduled_call.parent_call_sid,
                        trip_id=trip_id,
                        reason="SCHEDULED_CALL_DUE",
                        extra_data={
                            "schedule_id": str(scheduled_call.id),
                            "phone": driver.phoneNumber,
                        }
                    )

                    # Trigger the call
                    success = await self.trigger_call(payload, run_id=run_id)

                    if success:
                        # Delete the record after successful call
                        deleted = self.delete_scheduled_call(scheduled_call.id)

                        log_scheduled_call_processing(
                            schedule_id=str(scheduled_call.id),
                            driver=scheduled_call.driver,
                            status=scheduled_call.status,
                            retry_count=scheduled_call.retry_count,
                            parent_call_sid=scheduled_call.parent_call_sid,
                            action="CALL_TRIGGERED",
                            result="SUCCESS" if deleted else "SUCCESS_BUT_DELETE_FAILED",
                        )

                        if deleted:
                            logger.info(
                                f"[SCHEDULER] Successfully processed and deleted scheduled call {scheduled_call.id}"
                            )
                        else:
                            logger.warning(
                                f"[SCHEDULER] Call triggered but failed to delete record {scheduled_call.id}"
                            )
                    else:
                        log_scheduled_call_processing(
                            schedule_id=str(scheduled_call.id),
                            driver=scheduled_call.driver,
                            status=scheduled_call.status,
                            retry_count=scheduled_call.retry_count,
                            parent_call_sid=scheduled_call.parent_call_sid,
                            action="CALL_TRIGGER_FAILED",
                            result="WILL_RETRY_NEXT_RUN",
                        )
                        logger.error(
                            f"[SCHEDULER] Failed to trigger call for scheduled call {scheduled_call.id}"
                        )
                        # Don't delete - will retry on next run

                except Exception as e:
                    logger.error(
                        f"[SCHEDULER] Error processing scheduled call {scheduled_call.id}: {str(e)} (run_id={run_id})",
                        exc_info=True,
                    )
                    # Remove from lock on error so it can be retried
                    _processing_lock.discard(call_id_str)
                    continue

        except Exception as e:
            logger.error(
                f"[SCHEDULER] Error in process_due_calls: {str(e)} (run_id={run_id})", exc_info=True
            )
        finally:
            # Clean up the processing lock for completed calls
            # Keep only entries that might still be processing
            logger.info(f"[SCHEDULER] Cleaning up processing lock, current size: {len(_processing_lock)} (run_id={run_id})")

        logger.info(f"[SCHEDULER] Completed scheduled calls processing (run_id={run_id})")


# Singleton instance
scheduled_calls_processor = ScheduledCallsProcessor()
