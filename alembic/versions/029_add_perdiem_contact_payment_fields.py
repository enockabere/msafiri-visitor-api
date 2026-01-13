"""Add contact and payment fields to perdiem requests

Revision ID: 029_add_perdiem_contact_payment_fields
Revises: 028_add_travel_preference_fields
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '029_add_perdiem_contact_payment_fields'
down_revision = '028_add_travel_preference_fields'
branch_labels = None
depends_on = None

def upgrade():
    # Create new enums
    payment_method_enum = postgresql.ENUM('cash', 'mobile_money', name='paymentmethod')
    payment_method_enum.create(op.get_bind())
    
    cash_hours_enum = postgresql.ENUM('morning', 'afternoon', name='cashhours')
    cash_hours_enum.create(op.get_bind())
    
    # Update perdiem status enum
    op.execute("ALTER TYPE perdiemstatus ADD VALUE 'line_manager_approved'")
    op.execute("ALTER TYPE perdiemstatus ADD VALUE 'budget_owner_approved'")
    
    # Add new columns to perdiem_requests table
    op.add_column('perdiem_requests', sa.Column('phone_number', sa.String(20), nullable=False, server_default=''))
    op.add_column('perdiem_requests', sa.Column('email', sa.String(255), nullable=False, server_default=''))
    op.add_column('perdiem_requests', sa.Column('payment_method', payment_method_enum, nullable=False, server_default='cash'))
    op.add_column('perdiem_requests', sa.Column('cash_pickup_date', sa.Date(), nullable=True))
    op.add_column('perdiem_requests', sa.Column('cash_hours', cash_hours_enum, nullable=True))
    op.add_column('perdiem_requests', sa.Column('mpesa_number', sa.String(20), nullable=True))
    
    # Add approval workflow columns
    op.add_column('perdiem_requests', sa.Column('line_manager_approved_by', sa.String(255), nullable=True))
    op.add_column('perdiem_requests', sa.Column('line_manager_approved_at', sa.DateTime(), nullable=True))
    op.add_column('perdiem_requests', sa.Column('budget_owner_approved_by', sa.String(255), nullable=True))
    op.add_column('perdiem_requests', sa.Column('budget_owner_approved_at', sa.DateTime(), nullable=True))
    op.add_column('perdiem_requests', sa.Column('rejected_by', sa.String(255), nullable=True))
    op.add_column('perdiem_requests', sa.Column('rejected_at', sa.DateTime(), nullable=True))
    op.add_column('perdiem_requests', sa.Column('rejection_reason', sa.Text(), nullable=True))
    
    # Remove server defaults after adding columns
    op.alter_column('perdiem_requests', 'phone_number', server_default=None)
    op.alter_column('perdiem_requests', 'email', server_default=None)
    op.alter_column('perdiem_requests', 'payment_method', server_default=None)

def downgrade():
    # Remove added columns
    op.drop_column('perdiem_requests', 'rejection_reason')
    op.drop_column('perdiem_requests', 'rejected_at')
    op.drop_column('perdiem_requests', 'rejected_by')
    op.drop_column('perdiem_requests', 'budget_owner_approved_at')
    op.drop_column('perdiem_requests', 'budget_owner_approved_by')
    op.drop_column('perdiem_requests', 'line_manager_approved_at')
    op.drop_column('perdiem_requests', 'line_manager_approved_by')
    op.drop_column('perdiem_requests', 'mpesa_number')
    op.drop_column('perdiem_requests', 'cash_hours')
    op.drop_column('perdiem_requests', 'cash_pickup_date')
    op.drop_column('perdiem_requests', 'payment_method')
    op.drop_column('perdiem_requests', 'email')
    op.drop_column('perdiem_requests', 'phone_number')
    
    # Drop enums
    op.execute('DROP TYPE cashhours')
    op.execute('DROP TYPE paymentmethod')