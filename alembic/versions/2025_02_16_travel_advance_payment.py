"""Add payment and accommodation fields to travel_advances

Revision ID: 2025_02_16_advance_payment
Revises: 2025_02_12_fix_travelertype
Create Date: 2025-02-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_02_16_advance_payment'
down_revision = '2025_02_12_fix_travelertype'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new enum types
    accommodation_type_enum = sa.Enum(
        'full_board', 'half_board', 'bed_and_breakfast', 'bed_only',
        name='accommodationtype'
    )
    payment_method_enum = sa.Enum(
        'cash', 'mpesa', 'bank',
        name='advancepaymentmethod'
    )
    cash_hours_enum = sa.Enum(
        'morning', 'afternoon',
        name='advancecashhours'
    )

    # Create enum types
    accommodation_type_enum.create(op.get_bind(), checkfirst=True)
    payment_method_enum.create(op.get_bind(), checkfirst=True)
    cash_hours_enum.create(op.get_bind(), checkfirst=True)

    # Add currency column
    op.add_column('travel_advances',
        sa.Column('currency', sa.String(3), nullable=False, server_default='KES'))

    # Add accommodation type for per diem
    op.add_column('travel_advances',
        sa.Column('accommodation_type', accommodation_type_enum, nullable=True))

    # Add payment method fields
    op.add_column('travel_advances',
        sa.Column('payment_method', payment_method_enum, nullable=False, server_default='cash'))
    op.add_column('travel_advances',
        sa.Column('cash_pickup_date', sa.Date(), nullable=True))
    op.add_column('travel_advances',
        sa.Column('cash_hours', cash_hours_enum, nullable=True))
    op.add_column('travel_advances',
        sa.Column('mpesa_number', sa.String(20), nullable=True))
    op.add_column('travel_advances',
        sa.Column('bank_account', sa.String(50), nullable=True))

    # Update expense_category enum to replace ticket with transport
    # First, update any existing ticket values to transport
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE travel_advances
        SET expense_category = 'transport'
        WHERE expense_category = 'ticket'
    """))


def downgrade() -> None:
    # Drop columns
    op.drop_column('travel_advances', 'bank_account')
    op.drop_column('travel_advances', 'mpesa_number')
    op.drop_column('travel_advances', 'cash_hours')
    op.drop_column('travel_advances', 'cash_pickup_date')
    op.drop_column('travel_advances', 'payment_method')
    op.drop_column('travel_advances', 'accommodation_type')
    op.drop_column('travel_advances', 'currency')

    # Drop enum types
    sa.Enum(name='advancecashhours').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='advancepaymentmethod').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='accommodationtype').drop(op.get_bind(), checkfirst=True)
