# File: alembic/versions/enhanced_profile_safe.py
"""Add enhanced profile fields and tenant features (Safe Version)

Revision ID: enhanced_profile_safe
Revises: aff03164daa5
Create Date: 2025-08-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = 'enhanced_profile_safe'
down_revision = 'aff03164daa5'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add enhanced profile fields to users table
    print("Adding user profile fields...")
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('nationality', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('passport_number', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('passport_issue_date', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('passport_expiry_date', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('whatsapp_number', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('email_work', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('email_personal', sa.String(length=255), nullable=True))
    
    # Password management fields
    print("Adding password management fields...")
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('email_verification_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('email_verification_expires', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Profile tracking fields
    print("Adding profile tracking fields...")
    op.add_column('users', sa.Column('profile_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('profile_updated_by', sa.String(length=255), nullable=True))
    
    # Enhanced tenant fields
    print("Adding tenant enhancement fields...")
    op.add_column('tenants', sa.Column('admin_email', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('secondary_admin_emails', sa.Text(), nullable=True))
    op.add_column('tenants', sa.Column('created_by', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('last_modified_by', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('last_notification_sent', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenants', sa.Column('allow_self_registration', sa.Boolean(), server_default=text('false')))
    op.add_column('tenants', sa.Column('require_admin_approval', sa.Boolean(), server_default=text('true')))
    op.add_column('tenants', sa.Column('max_users', sa.String(length=50), nullable=True))
    op.add_column('tenants', sa.Column('phone_number', sa.String(length=20), nullable=True))
    op.add_column('tenants', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('tenants', sa.Column('website', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('logo_url', sa.String(length=500), nullable=True))
    op.add_column('tenants', sa.Column('primary_color', sa.String(length=7), nullable=True))
    op.add_column('tenants', sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenants', sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True))
    
    # Handle enum addition safely
    print("Adding new user status enum value...")
    connection = op.get_bind()
    
    # Check if the enum value already exists
    result = connection.execute(text("""
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'pending_email_verification' 
        AND enumtypid = (
            SELECT oid FROM pg_type WHERE typname = 'userstatus'
        )
    """))
    
    if not result.fetchone():
        try:
            connection.execute(text("ALTER TYPE userstatus ADD VALUE 'pending_email_verification'"))
            print("Added 'pending_email_verification' status")
        except Exception as e:
            print(f"Warning: Could not add enum value: {e}")
    else:
        print("Enum value 'pending_email_verification' already exists")
    
    print("Migration completed successfully!")

def downgrade() -> None:
    print("Starting downgrade...")
    
    # Remove user profile fields
    print("Removing user profile fields...")
    op.drop_column('users', 'profile_updated_by')
    op.drop_column('users', 'profile_updated_at')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'email_verification_expires')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'email_personal')
    op.drop_column('users', 'email_work')
    op.drop_column('users', 'whatsapp_number')
    op.drop_column('users', 'passport_expiry_date')
    op.drop_column('users', 'passport_issue_date')
    op.drop_column('users', 'passport_number')
    op.drop_column('users', 'nationality')
    op.drop_column('users', 'date_of_birth')
    
    # Remove tenant fields
    print("Removing tenant enhancement fields...")
    op.drop_column('tenants', 'deactivated_at')
    op.drop_column('tenants', 'activated_at')
    op.drop_column('tenants', 'primary_color')
    op.drop_column('tenants', 'logo_url')
    op.drop_column('tenants', 'website')
    op.drop_column('tenants', 'address')
    op.drop_column('tenants', 'phone_number')
    op.drop_column('tenants', 'max_users')
    op.drop_column('tenants', 'require_admin_approval')
    op.drop_column('tenants', 'allow_self_registration')
    op.drop_column('tenants', 'last_notification_sent')
    op.drop_column('tenants', 'last_modified_by')
    op.drop_column('tenants', 'created_by')
    op.drop_column('tenants', 'secondary_admin_emails')
    op.drop_column('tenants', 'admin_email')
    
    print("Downgrade completed! Note: Enum values cannot be removed without recreating the enum type.")
    print("The 'pending_email_verification' status will remain in the enum but won't be used.")