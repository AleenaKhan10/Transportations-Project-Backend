"""
Migration 001: Add call_sid column to calls table (nullable)

This is the first step in the call_sid refactor migration.
The column is nullable initially to allow backfilling existing records.

Author: Claude Code
Date: 2025-11-21
"""

from sqlalchemy import Column, String, text
from alembic import op
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """Add call_sid column as nullable VARCHAR(255)."""
    try:
        # Add call_sid column to calls table in dev schema
        op.add_column(
            'calls',
            Column('call_sid', String(255), nullable=True),
            schema='dev'
        )
        logger.info("Added call_sid column (nullable) to dev.calls table")
        print("Migration 001: Added call_sid column (nullable) to dev.calls table")
    except Exception as e:
        logger.error(f"Failed to add call_sid column: {e}")
        raise


def downgrade():
    """Remove call_sid column."""
    try:
        op.drop_column('calls', 'call_sid', schema='dev')
        logger.info("Removed call_sid column from dev.calls table")
        print("Migration 001 Rollback: Removed call_sid column from dev.calls table")
    except Exception as e:
        logger.error(f"Failed to remove call_sid column: {e}")
        raise


# For manual execution
if __name__ == "__main__":
    print("This migration should be run through alembic or database migration tool")
    print("Manual execution not recommended")
