"""
APScheduler Configuration

This module sets up the background scheduler for processing scheduled calls.
It initializes APScheduler and registers the job to check for due calls.
"""

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler = None


async def process_scheduled_calls_job():
    """
    Job function that processes scheduled calls.
    This is called by the scheduler every minute.
    """
    try:
        from utils.scheduled_calls_processor import scheduled_calls_processor
        await scheduled_calls_processor.process_due_calls()
    except Exception as e:
        logger.error(f"[SCHEDULER] Error in scheduled calls job: {str(e)}", exc_info=True)


def init_scheduler():
    """
    Initialize and start the APScheduler.
    Should be called on FastAPI startup.
    """
    global scheduler

    if scheduler is not None:
        logger.warning("[SCHEDULER] Scheduler already initialized")
        return scheduler

    logger.info("[SCHEDULER] Initializing APScheduler...")

    # Create async scheduler
    scheduler = AsyncIOScheduler(
        timezone="UTC",
        job_defaults={
            "coalesce": True,  # Combine multiple pending executions into one
            "max_instances": 1,  # Only one instance of each job running at a time
            "misfire_grace_time": 60  # Allow 60 seconds grace period for missed jobs
        }
    )

    # Add job to process scheduled calls every minute
    scheduler.add_job(
        process_scheduled_calls_job,
        trigger=IntervalTrigger(minutes=1),
        id="process_scheduled_calls",
        name="Process Scheduled Driver Calls",
        replace_existing=True
    )

    # Start the scheduler
    scheduler.start()
    logger.info("[SCHEDULER] APScheduler started - processing scheduled calls every minute")

    return scheduler


def shutdown_scheduler():
    """
    Shutdown the scheduler gracefully.
    Should be called on FastAPI shutdown.
    """
    global scheduler

    if scheduler is not None:
        logger.info("[SCHEDULER] Shutting down APScheduler...")
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("[SCHEDULER] APScheduler shutdown complete")


def get_scheduler() -> AsyncIOScheduler:
    """Get the current scheduler instance."""
    return scheduler
