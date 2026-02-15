"""add travel_advances table

Revision ID: 107
Revises: 106
Create Date: 2024-01-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '107'
down_revision = '106'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'travel_advances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('travel_request_id', sa.Integer(), nullable=False),
        sa.Column('traveler_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('expense_category', sa.Enum('visa_money', 'per_diem', 'security', 'ticket', name='expensecategory'), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'disbursed', name='advancestatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_by', sa.Integer(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('disbursed_by', sa.Integer(), nullable=True),
        sa.Column('disbursed_at', sa.DateTime(), nullable=True),
        sa.Column('disbursement_reference', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['travel_request_id'], ['travel_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['traveler_id'], ['travel_request_travelers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id']),
        sa.ForeignKeyConstraint(['disbursed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_travel_advances_travel_request_id'), 'travel_advances', ['travel_request_id'], unique=False)
    op.create_index(op.f('ix_travel_advances_traveler_id'), 'travel_advances', ['traveler_id'], unique=False)
    op.create_index(op.f('ix_travel_advances_user_id'), 'travel_advances', ['user_id'], unique=False)
    op.create_index(op.f('ix_travel_advances_tenant_id'), 'travel_advances', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_travel_advances_status'), 'travel_advances', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_travel_advances_status'), table_name='travel_advances')
    op.drop_index(op.f('ix_travel_advances_tenant_id'), table_name='travel_advances')
    op.drop_index(op.f('ix_travel_advances_user_id'), table_name='travel_advances')
    op.drop_index(op.f('ix_travel_advances_traveler_id'), table_name='travel_advances')
    op.drop_index(op.f('ix_travel_advances_travel_request_id'), table_name='travel_advances')
    op.drop_table('travel_advances')
    op.execute('DROP TYPE expensecategory')
    op.execute('DROP TYPE advancestatus')
