"""
Migration 006: Add post-call webhook metadata fields to calls table

This migration adds 6 new nullable columns to the calls table to store
post-call completion metadata from ElevenLabs webhooks:
- transcript_summary: Text summary of conversation from analysis
- call_duration_seconds: Call duration in seconds
- cost: Call cost in dollars from billing
- call_successful: Boolean success flag from analysis
- analysis_data: JSON string of full analysis results
- metadata_json: JSON string of full webhook metadata

All fields are nullable for backward compatibility with existing records.

Author: Claude Code
Date: 2025-11-21
"""

from alembic import op
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """Add post-call webhook metadata fields to calls table."""
    connection = op.get_bind()

    try:
        logger.info("Migration 006: Adding post-call webhook metadata fields")
        print("Migration 006: Adding post-call webhook metadata fields to calls table")

        # Check if columns already exist
        result = connection.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'dev'
            AND table_name = 'calls'
            AND column_name IN (
                'transcript_summary',
                'call_duration_seconds',
                'cost',
                'call_successful',
                'analysis_data',
                'metadata_json'
            )
        """))

        existing_columns = [row[0] for row in result]

        if len(existing_columns) == 6:
            logger.info("All post-call metadata columns already exist, skipping migration")
            print("Migration 006: All columns already exist, skipping")
            return

        # Add transcript_summary column
        if 'transcript_summary' not in existing_columns:
            connection.execute(text("""
                ALTER TABLE dev.calls
                ADD COLUMN transcript_summary TEXT NULL
            """))
            logger.info("Added transcript_summary column")
            print("Migration 006: Added transcript_summary column")

        # Add call_duration_seconds column
        if 'call_duration_seconds' not in existing_columns:
            connection.execute(text("""
                ALTER TABLE dev.calls
                ADD COLUMN call_duration_seconds INTEGER NULL
            """))
            logger.info("Added call_duration_seconds column")
            print("Migration 006: Added call_duration_seconds column")

        # Add cost column
        if 'cost' not in existing_columns:
            connection.execute(text("""
                ALTER TABLE dev.calls
                ADD COLUMN cost DOUBLE PRECISION NULL
            """))
            logger.info("Added cost column")
            print("Migration 006: Added cost column")

        # Add call_successful column
        if 'call_successful' not in existing_columns:
            connection.execute(text("""
                ALTER TABLE dev.calls
                ADD COLUMN call_successful BOOLEAN NULL
            """))
            logger.info("Added call_successful column")
            print("Migration 006: Added call_successful column")

        # Add analysis_data column
        if 'analysis_data' not in existing_columns:
            connection.execute(text("""
                ALTER TABLE dev.calls
                ADD COLUMN analysis_data TEXT NULL
            """))
            logger.info("Added analysis_data column")
            print("Migration 006: Added analysis_data column")

        # Add metadata_json column
        if 'metadata_json' not in existing_columns:
            connection.execute(text("""
                ALTER TABLE dev.calls
                ADD COLUMN metadata_json TEXT NULL
            """))
            logger.info("Added metadata_json column")
            print("Migration 006: Added metadata_json column")

        # Add column comments for documentation
        connection.execute(text("""
            COMMENT ON COLUMN dev.calls.transcript_summary IS 'Summary of call conversation from ElevenLabs analysis';
            COMMENT ON COLUMN dev.calls.call_duration_seconds IS 'Duration of call in seconds from metadata';
            COMMENT ON COLUMN dev.calls.cost IS 'Cost of call in dollars from ElevenLabs billing';
            COMMENT ON COLUMN dev.calls.call_successful IS 'Boolean flag indicating if call was successful';
            COMMENT ON COLUMN dev.calls.analysis_data IS 'JSON string of full analysis results';
            COMMENT ON COLUMN dev.calls.metadata_json IS 'JSON string of full metadata from webhook'
        """))

        logger.info("Added column comments")
        print("Migration 006: Added column comments")

        connection.commit()

        logger.info("Migration 006 completed successfully")
        print("Migration 006: Completed successfully - Added 6 post-call metadata fields")

    except Exception as e:
        logger.error(f"Migration 006 failed: {e}")
        print(f"Migration 006 failed: {e}")
        connection.rollback()
        raise


def downgrade():
    """Remove post-call webhook metadata fields from calls table."""
    connection = op.get_bind()

    try:
        logger.info("Migration 006 Rollback: Removing post-call metadata fields")
        print("Migration 006 Rollback: Removing post-call metadata fields")

        # Drop all 6 columns
        connection.execute(text("""
            ALTER TABLE dev.calls
            DROP COLUMN IF EXISTS transcript_summary,
            DROP COLUMN IF EXISTS call_duration_seconds,
            DROP COLUMN IF EXISTS cost,
            DROP COLUMN IF EXISTS call_successful,
            DROP COLUMN IF EXISTS analysis_data,
            DROP COLUMN IF EXISTS metadata_json
        """))

        logger.info("Dropped all post-call metadata columns")
        print("Migration 006 Rollback: Dropped all 6 columns")

        connection.commit()

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        print(f"Migration 006 Rollback failed: {e}")
        connection.rollback()
        raise


# For manual execution
if __name__ == "__main__":
    print("This migration should be run through alembic or database migration tool")
    print("Manual execution not recommended")
