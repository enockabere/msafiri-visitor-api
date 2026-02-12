"""Fix travelertype enum case

Revision ID: 2025_02_12_fix_travelertype
Revises: 2025_02_12_acceptance
Create Date: 2025-02-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_02_12_fix_travelertype'
down_revision = '2025_02_12_acceptance'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check current enum values
    conn = op.get_bind()
    
    # Update existing data to lowercase if needed
    conn.execute(sa.text("""
        UPDATE travel_request_travelers 
        SET traveler_type = LOWER(traveler_type::text)::travelertype
        WHERE traveler_type::text IN ('SELF', 'DEPENDANT', 'STAFF')
    """))


def downgrade() -> None:
    pass
