"""Backfill deletion dates for existing passport records

Revision ID: 2025_02_18_backfill
Revises: 2025_02_18_deletion_date
Create Date: 2025-02-18 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '2025_02_18_backfill'
down_revision = '2025_02_18_deletion_date'
branch_labels = None
depends_on = None


def upgrade():
    # Update existing passport records to set deletion_date = event.end_date + 30 days
    op.execute(text("""
        UPDATE passport_records pr
        SET deletion_date = e.end_date + INTERVAL '30 days'
        FROM events e
        WHERE pr.event_id = e.id
        AND pr.deletion_date IS NULL
    """))


def downgrade():
    # Set deletion_date back to NULL for records that were backfilled
    op.execute(text("""
        UPDATE passport_records
        SET deletion_date = NULL
        WHERE deletion_date IS NOT NULL
    """))
