"""change recommendation text to boolean

Revision ID: change_recommendation_to_boolean
Revises: fix_tenant_id_type_mismatch
Create Date: 2024-12-19 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'change_recommendation_to_boolean'
down_revision = 'fix_tenant_id_type_mismatch'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the old recommendation_text column and add new is_recommended boolean column
    op.drop_column('line_manager_recommendations', 'recommendation_text')
    op.add_column('line_manager_recommendations', sa.Column('is_recommended', sa.Boolean(), nullable=True, default=False))
    
    # Update existing records where submitted_at is not null to set is_recommended = True
    op.execute("UPDATE line_manager_recommendations SET is_recommended = TRUE WHERE submitted_at IS NOT NULL")
    
    # Make is_recommended not nullable after setting defaults
    op.alter_column('line_manager_recommendations', 'is_recommended', nullable=False, server_default=sa.false())


def downgrade():
    # Revert back to recommendation_text
    op.drop_column('line_manager_recommendations', 'is_recommended')
    op.add_column('line_manager_recommendations', sa.Column('recommendation_text', sa.Text(), nullable=True))
