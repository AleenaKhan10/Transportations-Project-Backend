"""
Scheduled Calls Processor

This module handles the automatic processing of scheduled driver calls.
It uses APScheduler to periodically check for due scheduled calls and
triggers them via the ElevenLabs API.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
import httpx
from sqlmodel import Session, select

from db import engine
from models.driver_sheduled_calls import DriverSheduledCalls
from models.drivers import Driver
from models.trips import Trip
from config import settings

logger = logging.getLogger(__name__)


class ScheduledCallsProcessor:
    """Processes scheduled driver calls when they are due."""

    def __init__(self):
        self.api_base_url = settings.CLOUD_RUN_URL or "http://localhost:8000"

    def get_due_calls(self) -> List[DriverSheduledCalls]:
        """
        Get all scheduled calls that are ready for processing.
        Returns records where status is True (active).
        """
        with Session(engine) as session:
            statement = select(DriverSheduledCalls).where(
                DriverSheduledCalls.status == True
            )
            results = session.exec(statement).all()
            logger.info(f"[SCHEDULER] Found {len(results)} active scheduled calls")
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
        Includes trip_id and custom_rules in the payload.
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
            f"custom_rules: {custom_rules[:50] if custom_rules else 'None'}..."
        )

        return payload

    async def trigger_call(self, payload: dict) -> bool:
        """
        Trigger the call-elevenlabs API endpoint.
        Returns True if successful, False otherwise.
        """
        url = f"{self.api_base_url}/driver_data/call-elevenlabs"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)

                if response.status_code == 200:
                    logger.info(
                        f"[SCHEDULER] Successfully triggered call for driver {payload['drivers'][0]['driverId']}"
                    )
                    return True
                else:
                    logger.error(
                        f"[SCHEDULER] Failed to trigger call. Status: {response.status_code}, Response: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"[SCHEDULER] Error triggering call: {str(e)}", exc_info=True)
            return False

    def delete_scheduled_call(self, record_id) -> bool:
        """Delete a scheduled call record after successful processing."""
        return DriverSheduledCalls.delete_record_by_id(record_id)

    async def process_due_calls(self):
        """
        Main processing function called by the scheduler.
        Processes all due scheduled calls.
        """
        logger.info("[SCHEDULER] Starting scheduled calls processing...")

        try:
            due_calls = self.get_due_calls()

            if not due_calls:
                logger.info("[SCHEDULER] No due calls to process")
                return

            for scheduled_call in due_calls:
                try:
                    logger.info(
                        f"[SCHEDULER] Processing scheduled call {scheduled_call.id} for driver {scheduled_call.driver}"
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

                    # Check if there are any violation details
                    if not payload["drivers"][0]["violations"]["violationDetails"]:
                        logger.warning(
                            f"[SCHEDULER] No violations or reminders for scheduled call {scheduled_call.id}. Skipping."
                        )
                        self.delete_scheduled_call(scheduled_call.id)
                        continue

                    # Trigger the call
                    success = await self.trigger_call(payload)

                    if success:
                        # Delete the record after successful call
                        deleted = self.delete_scheduled_call(scheduled_call.id)
                        if deleted:
                            logger.info(
                                f"[SCHEDULER] Successfully processed and deleted scheduled call {scheduled_call.id}"
                            )
                        else:
                            logger.warning(
                                f"[SCHEDULER] Call triggered but failed to delete record {scheduled_call.id}"
                            )
                    else:
                        logger.error(
                            f"[SCHEDULER] Failed to trigger call for scheduled call {scheduled_call.id}"
                        )
                        # Don't delete - will retry on next run

                except Exception as e:
                    logger.error(
                        f"[SCHEDULER] Error processing scheduled call {scheduled_call.id}: {str(e)}",
                        exc_info=True,
                    )
                    continue

        except Exception as e:
            logger.error(
                f"[SCHEDULER] Error in process_due_calls: {str(e)}", exc_info=True
            )

        logger.info("[SCHEDULER] Completed scheduled calls processing")


# Singleton instance
scheduled_calls_processor = ScheduledCallsProcessor()
