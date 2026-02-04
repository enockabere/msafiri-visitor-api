"""Add voucher_type to event_allocations

Revision ID: 095_add_voucher_type_to_allocations
Revises: 094_make_registration_id_nullable
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '095_add_voucher_type_to_allocations'
down_revision = '094_make_registration_id_nullable'
branch_labels = None
depends_on = None

def upgrade():
    # Add voucher_type column
    op.add_column('event_allocations', sa.Column('voucher_type', sa.String(), nullable=True))
    
    # Add vouchers_per_participant column (new generic field)
    op.add_column('event_allocations', sa.Column('vouchers_per_participant', sa.Integer(), nullable=True, default=0))
    
    # Migrate existing data: copy drink_vouchers_per_participant to vouchers_per_participant and set voucher_type
    op.execute("""
        UPDATE event_allocations 
        SET vouchers_per_participant = drink_vouchers_per_participant,
            voucher_type = 'Drinks'
        WHERE drink_vouchers_per_participant > 0
    """)

def downgrade():
    # Remove the new columns
    op.drop_column('event_allocations', 'vouchers_per_participant')
    op.drop_column('event_allocations', 'voucher_type')