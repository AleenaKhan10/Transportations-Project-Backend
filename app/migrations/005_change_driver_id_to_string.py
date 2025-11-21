"""
Migration 005: Change driver_id from INTEGER to VARCHAR and add foreign key

This migration changes the driver_id column type from INTEGER to VARCHAR(255)
and adds a foreign key constraint to driversdirectory.driverId.

Steps:
1. Drop existing driver_id column (if INTEGER)
2. Add new driver_id column as VARCHAR(255) nullable
3. Add foreign key constraint to driversdirectory.driverId

Author: Claude Code
Date: 2025-11-21
"""

from alembic import op
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """Change driver_id to VARCHAR and add foreign key constraint."""
    connection = op.get_bind()

    try:
        # Check current driver_id column type
        result = connection.execute(text("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'dev'
            AND table_name = 'calls'
            AND column_name = 'driver_id'
        """))

        current_type = result.scalar()
        logger.info(f"Current driver_id type: {current_type}")
        print(f"Migration 005: Current driver_id type: {current_type}")

        # If already VARCHAR/character varying, just add foreign key if missing
        if current_type and 'character' in current_type.lower():
            logger.info("driver_id is already VARCHAR type, checking foreign key")
            print("Migration 005: driver_id is already VARCHAR type, checking foreign key")

            # Check if foreign key exists
            fk_result = connection.execute(text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = 'dev'
                AND table_name = 'calls'
                AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%driver_id%'
            """))

            if not fk_result.fetchone():
                logger.info("Adding foreign key constraint")
                print("Migration 005: Adding foreign key constraint")

                connection.execute(text("""
                    ALTER TABLE dev.calls
                    ADD CONSTRAINT fk_calls_driver_id
                    FOREIGN KEY (driver_id)
                    REFERENCES dev.driversdirectory(driverId)
                    ON DELETE SET NULL
                """))

                logger.info("Foreign key constraint added successfully")
                print("Migration 005: Foreign key constraint added successfully")
            else:
                logger.info("Foreign key constraint already exists")
                print("Migration 005: Foreign key constraint already exists")

            connection.commit()
            return

        # If INTEGER type, need to change to VARCHAR
        logger.info("Converting driver_id from INTEGER to VARCHAR(255)")
        print("Migration 005: Converting driver_id from INTEGER to VARCHAR(255)")

        # First, drop any existing constraints on driver_id
        connection.execute(text("""
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
        connection.execute(text("""
            ALTER TABLE dev.calls
            ALTER COLUMN driver_id TYPE VARCHAR(255)
            USING CAST(driver_id AS VARCHAR(255))
        """))

        logger.info("Changed driver_id column type to VARCHAR(255)")
        print("Migration 005: Changed driver_id column type to VARCHAR(255)")

        # Add foreign key constraint
        connection.execute(text("""
            ALTER TABLE dev.calls
            ADD CONSTRAINT fk_calls_driver_id
            FOREIGN KEY (driver_id)
            REFERENCES dev.driversdirectory(driverId)
            ON DELETE SET NULL
        """))

        logger.info("Added foreign key constraint to driversdirectory.driverId")
        print("Migration 005: Added foreign key constraint to driversdirectory.driverId")

        connection.commit()

        logger.info("Migration 005 completed successfully")
        print("Migration 005: Completed successfully")

    except Exception as e:
        logger.error(f"Migration 005 failed: {e}")
        print(f"Migration 005 failed: {e}")
        connection.rollback()
        raise


def downgrade():
    """Revert driver_id back to INTEGER and remove foreign key."""
    connection = op.get_bind()

    try:
        # Drop foreign key constraint
        connection.execute(text("""
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

        logger.info("Dropped foreign key constraint")
        print("Migration 005 Rollback: Dropped foreign key constraint")

        # Change column type back to INTEGER
        connection.execute(text("""
            ALTER TABLE dev.calls
            ALTER COLUMN driver_id TYPE INTEGER
            USING CASE
                WHEN driver_id ~ '^[0-9]+$' THEN CAST(driver_id AS INTEGER)
                ELSE NULL
            END
        """))

        logger.info("Changed driver_id back to INTEGER")
        print("Migration 005 Rollback: Changed driver_id back to INTEGER")

        connection.commit()

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        print(f"Migration 005 Rollback failed: {e}")
        connection.rollback()
        raise


# For manual execution
if __name__ == "__main__":
    print("This migration should be run through alembic or database migration tool")
    print("Manual execution not recommended")
