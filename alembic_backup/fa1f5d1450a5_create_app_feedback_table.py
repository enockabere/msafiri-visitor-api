"""create_app_feedback_table

Revision ID: fa1f5d1450a5
Revises: c31ac3f9345d
Create Date: 2025-10-27 15:22:59.930426

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fa1f5d1450a5'
down_revision = 'c31ac3f9345d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create app_feedback table
    op.create_table(
        'app_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('category', sa.Enum('user_experience', 'performance', 'features', 'bug_report', 'suggestion', 'general', name='feedbackcategory'), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_app_feedback_user_id'), 'app_feedback', ['user_id'], unique=False)
    op.create_index(op.f('ix_app_feedback_rating'), 'app_feedback', ['rating'], unique=False)
    op.create_index(op.f('ix_app_feedback_category'), 'app_feedback', ['category'], unique=False)
    
    # Create feedback_prompts table
    op.create_table(
        'feedback_prompts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('last_prompted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('prompt_count', sa.Integer(), default=0),
        sa.Column('dismissed_count', sa.Integer(), default=0),
        sa.Column('has_submitted_feedback', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feedback_prompts_user_id'), 'feedback_prompts', ['user_id'], unique=True)


def downgrade() -> None:
    # Drop app_feedback table
    op.drop_index(op.f('ix_feedback_prompts_user_id'), table_name='feedback_prompts')
    op.drop_table('feedback_prompts')
    op.drop_index(op.f('ix_app_feedback_category'), table_name='app_feedback')
    op.drop_index(op.f('ix_app_feedback_rating'), table_name='app_feedback')
    op.drop_index(op.f('ix_app_feedback_user_id'), table_name='app_feedback')
    op.drop_table('app_feedback')