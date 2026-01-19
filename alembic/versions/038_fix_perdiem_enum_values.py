"""Fix perdiem enum values to uppercase

Revision ID: 038_fix_perdiem_enum_values
Revises: 037_add_event_travel_requirements_table
Create Date: 2025-01-19 20:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '038_fix_perdiem_enum_values'
down_revision = '037_add_event_travel_requirements_table'
branch_labels = None
depends_on = None

def upgrade():
    # Drop existing enums if they exist
    op.execute("DROP TYPE IF EXISTS paymentmethod CASCADE")
    op.execute("DROP TYPE IF EXISTS cashhours CASCADE")
    
    # Create new enums with uppercase values to match database expectation
    payment_method_enum = postgresql.ENUM('CASH', 'MOBILE_MONEY', name='paymentmethod')
    payment_method_enum.create(op.get_bind())
    
    cash_hours_enum = postgresql.ENUM('MORNING', 'AFTERNOON', name='cashhours')
    cash_hours_enum.create(op.get_bind())
    
    # Re-add columns with correct enum types
    try:
        op.add_column('perdiem_requests', sa.Column('payment_method', payment_method_enum, nullable=False, server_default='CASH'))
        op.add_column('perdiem_requests', sa.Column('cash_hours', cash_hours_enum, nullable=True))
    except:
        # Columns might already exist, alter them instead
        op.execute("ALTER TABLE perdiem_requests ALTER COLUMN payment_method TYPE paymentmethod USING payment_method::text::paymentmethod")
        op.execute("ALTER TABLE perdiem_requests ALTER COLUMN cash_hours TYPE cashhours USING cash_hours::text::cashhours")

def downgrade():
    # Drop uppercase enums
    op.execute("DROP TYPE IF EXISTS paymentmethod CASCADE")
    op.execute("DROP TYPE IF EXISTS cashhours CASCADE")
    
    # Recreate lowercase enums
    payment_method_enum = postgresql.ENUM('cash', 'mobile_money', name='paymentmethod')
    payment_method_enum.create(op.get_bind())
    
    cash_hours_enum = postgresql.ENUM('morning', 'afternoon', name='cashhours')
    cash_hours_enum.create(op.get_bind())