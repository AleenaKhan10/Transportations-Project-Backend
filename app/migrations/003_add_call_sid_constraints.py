"""
Migration 003: Add constraints and indexes for call_sid

Adds:
- NOT NULL constraint on call_sid
- Unique constraint on call_sid (uq_calls_call_sid)
- Single column index on call_sid (idx_calls_call_sid)
- Compound index on (call_sid, status) (idx_calls_call_sid_status)

Author: Claude Code
Date: 2025-11-21
"""

from alembic import op
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """Add NOT NULL constraint, unique constraint, and indexes to call_sid."""
    try:
        # Step 1: Make call_sid non-nullable
        op.alter_column(
            'calls',
            'call_sid',
            nullable=False,
            schema='dev'
        )
        logger.info("Made call_sid non-nullable")
        print("Migration 003: Made call_sid non-nullable")

        # Step 2: Add unique constraint
        op.create_unique_constraint(
            'uq_calls_call_sid',
            'calls',
            ['call_sid'],
            schema='dev'
        )
        logger.info("Added unique constraint uq_calls_call_sid")
        print("Migration 003: Added unique constraint uq_calls_call_sid")

        # Step 3: Add single column index
        op.create_index(
            'idx_calls_call_sid',
            'calls',
            ['call_sid'],
            schema='dev'
        )
        logger.info("Added index idx_calls_call_sid")
        print("Migration 003: Added index idx_calls_call_sid")

        # Step 4: Add compound index on (call_sid, status)
        op.create_index(
            'idx_calls_call_sid_status',
            'calls',
            ['call_sid', 'status'],
            schema='dev'
        )
        logger.info("Added compound index idx_calls_call_sid_status")
        print("Migration 003: Added compound index idx_calls_call_sid_status")

    except Exception as e:
        logger.error(f"Failed to add constraints/indexes: {e}")
        raise


def downgrade():
    """Remove indexes, constraints, and make call_sid nullable again."""
    try:
        # Remove in reverse order
        op.drop_index('idx_calls_call_sid_status', 'calls', schema='dev')
        logger.info("Removed compound index idx_calls_call_sid_status")
        print("Migration 003 Rollback: Removed compound index idx_calls_call_sid_status")

        op.drop_index('idx_calls_call_sid', 'calls', schema='dev')
        logger.info("Removed index idx_calls_call_sid")
        print("Migration 003 Rollback: Removed index idx_calls_call_sid")

        op.drop_constraint('uq_calls_call_sid', 'calls', schema='dev')
        logger.info("Removed unique constraint uq_calls_call_sid")
        print("Migration 003 Rollback: Removed unique constraint uq_calls_call_sid")

        op.alter_column('calls', 'call_sid', nullable=True, schema='dev')
        logger.info("Made call_sid nullable")
        print("Migration 003 Rollback: Made call_sid nullable")

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        raise


# For manual execution
if __name__ == "__main__":
    print("This migration should be run through alembic or database migration tool")
    print("Manual execution not recommended")
