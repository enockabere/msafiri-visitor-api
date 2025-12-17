"""Final merge of all migration heads December 2024

Revision ID: final_merge_dec_2024
Revises: 0144f8889f85, add_additional_requirements, add_chat_mention_enum, add_invitations_table, add_pickup_confirmed, change_recommendation_to_boolean, merge_loi_and_voucher_heads, remove_accommodation_type, remove_description_standalone
Create Date: 2024-12-08 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'final_merge_dec_2024'
down_revision = (
    '0144f8889f85',
    'add_additional_requirements',
    'add_chat_mention_enum',
    'add_invitations_table',
    'add_pickup_confirmed',
    'change_recommendation_to_boolean',
    'merge_loi_and_voucher_heads',
    'remove_accommodation_type',
    'remove_description_standalone'
)
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge migration - no schema changes needed
    pass


def downgrade():
    # This is a merge migration - no schema changes needed
    pass
