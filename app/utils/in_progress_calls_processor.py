"""
In-Progress Calls Processor

This module handles the automatic finalization of calls that are stuck in IN_PROGRESS status.
It fetches conversation data from ElevenLabs API and updates the call records accordingly.
If a call has failed and retries are available, it schedules a retry via DriverSheduledCalls.
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from models.call import Call, CallStatus, RetryStatus
from models.driver_sheduled_calls import DriverSheduledCalls
from utils.elevenlabs_client import elevenlabs_client

logger = logging.getLogger(__name__)

# Retry delay configuration (in minutes)
RETRY_DELAYS = [10, 30, 60]  # 1st retry: 10 min, 2nd: 30 min, 3rd: 60 min


def get_retry_delay_minutes(retry_count: int) -> int:
    """
    Get the delay in minutes for a retry attempt.

    Args:
        retry_count: Current retry count (0 = first call, 1 = first retry, etc.)

    Returns:
        Delay in minutes before the retry should be triggered
    """
    if retry_count < len(RETRY_DELAYS):
        return RETRY_DELAYS[retry_count]
    return RETRY_DELAYS[-1]  # Use last value for any additional retries


class InProgressCallsProcessor:
    """Processes calls stuck in IN_PROGRESS status and handles retries."""

    async def process_in_progress_calls(self):
        """
        Main processing function called by the scheduler.
        Finds IN_PROGRESS calls older than 2 minutes and checks their status via ElevenLabs API.
        """
        logger.info("[IN_PROGRESS_PROCESSOR] Starting in-progress calls processing...")

        try:
            # Get calls that are IN_PROGRESS and older than 2 minutes
            in_progress_calls = Call.get_in_progress_calls_older_than(minutes=2)

            if not in_progress_calls:
                logger.info("[IN_PROGRESS_PROCESSOR] No in-progress calls to process")
                return

            logger.info(
                f"[IN_PROGRESS_PROCESSOR] Found {len(in_progress_calls)} in-progress calls to check"
            )

            for call in in_progress_calls:
                try:
                    await self.process_single_call(call)
                except Exception as e:
                    logger.error(
                        f"[IN_PROGRESS_PROCESSOR] Error processing call {call.call_sid}: {str(e)}",
                        exc_info=True,
                    )
                    continue

        except Exception as e:
            logger.error(
                f"[IN_PROGRESS_PROCESSOR] Error in process_in_progress_calls: {str(e)}",
                exc_info=True,
            )

        logger.info("[IN_PROGRESS_PROCESSOR] Completed in-progress calls processing")

    async def process_single_call(self, call: Call):
        """
        Process a single in-progress call.
        Fetches data from ElevenLabs and updates status accordingly.

        Args:
            call: The Call object to process
        """
        logger.info(
            f"[IN_PROGRESS_PROCESSOR] Processing call {call.call_sid}, "
            f"conversation_id: {call.conversation_id}"
        )

        # Skip if no conversation_id (API call may have failed before getting response)
        if not call.conversation_id:
            logger.warning(
                f"[IN_PROGRESS_PROCESSOR] Call {call.call_sid} has no conversation_id. "
                "Marking as failed (API call likely failed)."
            )
            await self.handle_failed_call(call, reason="No conversation_id")
            return

        # Fetch conversation data from ElevenLabs
        try:
            conversation_data = await elevenlabs_client.get_conversation(
                call.conversation_id
            )

            if not conversation_data:
                logger.warning(
                    f"[IN_PROGRESS_PROCESSOR] No data returned for conversation {call.conversation_id}"
                )
                # Don't mark as failed yet - might be temporary API issue
                return

            # Check conversation status
            conversation_status = conversation_data.get("status", "unknown")
            logger.info(
                f"[IN_PROGRESS_PROCESSOR] Conversation {call.conversation_id} status: {conversation_status}"
            )

            if conversation_status in ("done", "failed"):
                # Call has completed - update the record
                await self.finalize_completed_call(call, conversation_data)
            else:
                # Call still in progress according to ElevenLabs
                logger.info(
                    f"[IN_PROGRESS_PROCESSOR] Call {call.call_sid} still in progress "
                    f"(status: {conversation_status})"
                )

        except Exception as e:
            logger.error(
                f"[IN_PROGRESS_PROCESSOR] Error fetching conversation {call.conversation_id}: {str(e)}",
                exc_info=True,
            )
            # Don't mark as failed - might be temporary API issue

    async def finalize_completed_call(self, call: Call, conversation_data: dict):
        """
        Finalize a completed call - update record and handle retry if needed.

        Args:
            call: The Call object
            conversation_data: Data from ElevenLabs API
        """
        # Extract metadata
        metadata = conversation_data.get("metadata", {})
        analysis = conversation_data.get("analysis", {})

        call_duration = metadata.get("call_duration_secs", 0)
        cost_value = (
            metadata.get("cost", 0) / 100000.0 if metadata.get("cost") else None
        )

        # Parse call_successful
        call_successful_raw = analysis.get("call_successful")
        if isinstance(call_successful_raw, str):
            call_successful = call_successful_raw.lower() == "success"
        else:
            call_successful = bool(call_successful_raw) if call_successful_raw is not None else None

        transcript_summary = analysis.get("transcript_summary", "")

        # Calculate end time
        start_time_unix = metadata.get("start_time_unix_secs")
        if start_time_unix:
            call_end_time = datetime.fromtimestamp(
                start_time_unix + call_duration, tz=timezone.utc
            )
        else:
            call_end_time = datetime.now(timezone.utc)

        # Serialize metadata
        analysis_data = json.dumps(analysis) if analysis else None
        metadata_json = json.dumps(metadata) if metadata else None

        # Determine if call was successful
        # A call is considered failed if:
        # 1. conversation_status is "failed", OR
        # 2. call_successful is False (AI didn't accomplish goal)
        # 3. call_duration is very short (< 5 seconds - likely not answered)
        # 4. Voicemail was detected (termination_reason contains "voicemail")
        conversation_status = conversation_data.get("status", "unknown")
        call_not_answered = call_duration < 5

        # Check if voicemail was detected
        termination_reason = metadata.get("termination_reason", "")
        voicemail_detected = "voicemail" in termination_reason.lower()

        is_failed = (
            conversation_status == "failed"
            or call_not_answered
            or call_successful is False
            or voicemail_detected
        )

        if is_failed:
            failure_reasons = []
            if conversation_status == "failed":
                failure_reasons.append(f"conversation_status={conversation_status}")
            if call_not_answered:
                failure_reasons.append(f"call_duration={call_duration}s")
            if call_successful is False:
                failure_reasons.append("call_successful=False")
            if voicemail_detected:
                failure_reasons.append(f"voicemail_detected")
            logger.info(
                f"[IN_PROGRESS_PROCESSOR] Call {call.call_sid} failed. "
                f"Reasons: {', '.join(failure_reasons)}"
            )
            await self.handle_failed_call(
                call,
                reason=f"conversation_status={conversation_status}, call_successful={call_successful}",
                call_end_time=call_end_time,
                transcript_summary=transcript_summary,
                call_duration_seconds=call_duration,
                cost=cost_value,
                call_successful=call_successful,
                analysis_data=analysis_data,
                metadata_json=metadata_json,
            )
        else:
            # Call completed successfully
            logger.info(f"[IN_PROGRESS_PROCESSOR] Call {call.call_sid} completed successfully")
            Call.update_conversation_metadata(
                call_sid=call.call_sid,
                status=CallStatus.COMPLETED,
                call_end_time=call_end_time,
                transcript_summary=transcript_summary,
                call_duration_seconds=call_duration,
                cost=cost_value,
                call_successful=call_successful,
                analysis_data=analysis_data,
                metadata_json=metadata_json,
            )

    async def handle_failed_call(
        self,
        call: Call,
        reason: str,
        call_end_time: Optional[datetime] = None,
        transcript_summary: Optional[str] = None,
        call_duration_seconds: Optional[int] = None,
        cost: Optional[float] = None,
        call_successful: Optional[bool] = None,
        analysis_data: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ):
        """
        Handle a failed call - schedule retry if possible, otherwise mark as exhausted.

        Args:
            call: The Call object
            reason: Reason for failure
            Other args: Optional metadata from ElevenLabs
        """
        if call_end_time is None:
            call_end_time = datetime.now(timezone.utc)

        # Check if retries are available
        if call.retry_count < call.max_retries:
            # Schedule retry
            next_retry_count = call.retry_count + 1
            delay_minutes = get_retry_delay_minutes(call.retry_count)
            next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)

            logger.info(
                f"[IN_PROGRESS_PROCESSOR] Scheduling retry {next_retry_count}/{call.max_retries} "
                f"for call {call.call_sid} in {delay_minutes} minutes"
            )

            # Update call status to FAILED with RETRY_SCHEDULED
            Call.mark_call_failed_with_retry(
                call_sid=call.call_sid,
                call_end_time=call_end_time,
                next_retry_at=next_retry_at,
                transcript_summary=transcript_summary,
                call_duration_seconds=call_duration_seconds,
                cost=cost,
                call_successful=call_successful,
                analysis_data=analysis_data,
                metadata_json=metadata_json,
            )

            # Create scheduled call for retry using saved context
            self.schedule_retry_call(call, next_retry_at, next_retry_count)

        else:
            # No more retries - mark as exhausted
            logger.info(
                f"[IN_PROGRESS_PROCESSOR] Call {call.call_sid} exhausted all retries "
                f"({call.retry_count}/{call.max_retries})"
            )

            Call.mark_call_failed_exhausted(
                call_sid=call.call_sid,
                call_end_time=call_end_time,
                transcript_summary=transcript_summary,
                call_duration_seconds=call_duration_seconds,
                cost=cost,
                call_successful=call_successful,
                analysis_data=analysis_data,
                metadata_json=metadata_json,
            )

    def schedule_retry_call(
        self, call: Call, scheduled_time: datetime, retry_count: int
    ):
        """
        Create a scheduled call record for retry.

        Args:
            call: The original failed Call object
            scheduled_time: When to trigger the retry
            retry_count: The retry attempt number
        """
        # Use saved context from the original call
        # Driver name is used as the "driver" field in DriverSheduledCalls
        driver_identifier = call.driver_name or call.driver_id

        if not driver_identifier:
            logger.error(
                f"[IN_PROGRESS_PROCESSOR] Cannot schedule retry for call {call.call_sid}: "
                "no driver_name or driver_id"
            )
            return

        # Check if a retry schedule already exists for this call
        if DriverSheduledCalls.has_pending_retry_for_call(call.call_sid):
            logger.info(
                f"[IN_PROGRESS_PROCESSOR] Retry schedule already exists for call {call.call_sid}, "
                "skipping duplicate creation"
            )
            return

        # Parse violations and reminders from JSON
        violation_str = None
        reminder_str = None

        if call.violations_json:
            try:
                violations = json.loads(call.violations_json)
                # Convert list of violation dicts to comma-separated descriptions
                violation_str = ", ".join(
                    v.get("description", "") for v in violations if v.get("type") == "VIOLATION"
                )
                reminder_str = ", ".join(
                    v.get("description", "") for v in violations if v.get("type") == "REMINDER"
                )
            except json.JSONDecodeError:
                logger.warning(
                    f"[IN_PROGRESS_PROCESSOR] Failed to parse violations_json for call {call.call_sid}"
                )

        # Also check reminders_json separately if it exists
        if call.reminders_json:
            try:
                reminders = json.loads(call.reminders_json)
                if reminders:
                    reminder_list = [r.get("description", "") for r in reminders]
                    if reminder_str:
                        reminder_str += ", " + ", ".join(reminder_list)
                    else:
                        reminder_str = ", ".join(reminder_list)
            except json.JSONDecodeError:
                logger.warning(
                    f"[IN_PROGRESS_PROCESSOR] Failed to parse reminders_json for call {call.call_sid}"
                )

        # Create the scheduled call record
        scheduled_record = DriverSheduledCalls.create_retry_schedule(
            driver=driver_identifier,
            violation=violation_str if violation_str else None,
            reminder=reminder_str if reminder_str else None,
            custom_rule=call.custom_rules,
            call_scheduled_date_time=scheduled_time,
            retry_count=retry_count,
            parent_call_sid=call.call_sid,  # Link retry to original call
        )

        logger.info(
            f"[IN_PROGRESS_PROCESSOR] Created retry schedule {scheduled_record.id} for driver {driver_identifier}, "
            f"scheduled at {scheduled_time}, parent_call_sid={call.call_sid}"
        )


# Singleton instance
in_progress_calls_processor = InProgressCallsProcessor()
