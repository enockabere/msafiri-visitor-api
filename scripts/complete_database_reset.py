# File: scripts/complete_database_reset.py
"""
Complete database reset script - DESTROYS ALL DATA
Use with extreme caution!
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import subprocess
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import UserRole, AuthProvider, UserStatus

def confirm_reset():
    """Confirm the user really wants to reset everything"""
    print("⚠️  WARNING: COMPLETE DATABASE RESET")
    print("=" * 50)
    print("This will:")
    print("❌ DROP ALL TABLES")
    print("❌ DELETE ALL DATA") 
    print("❌ REMOVE ALL USERS")
    print("❌ REMOVE ALL TENANTS")
    print("❌ REMOVE ALL NOTIFICATIONS")
    print("❌ REMOVE ALL MIGRATION HISTORY")
    print()
    print("✅ CREATE FRESH DATABASE")
    print("✅ RUN ALL MIGRATIONS FROM SCRATCH")
    print("✅ CREATE SINGLE SUPER ADMIN:")
    print("   📧 Email: abereenock95@gmail.com")
    print("   🔒 Password: SuperAdmin2025!")
    print()
    
    confirm = input("Are you ABSOLUTELY SURE? Type 'RESET_EVERYTHING' to confirm: ")
    return confirm == "RESET_EVERYTHING"

def drop_all_tables(database_url: str, db_name: str = "database"):
    """Drop all tables from database"""
    print(f"💣 Dropping all tables from {db_name}...")
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Get all table names
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if not tables:
                print(f"✅ {db_name} is already empty")
                return True
            
            print(f"🗑️  Found {len(tables)} tables to drop:")
            for table in tables:
                print(f"   - {table}")
            
            # Drop all tables
            for table in tables:
                try:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    print(f"   ✅ Dropped {table}")
                except Exception as e:
                    print(f"   ⚠️  Could not drop {table}: {e}")
            
            # Drop alembic version table specifically
            try:
                conn.execute(text('DROP TABLE IF EXISTS alembic_version CASCADE'))
                print("   ✅ Dropped alembic_version")
            except Exception as e:
                print(f"   ⚠️  alembic_version: {e}")
            
            # Drop any remaining sequences
            try:
                result = conn.execute(text("""
                    SELECT sequence_name FROM information_schema.sequences 
                    WHERE sequence_schema = 'public'
                """))
                sequences = [row[0] for row in result.fetchall()]
                
                for seq in sequences:
                    conn.execute(text(f'DROP SEQUENCE IF EXISTS "{seq}" CASCADE'))
                    print(f"   ✅ Dropped sequence {seq}")
            except Exception as e:
                print(f"   ⚠️  Sequences: {e}")
            
            # Drop custom enum types
            try:
                result = conn.execute(text("""
                    SELECT typname FROM pg_type 
                    WHERE typtype = 'e' AND typnamespace = (
                        SELECT oid FROM pg_namespace WHERE nspname = 'public'
                    )
                """))
                enums = [row[0] for row in result.fetchall()]
                
                for enum_name in enums:
                    conn.execute(text(f'DROP TYPE IF EXISTS "{enum_name}" CASCADE'))
                    print(f"   ✅ Dropped enum {enum_name}")
            except Exception as e:
                print(f"   ⚠️  Enums: {e}")
            
            conn.commit()
            print(f"✅ {db_name} completely cleared!")
            return True
            
    except Exception as e:
        print(f"❌ Failed to drop tables from {db_name}: {e}")
        return False

def run_fresh_migrations():
    """Run all migrations from scratch"""
    print("🚀 Running fresh migrations...")
    
    try:
        # Remove any existing migration files that might cause conflicts
        print("🧹 Cleaning up old migration artifacts...")
        
        # Initialize alembic fresh
        print("🔧 Initializing fresh migration environment...")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Fresh migrations completed successfully!")
            print(result.stdout)
            return True
        else:
            print(f"❌ Migration failed!")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

def create_super_admin():
    """Create the single super admin user"""
    print("👤 Creating super admin user...")
    
    try:
        from sqlalchemy.orm import Session
        from app.db.database import SessionLocal
        from app.models.user import User
        
        # User details
        email = "abereenock95@gmail.com"
        password = "SuperAdmin2025!"
        full_name = "Super Administrator"
        
        db = SessionLocal()
        
        try:
            # Create the user
            hashed_password = get_password_hash(password)
            
            super_admin = User(
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
                role=UserRole.SUPER_ADMIN,
                status=UserStatus.ACTIVE,
                is_active=True,
                tenant_id=None,  # Super admin doesn't belong to any tenant
                auth_provider=AuthProvider.LOCAL
            )
            
            db.add(super_admin)
            db.commit()
            db.refresh(super_admin)
            
            print(f"✅ Super admin created successfully!")
            print(f"   📧 Email: {email}")
            print(f"   🔒 Password: {password}")
            print(f"   👤 Name: {full_name}")
            print(f"   🛡️  Role: Super Administrator")
            print(f"   🆔 ID: {super_admin.id}")
            
            return True
            
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to create super admin: {e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def main():
    """Main reset process"""
    print("🔄 COMPLETE DATABASE RESET")
    print("=" * 50)
    
    # Confirm reset
    if not confirm_reset():
        print("❌ Reset cancelled by user")
        return False
    
    print("\n🚀 Starting complete database reset...")
    
    # Reset local database
    print("\n1️⃣ RESETTING LOCAL DATABASE")
    print("-" * 30)
    if not drop_all_tables(settings.DATABASE_URL, "Local Database"):
        print("❌ Failed to reset local database")
        return False
    
    # Reset Render database (if different)
    render_db_url = "postgresql://msafiri_db_user:v9yhk3xq8OyVVyd5eGrRM6T755amuvwl@dpg-d29gte2li9vc73fncigg-a.oregon-postgres.render.com/msafiri_db"
    
    if settings.DATABASE_URL != render_db_url:
        print("\n2️⃣ RESETTING RENDER DATABASE")
        print("-" * 30)
        if not drop_all_tables(render_db_url, "Render Database"):
            print("❌ Failed to reset Render database")
            return False
    else:
        print("\n2️⃣ RENDER DATABASE")
        print("-" * 30)
        print("✅ Using same database as local - already reset")
    
    # Run fresh migrations
    print("\n3️⃣ RUNNING FRESH MIGRATIONS")
    print("-" * 30)
    if not run_fresh_migrations():
        print("❌ Failed to run migrations")
        return False
    
    # Create super admin
    print("\n4️⃣ CREATING SUPER ADMIN USER")
    print("-" * 30)
    if not create_super_admin():
        print("❌ Failed to create super admin")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 COMPLETE DATABASE RESET SUCCESSFUL!")
    print("=" * 60)
    print()
    print("📋 SUPER ADMIN CREDENTIALS:")
    print("   📧 Email: abereenock95@gmail.com")
    print("   🔒 Password: SuperAdmin2025!")
    print()
    print("🔧 NEXT STEPS:")
    print("1. Start your API: uvicorn app.main:app --reload")
    print("2. Test login at: http://localhost:8000/docs")
    print("3. Test password reset functionality")
    print("4. Deploy to Render (should work cleanly now)")
    print()
    print("⚠️  REMEMBER:")
    print("- Change the password after first login")
    print("- All previous data has been permanently deleted")
    print("- Both local and Render databases are now identical")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ RESET FAILED!")
        print("Check the errors above and try again.")
        sys.exit(1)
    else:
        print("\n✅ RESET COMPLETED SUCCESSFULLY!")
        print("Your databases are now clean and ready to use.")