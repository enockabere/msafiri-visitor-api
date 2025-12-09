"""add_missing_fields_to_flight_itineraries

Revision ID: c25cc07cd632
Revises: final_merge_dec_2024
Create Date: 2025-12-09 14:48:14.022113

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c25cc07cd632'
down_revision = 'final_merge_dec_2024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to flight_itineraries table
    # These fields exist in old migrations but were never applied to production DB

    # Check if columns exist before adding (to avoid errors if they already exist)
    op.execute("""
        DO $$
        BEGIN
            -- Add itinerary_type if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='flight_itineraries' AND column_name='itinerary_type'
            ) THEN
                ALTER TABLE flight_itineraries
                ADD COLUMN itinerary_type VARCHAR(50);
            END IF;

            -- Add departure_airport if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='flight_itineraries' AND column_name='departure_airport'
            ) THEN
                ALTER TABLE flight_itineraries
                ADD COLUMN departure_airport VARCHAR(100);
            END IF;

            -- Add arrival_airport if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='flight_itineraries' AND column_name='arrival_airport'
            ) THEN
                ALTER TABLE flight_itineraries
                ADD COLUMN arrival_airport VARCHAR(100);
            END IF;

            -- Add pickup_location if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='flight_itineraries' AND column_name='pickup_location'
            ) THEN
                ALTER TABLE flight_itineraries
                ADD COLUMN pickup_location VARCHAR(255);
            END IF;
        END $$;
    """)

    # Set default value for itinerary_type on existing records
    op.execute("""
        UPDATE flight_itineraries
        SET itinerary_type = 'arrival'
        WHERE itinerary_type IS NULL;
    """)


def downgrade() -> None:
    # Remove the added columns
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='flight_itineraries' AND column_name='itinerary_type'
            ) THEN
                ALTER TABLE flight_itineraries DROP COLUMN itinerary_type;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='flight_itineraries' AND column_name='departure_airport'
            ) THEN
                ALTER TABLE flight_itineraries DROP COLUMN departure_airport;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='flight_itineraries' AND column_name='arrival_airport'
            ) THEN
                ALTER TABLE flight_itineraries DROP COLUMN arrival_airport;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='flight_itineraries' AND column_name='pickup_location'
            ) THEN
                ALTER TABLE flight_itineraries DROP COLUMN pickup_location;
            END IF;
        END $$;
    """)