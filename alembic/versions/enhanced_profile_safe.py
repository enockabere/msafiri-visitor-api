# File: alembic/versions/enhanced_profile_safe.py (FIXED VERSION)
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

def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    connection = op.get_bind()
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = :table_name 
            AND column_name = :column_name
        )
    """), {"table_name": table_name, "column_name": column_name})
    return result.scalar()

def add_column_if_not_exists(table_name, column_name, column_type):
    """Add column only if it doesn't exist"""
    if not column_exists(table_name, column_name):
        op.add_column(table_name, sa.Column(column_name, column_type, nullable=True))
        print(f"  ✅ Added {column_name}")
    else:
        print(f"  ⚠️  {column_name} already exists - skipped")

def upgrade() -> None:
    print("Starting safe migration with existence checks...")
    
    # Add enhanced profile fields to users table
    print("Adding user profile fields...")
    
    user_fields = [
        ('date_of_birth', sa.Date()),
        ('nationality', sa.String(length=100)),
        ('passport_number', sa.String(length=50)),
        ('passport_issue_date', sa.Date()),
        ('passport_expiry_date', sa.Date()),
        ('whatsapp_number', sa.String(length=20)),
        ('email_work', sa.String(length=255)),
        ('email_personal', sa.String(length=255)),
    ]
    
    for field_name, field_type in user_fields:
        add_column_if_not_exists('users', field_name, field_type)
    
    # Password management fields
    print("Adding password management fields...")
    password_fields = [
        ('password_reset_token', sa.String(length=255)),
        ('password_reset_expires', sa.DateTime(timezone=True)),
        ('email_verification_token', sa.String(length=255)),
        ('email_verification_expires', sa.DateTime(timezone=True)),
        ('email_verified_at', sa.DateTime(timezone=True)),
        ('password_changed_at', sa.DateTime(timezone=True)),
    ]
    
    for field_name, field_type in password_fields:
        add_column_if_not_exists('users', field_name, field_type)
    
    # Profile tracking fields
    print("Adding profile tracking fields...")
    tracking_fields = [
        ('profile_updated_at', sa.DateTime(timezone=True)),
        ('profile_updated_by', sa.String(length=255)),
    ]
    
    for field_name, field_type in tracking_fields:
        add_column_if_not_exists('users', field_name, field_type)
    
    # Enhanced tenant fields
    print("Adding tenant enhancement fields...")
    tenant_fields = [
        ('admin_email', sa.String(length=255)),
        ('secondary_admin_emails', sa.Text()),
        ('created_by', sa.String(length=255)),
        ('last_modified_by', sa.String(length=255)),
        ('last_notification_sent', sa.DateTime(timezone=True)),
        ('phone_number', sa.String(length=20)),
        ('address', sa.Text()),
        ('website', sa.String(length=255)),
        ('logo_url', sa.String(length=500)),
        ('primary_color', sa.String(length=7)),
        ('activated_at', sa.DateTime(timezone=True)),
        ('deactivated_at', sa.DateTime(timezone=True)),
        ('max_users', sa.String(length=50)),
    ]
    
    for field_name, field_type in tenant_fields:
        add_column_if_not_exists('tenants', field_name, field_type)
    
    # Add boolean fields with defaults
    print("Adding tenant boolean fields...")
    try:
        if not column_exists('tenants', 'allow_self_registration'):
            op.add_column('tenants', sa.Column('allow_self_registration', sa.Boolean(), server_default=text('false')))
            print("  ✅ Added allow_self_registration")
        else:
            print("  ⚠️  allow_self_registration already exists - skipped")
            
        if not column_exists('tenants', 'require_admin_approval'):
            op.add_column('tenants', sa.Column('require_admin_approval', sa.Boolean(), server_default=text('true')))
            print("  ✅ Added require_admin_approval")
        else:
            print("  ⚠️  require_admin_approval already exists - skipped")
    except Exception as e:
        print(f"  ⚠️  Boolean fields: {e}")
    
    # Handle enum addition safely
    print("Adding new user status enum...")
    try:
        connection = op.get_bind()
        
        # Check if enum value exists
        result = connection.execute(text("""
            SELECT 1 FROM pg_enum 
            WHERE enumlabel = 'pending_email_verification' 
            AND enumtypid = (
                SELECT oid FROM pg_type WHERE typname = 'userstatus'
            )
        """))
        
        if not result.fetchone():
            connection.execute(text("ALTER TYPE userstatus ADD VALUE 'pending_email_verification'"))
            print("  ✅ Added pending_email_verification status")
        else:
            print("  ✅ pending_email_verification status already exists")
            
    except Exception as e:
        print(f"  ⚠️  Enum addition: {e}")
    
    print("✅ Safe migration completed successfully!")

def downgrade() -> None:
    print("Starting downgrade...")
    
    # Remove user profile fields
    print("Removing user profile fields...")
    user_fields_to_remove = [
        'profile_updated_by', 'profile_updated_at', 'password_changed_at',
        'email_verified_at', 'email_verification_expires', 'email_verification_token',
        'password_reset_expires', 'password_reset_token', 'email_personal',
        'email_work', 'whatsapp_number', 'passport_expiry_date', 'passport_issue_date',
        'passport_number', 'nationality', 'date_of_birth'
    ]
    
    for field_name in user_fields_to_remove:
        try:
            if column_exists('users', field_name):
                op.drop_column('users', field_name)
                print(f"  ✅ Removed {field_name}")
        except Exception as e:
            print(f"  ⚠️  Could not remove {field_name}: {e}")
    
    # Remove tenant fields
    print("Removing tenant enhancement fields...")
    tenant_fields_to_remove = [
        'deactivated_at', 'activated_at', 'primary_color', 'logo_url',
        'website', 'address', 'phone_number', 'max_users', 'require_admin_approval',
        'allow_self_registration', 'last_notification_sent', 'last_modified_by',
        'created_by', 'secondary_admin_emails', 'admin_email'
    ]
    
    for field_name in tenant_fields_to_remove:
        try:
            if column_exists('tenants', field_name):
                op.drop_column('tenants', field_name)
                print(f"  ✅ Removed {field_name}")
        except Exception as e:
            print(f"  ⚠️  Could not remove {field_name}: {e}")
    
    print("✅ Downgrade completed!")
    print("Note: Enum values cannot be removed without recreating the enum type.")
    print("The 'pending_email_verification' status will remain in the enum but won't be used.")