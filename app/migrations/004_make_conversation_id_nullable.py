"""
Migration 004: Make conversation_id nullable

This allows Call records to be created before ElevenLabs responds.
conversation_id will be NULL initially and populated after API call succeeds.

Author: Claude Code
Date: 2025-11-21
"""

from alembic import op
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """Make conversation_id nullable to support proactive Call creation."""
    try:
        op.alter_column(
            'calls',
            'conversation_id',
            nullable=True,
            schema='dev'
        )
        logger.info("Made conversation_id nullable")
        print("Migration 004: Made conversation_id nullable")
        print("Note: Call records can now be created before ElevenLabs API call completes")

    except Exception as e:
        logger.error(f"Failed to make conversation_id nullable: {e}")
        raise


def downgrade():
    """Make conversation_id non-nullable again.

    WARNING: This downgrade may fail if there are Call records with NULL conversation_id.
    Ensure all calls have completed and have conversation_id populated before running rollback.
    """
    try:
        op.alter_column(
            'calls',
            'conversation_id',
            nullable=False,
            schema='dev'
        )
        logger.info("Made conversation_id non-nullable")
        print("Migration 004 Rollback: Made conversation_id non-nullable")
        print("WARNING: This may fail if NULL values exist in conversation_id")

    except Exception as e:
        logger.error(f"Rollback failed (may be due to NULL values): {e}")
        print("ERROR: Rollback failed. Check if there are NULL values in conversation_id")
        raise


# For manual execution
if __name__ == "__main__":
    print("This migration should be run through alembic or database migration tool")
    print("Manual execution not recommended")
