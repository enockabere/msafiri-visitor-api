"""Add user bank accounts table with encryption

Revision ID: add_user_bank_accounts
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'add_user_bank_accounts'
down_revision = None  # Update this with your latest migration
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_bank_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bank_name_encrypted', sa.String(), nullable=False),
        sa.Column('account_name_encrypted', sa.String(), nullable=False),
        sa.Column('account_number_encrypted', sa.String(), nullable=False),
        sa.Column('branch_name_encrypted', sa.String(), nullable=True),
        sa.Column('swift_code_encrypted', sa.String(), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_bank_accounts_id'), 'user_bank_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_user_bank_accounts_user_id'), 'user_bank_accounts', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_user_bank_accounts_user_id'), table_name='user_bank_accounts')
    op.drop_index(op.f('ix_user_bank_accounts_id'), table_name='user_bank_accounts')
    op.drop_table('user_bank_accounts')
