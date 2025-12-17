"""merge loi slug and voucher scanner heads

Revision ID: merge_loi_and_voucher_heads
Revises: add_slug_to_passport_records, merge_event_voucher_scanners
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_loi_and_voucher_heads'
down_revision = ('add_slug_to_passport_records', 'merge_event_voucher_scanners')
branch_labels = None
depends_on = None

def upgrade():
    # This is a merge migration - no changes needed
    pass

def downgrade():
    # This is a merge migration - no changes needed
    pass