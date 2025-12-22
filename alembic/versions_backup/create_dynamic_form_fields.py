"""Create dynamic form fields tables

Revision ID: create_dynamic_form_fields
Revises: change_recommendation_to_boolean
Create Date: 2024-12-19 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_dynamic_form_fields'
down_revision = '779de758951b'
branch_labels = None
depends_on = None

def upgrade():
    # Create form_fields table
    op.create_table('form_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('field_label', sa.String(255), nullable=False),
        sa.Column('field_type', sa.String(50), nullable=False),  # text, email, select, checkbox, textarea
        sa.Column('field_options', sa.Text(), nullable=True),  # JSON for select options
        sa.Column('is_required', sa.Boolean(), default=False),
        sa.Column('order_index', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create form_responses table (without foreign key to public_registrations for now)
    op.create_table('form_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('registration_id', sa.Integer(), nullable=True),
        sa.Column('field_id', sa.Integer(), nullable=False),
        sa.Column('field_value', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['field_id'], ['form_fields.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_form_fields_event_id', 'form_fields', ['event_id'])
    op.create_index('idx_form_fields_order', 'form_fields', ['event_id', 'order_index'])
    op.create_index('idx_form_responses_registration', 'form_responses', ['registration_id'])

def downgrade():
    op.drop_index('idx_form_responses_registration', 'form_responses')
    op.drop_index('idx_form_fields_order', 'form_fields')
    op.drop_index('idx_form_fields_event_id', 'form_fields')
    op.drop_table('form_responses')
    op.drop_table('form_fields')