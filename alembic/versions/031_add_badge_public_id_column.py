"""Add badge_public_id column to participant_badges

Revision ID: 031_add_badge_public_id
Revises: 030_fix_participant_certificates
Create Date: 2026-01-15 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '031_add_badge_public_id'
down_revision = '030_fix_participant_certificates'
branch_labels = None
depends_on = None


def upgrade():
    # Add badge_public_id column if it doesn't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'participant_badges' 
                AND column_name = 'badge_public_id'
            ) THEN
                ALTER TABLE participant_badges 
                ADD COLUMN badge_public_id VARCHAR(255);
            END IF;
        END $$;
    """)


def downgrade():
    op.drop_column('participant_badges', 'badge_public_id')
