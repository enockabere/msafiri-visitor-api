"""Add form_fields and form_responses tables

Revision ID: add_form_fields_001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_form_fields_001'
down_revision = None
depends_on = None

def upgrade():
    # Create form_fields table
    op.create_table(
        'form_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('field_label', sa.String(255), nullable=False),
        sa.Column('field_type', sa.String(50), nullable=False),
        sa.Column('field_options', sa.Text(), nullable=True),
        sa.Column('is_required', sa.Boolean(), default=False),
        sa.Column('order_index', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_protected', sa.Boolean(), default=False),
        sa.Column('section', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
    )
    
    # Create form_responses table
    op.create_table(
        'form_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=False),
        sa.Column('field_id', sa.Integer(), nullable=False),
        sa.Column('field_value', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['field_id'], ['form_fields.id'], ondelete='CASCADE'),
    )
    
    # Create indexes
    op.create_index('ix_form_fields_event_id', 'form_fields', ['event_id'])
    op.create_index('ix_form_fields_order_index', 'form_fields', ['order_index'])
    op.create_index('ix_form_responses_registration_id', 'form_responses', ['registration_id'])
    op.create_index('ix_form_responses_field_id', 'form_responses', ['field_id'])

def downgrade():
    op.drop_index('ix_form_responses_field_id', 'form_responses')
    op.drop_index('ix_form_responses_registration_id', 'form_responses')
    op.drop_index('ix_form_fields_order_index', 'form_fields')
    op.drop_index('ix_form_fields_event_id', 'form_fields')
    op.drop_table('form_responses')
    op.drop_table('form_fields')