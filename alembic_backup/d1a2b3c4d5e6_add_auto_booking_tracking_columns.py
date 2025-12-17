"""add_auto_booking_tracking_columns

Revision ID: d1a2b3c4d5e6
Revises: c25cc07cd632
Create Date: 2025-12-09 20:20:11.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1a2b3c4d5e6'
down_revision = 'c25cc07cd632'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add auto-booking tracking columns to transport_requests table
    op.execute("""
        DO $$
        BEGIN
            -- Add auto_booked column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='transport_requests' AND column_name='auto_booked'
            ) THEN
                ALTER TABLE transport_requests
                ADD COLUMN auto_booked BOOLEAN DEFAULT FALSE NOT NULL;
            END IF;

            -- Add auto_booking_attempted_at column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='transport_requests' AND column_name='auto_booking_attempted_at'
            ) THEN
                ALTER TABLE transport_requests
                ADD COLUMN auto_booking_attempted_at TIMESTAMP;
            END IF;

            -- Add auto_booking_error column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='transport_requests' AND column_name='auto_booking_error'
            ) THEN
                ALTER TABLE transport_requests
                ADD COLUMN auto_booking_error TEXT;
            END IF;

            -- Add pooled_with_request_ids column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='transport_requests' AND column_name='pooled_with_request_ids'
            ) THEN
                ALTER TABLE transport_requests
                ADD COLUMN pooled_with_request_ids TEXT;
            END IF;

            -- Add is_pool_leader column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='transport_requests' AND column_name='is_pool_leader'
            ) THEN
                ALTER TABLE transport_requests
                ADD COLUMN is_pool_leader BOOLEAN DEFAULT FALSE NOT NULL;
            END IF;
        END $$;
    """)

    # Create indexes for better query performance
    op.execute("""
        DO $$
        BEGIN
            -- Create index on auto_booked and event_id if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename='transport_requests' AND indexname='idx_transport_requests_auto_booked_event'
            ) THEN
                CREATE INDEX idx_transport_requests_auto_booked_event
                ON transport_requests(auto_booked, event_id);
            END IF;

            -- Create partial index on is_pool_leader if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename='transport_requests' AND indexname='idx_transport_requests_pool_leader'
            ) THEN
                CREATE INDEX idx_transport_requests_pool_leader
                ON transport_requests(is_pool_leader) WHERE is_pool_leader = true;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Drop indexes
    op.execute("""
        DROP INDEX IF EXISTS idx_transport_requests_pool_leader;
        DROP INDEX IF EXISTS idx_transport_requests_auto_booked_event;
    """)

    # Drop columns
    op.execute("""
        ALTER TABLE transport_requests
        DROP COLUMN IF EXISTS is_pool_leader,
        DROP COLUMN IF EXISTS pooled_with_request_ids,
        DROP COLUMN IF EXISTS auto_booking_error,
        DROP COLUMN IF EXISTS auto_booking_attempted_at,
        DROP COLUMN IF EXISTS auto_booked;
    """)
