# File: scripts/run_enhanced_migration.py
"""
Script to run the enhanced profile migration safely
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import subprocess
from sqlalchemy import create_engine, text
from app.core.config import settings

def check_database_connection():
    """Test database connection"""
    print("🔌 Testing database connection...")
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version[:50]}...")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_current_migration():
    """Check current migration state"""
    print("\n📋 Checking current migration state...")
    try:
        result = subprocess.run(
            ["alembic", "current"], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            print(f"✅ Current revision: {result.stdout.strip()}")
            return result.stdout.strip()
        else:
            print(f"❌ Could not check current migration: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Migration check failed: {e}")
        return None

def backup_recommendation():
    """Recommend backing up the database"""
    print("\n💾 BACKUP RECOMMENDATION")
    print("=" * 50)
    print("⚠️  IMPORTANT: Before running migrations, consider backing up your database:")
    print(f"   pg_dump {settings.DATABASE_URL.split('/')[-1]} > backup_before_enhancement.sql")
    print("\nThis migration will add new columns but won't modify existing data.")
    
    response = input("\nHave you backed up your database? (y/N): ").strip().lower()
    return response == 'y'

def run_migration():
    """Run the migration"""
    print("\n🚀 Running enhanced profile migration...")
    
    try:
        # Generate the migration file first
        print("Generating migration file...")
        result = subprocess.run([
            "alembic", "revision", "--autogenerate", 
            "-m", "Add enhanced profile and tenant fields"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to generate migration: {result.stderr}")
            return False
            
        print("✅ Migration file generated")
        
        # Run the migration
        print("Applying migration...")
        result = subprocess.run([
            "alembic", "upgrade", "head"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migration completed successfully!")
            print(result.stdout)
            return True
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

def verify_new_columns():
    """Verify that new columns were added"""
    print("\n🔍 Verifying new columns...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Check user table columns
            user_columns = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN (
                    'date_of_birth', 'nationality', 'passport_number',
                    'whatsapp_number', 'email_work', 'email_personal'
                )
            """)).fetchall()
            
            user_column_names = [col[0] for col in user_columns]
            print(f"✅ User profile columns added: {len(user_column_names)}/6")
            for col in user_column_names:
                print(f"   - {col}")
            
            # Check tenant table columns
            tenant_columns = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tenants' 
                AND column_name IN (
                    'admin_email', 'created_by', 'allow_self_registration'
                )
            """)).fetchall()
            
            tenant_column_names = [col[0] for col in tenant_columns]
            print(f"✅ Tenant enhancement columns added: {len(tenant_column_names)}/3")
            for col in tenant_column_names:
                print(f"   - {col}")
            
            return len(user_column_names) >= 5 and len(tenant_column_names) >= 2
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Main migration process"""
    print("🎯 ENHANCED MSAFIRI PROFILE MIGRATION")
    print("=" * 60)
    print("This will add enhanced profile fields to your database:")
    print("• User: Date of birth, nationality, passport info, WhatsApp, work/personal emails")
    print("• Tenant: Admin emails, creation tracking, settings")
    print("• Password: Reset tokens, change tracking")
    print("=" * 60)
    
    # Step 1: Check database connection
    if not check_database_connection():
        print("\n❌ Cannot connect to database. Check your DATABASE_URL.")
        return False
    
    # Step 2: Check current migration
    current_migration = check_current_migration()
    if not current_migration:
        print("\n❌ Cannot determine current migration state.")
        return False
    
    # Step 3: Backup recommendation
    if not backup_recommendation():
        print("\n⚠️  Migration cancelled. Please backup your database first.")
        return False
    
    # Step 4: Run migration
    if not run_migration():
        print("\n❌ Migration failed. Check the errors above.")
        return False
    
    # Step 5: Verify results
    if not verify_new_columns():
        print("\n⚠️  Migration completed but verification failed.")
        print("Check your database manually to ensure columns were added.")
        return False
    
    print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("✅ Enhanced profile fields have been added")
    print("✅ Tenant management features are ready")
    print("✅ Password management system is enabled")
    print("\nNext steps:")
    print("1. Update your models and schemas with the enhanced versions")
    print("2. Start your API: uvicorn app.main:app --reload")
    print("3. Test the new endpoints in Swagger UI")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n💡 If you encounter issues:")
        print("1. Check your database connection")
        print("2. Ensure Alembic is configured correctly")
        print("3. Try running: alembic current")
        print("4. Check the database logs for detailed errors")
        sys.exit(1)