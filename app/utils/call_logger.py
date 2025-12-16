"""
Call Logger Utility

This module provides a specialized logger for call-related events.
It logs to both console and optionally to a file based on configuration.
Helps track call flow, retry scheduling, and duplicate detection.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional
from config import settings

# Create a dedicated logger for calls
call_logger = logging.getLogger("call_events")


def setup_call_logger():
    """
    Setup the call logger with file and console handlers.
    Call this once during application startup.
    """
    global call_logger

    # Clear existing handlers
    call_logger.handlers = []
    call_logger.setLevel(logging.DEBUG)

    # Create formatter with detailed timestamp
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    call_logger.addHandler(console_handler)

    # Add file handler if enabled
    if settings.LOG_FILE_ENABLED:
        try:
            # Create logs directory if it doesn't exist
            log_dir = os.path.dirname(settings.LOG_FILE_PATH)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.FileHandler(
                settings.LOG_FILE_PATH,
                mode='a',  # Append mode
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            call_logger.addHandler(file_handler)

            call_logger.info(f"[CALL_LOGGER] File logging enabled: {settings.LOG_FILE_PATH}")
        except Exception as e:
            call_logger.error(f"[CALL_LOGGER] Failed to setup file logging: {e}")

    call_logger.info("[CALL_LOGGER] Call logger initialized")


def log_call_trigger(
    source: str,
    driver: str,
    call_sid: Optional[str] = None,
    conversation_id: Optional[str] = None,
    retry_count: int = 0,
    parent_call_sid: Optional[str] = None,
    trip_id: Optional[str] = None,
    reason: Optional[str] = None,
    extra_data: Optional[dict] = None
):
    """
    Log when a call is triggered.

    Args:
        source: Where the call was triggered from (e.g., "SCHEDULER", "API", "RETRY_PROCESSOR")
        driver: Driver identifier
        call_sid: Call SID if available
        conversation_id: ElevenLabs conversation ID if available
        retry_count: Current retry attempt number
        parent_call_sid: Original call's SID if this is a retry
        trip_id: Trip ID if available
        reason: Why the call was triggered
        extra_data: Any additional data to log
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    msg_parts = [
        f"[CALL_TRIGGER]",
        f"source={source}",
        f"driver={driver}",
    ]

    if call_sid:
        msg_parts.append(f"call_sid={call_sid}")
    if conversation_id:
        msg_parts.append(f"conversation_id={conversation_id}")
    if retry_count > 0:
        msg_parts.append(f"retry_count={retry_count}")
    if parent_call_sid:
        msg_parts.append(f"parent_call_sid={parent_call_sid}")
    if trip_id:
        msg_parts.append(f"trip_id={trip_id}")
    if reason:
        msg_parts.append(f"reason={reason}")
    if extra_data:
        msg_parts.append(f"extra={extra_data}")

    call_logger.info(" | ".join(msg_parts))


def log_retry_schedule(
    source: str,
    driver: str,
    original_call_sid: str,
    retry_count: int,
    scheduled_time: datetime,
    delay_minutes: int,
    reason: str,
    schedule_id: Optional[str] = None,
    duplicate_check_result: Optional[bool] = None
):
    """
    Log when a retry is scheduled.

    Args:
        source: Where the retry was scheduled from
        driver: Driver identifier
        original_call_sid: The original call's SID
        retry_count: Which retry attempt this will be
        scheduled_time: When the retry is scheduled
        delay_minutes: Delay in minutes
        reason: Why retry was scheduled
        schedule_id: The scheduled call record ID if created
        duplicate_check_result: Result of duplicate check (None if not checked)
    """
    msg_parts = [
        f"[RETRY_SCHEDULE]",
        f"source={source}",
        f"driver={driver}",
        f"original_call_sid={original_call_sid}",
        f"retry_count={retry_count}",
        f"scheduled_time={scheduled_time.isoformat()}",
        f"delay_minutes={delay_minutes}",
        f"reason={reason}",
    ]

    if schedule_id:
        msg_parts.append(f"schedule_id={schedule_id}")
    if duplicate_check_result is not None:
        msg_parts.append(f"duplicate_exists={duplicate_check_result}")

    call_logger.info(" | ".join(msg_parts))


def log_duplicate_detected(
    source: str,
    driver: str,
    original_call_sid: str,
    existing_schedule_info: Optional[str] = None
):
    """
    Log when a duplicate retry is detected and skipped.
    """
    msg_parts = [
        f"[DUPLICATE_DETECTED]",
        f"source={source}",
        f"driver={driver}",
        f"original_call_sid={original_call_sid}",
        f"action=SKIPPED",
    ]

    if existing_schedule_info:
        msg_parts.append(f"existing={existing_schedule_info}")

    call_logger.warning(" | ".join(msg_parts))


def log_call_status_change(
    call_sid: str,
    old_status: str,
    new_status: str,
    source: str,
    reason: Optional[str] = None
):
    """
    Log when a call status changes.
    """
    msg_parts = [
        f"[STATUS_CHANGE]",
        f"call_sid={call_sid}",
        f"old_status={old_status}",
        f"new_status={new_status}",
        f"source={source}",
    ]

    if reason:
        msg_parts.append(f"reason={reason}")

    call_logger.info(" | ".join(msg_parts))


def log_scheduled_call_processing(
    schedule_id: str,
    driver: str,
    status: bool,
    retry_count: int,
    parent_call_sid: Optional[str],
    action: str,
    result: Optional[str] = None
):
    """
    Log when a scheduled call is being processed.

    Args:
        schedule_id: The scheduled call record ID
        driver: Driver identifier
        status: Current status (True=active, False=pending)
        retry_count: Retry count
        parent_call_sid: Parent call SID if this is a retry
        action: What action is being taken
        result: Result of the action
    """
    is_retry = retry_count > 0

    msg_parts = [
        f"[SCHEDULED_CALL]",
        f"id={schedule_id}",
        f"driver={driver}",
        f"status={'ACTIVE' if status else 'PENDING'}",
        f"is_retry={is_retry}",
        f"retry_count={retry_count}",
        f"action={action}",
    ]

    if parent_call_sid:
        msg_parts.append(f"parent_call_sid={parent_call_sid}")
    if result:
        msg_parts.append(f"result={result}")

    call_logger.info(" | ".join(msg_parts))


# Initialize logger on module import
setup_call_logger()
