"""
Migration 002: Backfill call_sid for existing Call records

Generates call_sid for all existing records using format:
EL_{driver_id}_{created_at_timestamp}

For records with NULL driver_id, uses 'UNKNOWN' as placeholder.

Author: Claude Code
Date: 2025-11-21
"""

from alembic import op
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """Backfill call_sid for all existing Call records."""
    connection = op.get_bind()

    try:
        # Get count of records to backfill
        result = connection.execute(text("""
            SELECT COUNT(*) FROM dev.calls WHERE call_sid IS NULL
        """))
        count = result.scalar()
        logger.info(f"Backfilling {count} Call records with call_sid")
        print(f"Migration 002: Backfilling {count} Call records with call_sid")

        # Update records with generated call_sid
        # Format: EL_{driver_id}_{created_at_unix_timestamp}
        # Use 'UNKNOWN' for NULL driver_id
        connection.execute(text("""
            UPDATE dev.calls
            SET call_sid = CONCAT(
                'EL_',
                COALESCE(CAST(driver_id AS VARCHAR), 'UNKNOWN'),
                '_',
                CAST(EXTRACT(EPOCH FROM created_at) AS INTEGER)
            )
            WHERE call_sid IS NULL
        """))
        connection.commit()

        logger.info(f"Successfully backfilled {count} Call records")
        print(f"Migration 002: Successfully backfilled {count} Call records")

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        connection.rollback()
        raise


def downgrade():
    """Set all call_sid values to NULL."""
    connection = op.get_bind()

    try:
        connection.execute(text("""
            UPDATE dev.calls SET call_sid = NULL
        """))
        connection.commit()
        logger.info("Set all call_sid values to NULL")
        print("Migration 002 Rollback: Set all call_sid values to NULL")

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        connection.rollback()
        raise


# For manual execution
if __name__ == "__main__":
    print("This migration should be run through alembic or database migration tool")
    print("Manual execution not recommended")
