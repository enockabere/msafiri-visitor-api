"""create_public_registrations_table

Revision ID: create_public_registrations_table
Revises: create_event_feedback_table
Create Date: 2025-12-14 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'pub_reg_table'
down_revision = 'create_event_feedback_table'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create public_registrations table
    op.create_table('public_registrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('oc', sa.String(length=50), nullable=True),
        sa.Column('contract_status', sa.String(length=100), nullable=True),
        sa.Column('contract_type', sa.String(length=100), nullable=True),
        sa.Column('gender_identity', sa.String(length=100), nullable=True),
        sa.Column('sex', sa.String(length=50), nullable=True),
        sa.Column('pronouns', sa.String(length=50), nullable=True),
        sa.Column('current_position', sa.String(length=255), nullable=True),
        sa.Column('country_of_work', sa.String(length=255), nullable=True),
        sa.Column('project_of_work', sa.String(length=255), nullable=True),
        sa.Column('personal_email', sa.String(length=255), nullable=True),
        sa.Column('msf_email', sa.String(length=255), nullable=True),
        sa.Column('hrco_email', sa.String(length=255), nullable=True),
        sa.Column('career_manager_email', sa.String(length=255), nullable=True),
        sa.Column('ld_manager_email', sa.String(length=255), nullable=True),
        sa.Column('line_manager_email', sa.String(length=255), nullable=True),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('travelling_internationally', sa.String(length=10), nullable=True),
        sa.Column('travelling_from_country', sa.String(length=255), nullable=True),
        sa.Column('accommodation_type', sa.String(length=255), nullable=True),
        sa.Column('dietary_requirements', sa.Text(), nullable=True),
        sa.Column('accommodation_needs', sa.Text(), nullable=True),
        sa.Column('daily_meals', sa.String(length=255), nullable=True),
        sa.Column('certificate_name', sa.String(length=255), nullable=True),
        sa.Column('badge_name', sa.String(length=255), nullable=True),
        sa.Column('motivation_letter', sa.Text(), nullable=True),
        sa.Column('code_of_conduct_confirm', sa.String(length=10), nullable=True),
        sa.Column('travel_requirements_confirm', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_public_registrations_id'), 'public_registrations', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_public_registrations_id'), table_name='public_registrations')
    op.drop_table('public_registrations')