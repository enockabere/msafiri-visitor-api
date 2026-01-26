"""Replace budget_account_code with section, budget_code, activity_code, cost_center

Revision ID: 043_replace_budget_account_code_with_new_fields
Revises: 042_add_tenant_id_to_badge_templates
Create Date: 2024-01-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '043_replace_budget_account_code_with_new_fields'
down_revision = '042_add_tenant_id_to_badge_templates'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns
    op.add_column('events', sa.Column('section', sa.String(length=10), nullable=True))
    op.add_column('events', sa.Column('budget_code', sa.String(length=50), nullable=True))
    op.add_column('events', sa.Column('activity_code', sa.String(length=50), nullable=True))
    op.add_column('events', sa.Column('cost_center', sa.String(length=50), nullable=True))
    
    # Migrate existing data from budget_account_code to section
    op.execute("UPDATE events SET section = budget_account_code WHERE budget_account_code IS NOT NULL")
    
    # Drop the old column
    op.drop_column('events', 'budget_account_code')


def downgrade():
    # Add back the old column
    op.add_column('events', sa.Column('budget_account_code', sa.String(length=10), nullable=True))
    
    # Migrate data back from section to budget_account_code
    op.execute("UPDATE events SET budget_account_code = section WHERE section IS NOT NULL")
    
    # Drop new columns
    op.drop_column('events', 'cost_center')
    op.drop_column('events', 'activity_code')
    op.drop_column('events', 'budget_code')
    op.drop_column('events', 'section')