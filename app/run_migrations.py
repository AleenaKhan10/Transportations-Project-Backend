"""
Migration runner for call_sid refactor migrations.

This script runs the 4 sequential migrations to add call_sid support to the Call model.
Migrations are executed in order: 001 -> 002 -> 003 -> 004

Usage:
    python run_migrations.py
"""

from sqlalchemy import text, inspect
from db.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_column_exists(table_name: str, column_name: str, schema: str = 'dev') -> bool:
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name, schema=schema)
    return any(col['name'] == column_name for col in columns)


def migration_001_add_call_sid_column():
    """Migration 001: Add call_sid column as nullable."""
    logger.info("Running Migration 001: Add call_sid column")

    if check_column_exists('calls', 'call_sid'):
        logger.info("call_sid column already exists, skipping migration 001")
        return

    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE dev.calls
            ADD COLUMN call_sid VARCHAR(255) NULL
        """))

    logger.info("✓ Migration 001 completed: Added call_sid column (nullable)")


def migration_002_backfill_call_sid():
    """Migration 002: Backfill call_sid for existing records."""
    logger.info("Running Migration 002: Backfill call_sid values")

    with engine.begin() as conn:
        # Check if there are any NULL call_sid values
        result = conn.execute(text("""
            SELECT COUNT(*) FROM dev.calls WHERE call_sid IS NULL
        """))
        null_count = result.scalar()

        if null_count == 0:
            logger.info("No NULL call_sid values found, skipping migration 002")
            return

        logger.info(f"Backfilling {null_count} records with generated call_sid values")

        # Backfill using format: EL_{driver_id}_{created_at_timestamp}
        conn.execute(text("""
            UPDATE dev.calls
            SET call_sid = CONCAT(
                'EL_',
                COALESCE(CAST(driver_id AS VARCHAR), 'UNKNOWN'),
                '_',
                CAST(EXTRACT(EPOCH FROM created_at) AS INTEGER)
            )
            WHERE call_sid IS NULL
        """))

    logger.info("✓ Migration 002 completed: Backfilled call_sid values")


def migration_003_add_call_sid_constraints():
    """Migration 003: Add NOT NULL constraint, unique constraint, and indexes."""
    logger.info("Running Migration 003: Add constraints and indexes")

    with engine.begin() as conn:
        # Check if constraint already exists
        result = conn.execute(text("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_schema = 'dev'
            AND table_name = 'calls'
            AND constraint_name = 'uq_calls_call_sid'
        """))

        if result.fetchone():
            logger.info("Constraints already exist, skipping migration 003")
            return

        # Add NOT NULL constraint
        conn.execute(text("""
            ALTER TABLE dev.calls
            ALTER COLUMN call_sid SET NOT NULL
        """))
        logger.info("  - Set call_sid to NOT NULL")

        # Add unique constraint
        conn.execute(text("""
            ALTER TABLE dev.calls
            ADD CONSTRAINT uq_calls_call_sid UNIQUE (call_sid)
        """))
        logger.info("  - Added unique constraint on call_sid")

        # Check and add single column index
        result = conn.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'dev'
            AND tablename = 'calls'
            AND indexname = 'idx_calls_call_sid'
        """))

        if not result.fetchone():
            conn.execute(text("""
                CREATE INDEX idx_calls_call_sid ON dev.calls (call_sid)
            """))
            logger.info("  - Created index idx_calls_call_sid")

        # Check and add compound index
        result = conn.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'dev'
            AND tablename = 'calls'
            AND indexname = 'idx_calls_call_sid_status'
        """))

        if not result.fetchone():
            conn.execute(text("""
                CREATE INDEX idx_calls_call_sid_status ON dev.calls (call_sid, status)
            """))
            logger.info("  - Created compound index idx_calls_call_sid_status")

    logger.info("✓ Migration 003 completed: Added constraints and indexes")


def migration_004_make_conversation_id_nullable():
    """Migration 004: Make conversation_id nullable."""
    logger.info("Running Migration 004: Make conversation_id nullable")

    with engine.begin() as conn:
        # Check if conversation_id is already nullable
        result = conn.execute(text("""
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'dev'
            AND table_name = 'calls'
            AND column_name = 'conversation_id'
        """))

        row = result.fetchone()
        if row and row[0] == 'YES':
            logger.info("conversation_id is already nullable, skipping migration 004")
            return

        # Make conversation_id nullable
        conn.execute(text("""
            ALTER TABLE dev.calls
            ALTER COLUMN conversation_id DROP NOT NULL
        """))

    logger.info("Migration 004 completed: Made conversation_id nullable")


def migration_005_change_driver_id_to_string():
    """Migration 005: Change driver_id to VARCHAR and add foreign key."""
    logger.info("Running Migration 005: Change driver_id to VARCHAR and add foreign key")

    with engine.begin() as conn:
        # Check current driver_id column type
        result = conn.execute(text("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'dev'
            AND table_name = 'calls'
            AND column_name = 'driver_id'
        """))

        current_type = result.scalar()
        logger.info(f"Current driver_id type: {current_type}")

        # If already VARCHAR/character varying, just add foreign key if missing
        if current_type and 'character' in current_type.lower():
            logger.info("driver_id is already VARCHAR type, checking foreign key")

            # Check if foreign key exists
            fk_result = conn.execute(text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = 'dev'
                AND table_name = 'calls'
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%driver_id%'
            """))

            if not fk_result.fetchone():
                logger.info("Adding foreign key constraint")

                conn.execute(text("""
                    ALTER TABLE dev.calls
                    ADD CONSTRAINT fk_calls_driver_id
                    FOREIGN KEY (driver_id)
                    REFERENCES dev.driversdirectory("driverId")
                    ON DELETE SET NULL
                """))

                logger.info("Foreign key constraint added successfully")
            else:
                logger.info("Foreign key constraint already exists")

            logger.info("Migration 005 completed: driver_id already VARCHAR with foreign key")
            return

        # If INTEGER type, need to change to VARCHAR
        logger.info("Converting driver_id from INTEGER to VARCHAR(255)")

        # First, drop any existing constraints on driver_id
        conn.execute(text("""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_schema = 'dev'
                    AND table_name = 'calls'
                    AND constraint_type = 'FOREIGN KEY'
                    AND constraint_name LIKE '%driver_id%'
                ) LOOP
                    EXECUTE 'ALTER TABLE dev.calls DROP CONSTRAINT ' || r.constraint_name;
                END LOOP;
            END$$;
        """))

        # Change column type using USING clause for safe conversion
        conn.execute(text("""
            ALTER TABLE dev.calls
            ALTER COLUMN driver_id TYPE VARCHAR(255)
            USING CAST(driver_id AS VARCHAR(255))
        """))

        logger.info("  - Changed driver_id column type to VARCHAR(255)")

        # Add foreign key constraint
        conn.execute(text("""
            ALTER TABLE dev.calls
            ADD CONSTRAINT fk_calls_driver_id
            FOREIGN KEY (driver_id)
            REFERENCES dev.driversdirectory("driverId")
            ON DELETE SET NULL
        """))

        logger.info("  - Added foreign key constraint to driversdirectory.driverId")

    logger.info("Migration 005 completed: Changed driver_id to VARCHAR with foreign key")


def run_all_migrations():
    """Run all migrations in sequence."""
    logger.info("=" * 70)
    logger.info("Starting call_sid refactor migrations")
    logger.info("=" * 70)

    try:
        migration_001_add_call_sid_column()
        migration_002_backfill_call_sid()
        migration_003_add_call_sid_constraints()
        migration_004_make_conversation_id_nullable()
        migration_005_change_driver_id_to_string()

        logger.info("=" * 70)
        logger.info("All migrations completed successfully!")
        logger.info("=" * 70)

        # Verify final state
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT column_name, is_nullable, data_type
                FROM information_schema.columns
                WHERE table_schema = 'dev'
                AND table_name = 'calls'
                AND column_name IN ('call_sid', 'conversation_id', 'driver_id')
                ORDER BY column_name
            """))

            logger.info("\nFinal schema verification:")
            for row in result:
                logger.info(f"  {row[0]}: {row[2]} (nullable={row[1]})")

            # Check foreign key constraint
            fk_result = conn.execute(text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_schema = 'dev'
                AND table_name = 'calls'
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%driver_id%'
            """))

            logger.info("\nForeign key constraints:")
            for row in fk_result:
                logger.info(f"  {row[0]}: {row[1]}")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    run_all_migrations()
