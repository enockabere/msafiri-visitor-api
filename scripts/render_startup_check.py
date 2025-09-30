"""
Startup check for Render deployment - ensures database is ready
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import time
from sqlalchemy import create_engine, text
from app.core.config import settings

def wait_for_database(max_attempts=30, delay=2):
    """Wait for database to be ready"""
    print("🔄 Waiting for database connection...")
    
    for attempt in range(max_attempts):
        try:
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.scalar()
            print("✅ Database connection successful!")
            return True
            
        except Exception as e:
            print(f"⏳ Attempt {attempt + 1}/{max_attempts}: {e}")
            if attempt < max_attempts - 1:
                time.sleep(delay)
            
    print("❌ Database connection failed after all attempts")
    return False

def check_tables_exist():
    """Check if required tables exist"""
    print("🔍 Checking database tables...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Check for core tables
            tables_to_check = ['users', 'tenants', 'notifications']
            missing_tables = []
            
            for table in tables_to_check:
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """))
                
                if not result.scalar():
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"⚠️  Missing tables: {missing_tables}")
                return False
            else:
                print("✅ All required tables exist")
                return True
                
    except Exception as e:
        print(f"❌ Table check failed: {e}")
        return False

def ensure_super_admin():
    """Ensure super admin exists"""
    print("👤 Checking super admin...")
    
    try:
        from sqlalchemy.orm import Session
        from app.db.database import SessionLocal
        from app.models.user import User, UserRole, AuthProvider, UserStatus
        from app.core.security import get_password_hash
        
        email = "abereenock95@gmail.com"
        
        db = SessionLocal()
        
        try:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                print(f"✅ Super admin exists: {email}")
                return True
            else:
                print("🔧 Creating super admin...")
                hashed_password = get_password_hash("SuperAdmin2025!")
                
                super_admin = User(
                    email=email,
                    hashed_password=hashed_password,
                    full_name="Super Administrator",
                    role=UserRole.SUPER_ADMIN,
                    status=UserStatus.ACTIVE,
                    is_active=True,
                    tenant_id=None,
                    auth_provider=AuthProvider.LOCAL
                )
                
                db.add(super_admin)
                db.commit()
                print(f"✅ Super admin created: {email}")
                return True
                
        except Exception as e:
            print(f"❌ Super admin setup failed: {e}")
            db.rollback()
            return False
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Super admin check failed: {e}")
        return False

def main():
    """Main startup check"""
    print("🚀 RENDER STARTUP CHECK")
    print("=" * 40)
    
    # Step 1: Wait for database
    if not wait_for_database():
        sys.exit(1)
    
    # Step 2: Check tables
    if not check_tables_exist():
        print("⚠️  Tables missing - this should have been handled in build")
        # Don't fail - the app might still work
    
    # Step 3: Ensure super admin
    if not ensure_super_admin():
        print("⚠️  Super admin setup failed - but continuing")
        # Don't fail - admin can be created later
    
    print("\n✅ STARTUP CHECK COMPLETED")
    print("🎯 Ready to start the application")

if __name__ == "__main__":
    main()