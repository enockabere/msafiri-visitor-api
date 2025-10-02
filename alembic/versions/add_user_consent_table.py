"""Add user consent table for data protection and terms acceptance

Revision ID: add_user_consent_001
Revises: 
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_user_consent_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create user_consents table
    op.create_table('user_consents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('data_protection_accepted', sa.Boolean(), nullable=True, default=False),
        sa.Column('terms_conditions_accepted', sa.Boolean(), nullable=True, default=False),
        sa.Column('data_protection_version', sa.String(), nullable=True),
        sa.Column('terms_conditions_version', sa.String(), nullable=True),
        sa.Column('data_protection_link', sa.Text(), nullable=True),
        sa.Column('terms_conditions_link', sa.Text(), nullable=True),
        sa.Column('data_protection_accepted_at', sa.DateTime(), nullable=True),
        sa.Column('terms_conditions_accepted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_consents_id'), 'user_consents', ['id'], unique=False)
    op.create_index(op.f('ix_user_consents_user_id'), 'user_consents', ['user_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_user_consents_user_id'), table_name='user_consents')
    op.drop_index(op.f('ix_user_consents_id'), table_name='user_consents')
    op.drop_table('user_consents')