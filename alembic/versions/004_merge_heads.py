"""Merge multiple migration heads

Revision ID: 004_merge_heads
Revises: 003_add_registration_form_fields, create_events_table, add_user_profile_and_participant_fields, create_roles_table, add_user_consent_table, create_emergency_contacts_table, create_chat_tables, create_admin_invitations_table, add_updated_by_to_roles, add_reply_to_message_id, add_must_change_password_field, add_missing_events_columns, add_gender_column, add_country_column_to_tenants
Create Date: 2024-10-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_merge_heads'
down_revision = (
    '003_add_registration_form_fields',
    'create_events_table', 
    'add_user_profile_and_participant_fields',
    'create_roles_table',
    'add_user_consent_table',
    'create_emergency_contacts_table',
    'create_chat_tables',
    'create_admin_invitations_table',
    'add_updated_by_to_roles',
    'add_reply_to_message_id',
    'add_must_change_password_field',
    'add_missing_events_columns',
    'add_gender_column',
    'add_country_column_to_tenants'
)
branch_labels = None
depends_on = None

def upgrade() -> None:
    # This is a merge migration - no schema changes needed
    pass

def downgrade() -> None:
    # This is a merge migration - no schema changes needed
    pass