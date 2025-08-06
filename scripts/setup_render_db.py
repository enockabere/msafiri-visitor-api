# File: scripts/setup_render_db.py
"""
Complete setup script for Render PostgreSQL database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import subprocess
import psycopg2
from sqlalchemy import create_engine, text
from app.core.config import settings

# Your Render database credentials
RENDER_DATABASE_URL = "postgresql://msafiri_db_user:v9yhk3xq8OyVVyd5eGrRM6T755amuvwl@dpg-d29gte2li9vc73fncigg-a.oregon-postgres.render.com/msafiri_db"

def test_connection():
    """Test connection to Render database"""
    print("🔌 Testing connection to Render PostgreSQL...")
    
    try:
        engine = create_engine(RENDER_DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Connected successfully!")
            print(f"📋 PostgreSQL Version: {version[:50]}...")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def run_migrations():
    """Run Alembic migrations"""
    print("\n📋 Running database migrations...")
    
    try:
        # Run migrations
        result = subprocess.run(
            ["alembic", "upgrade", "head"], 
            capture_output=True, 
            text=True,
            env={**os.environ, "DATABASE_URL": RENDER_DATABASE_URL}
        )
        
        if result.returncode == 0:
            print("✅ Migrations completed successfully!")
            print(result.stdout)
            return True
        else:
            print(f"❌ Migration failed!")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

def create_initial_data():
    """Create initial test data"""
    print("\n👥 Creating initial data...")
    
    try:
        # Temporarily set the DATABASE_URL for the script
        os.environ["DATABASE_URL"] = RENDER_DATABASE_URL
        
        from scripts.create_initial_data import create_initial_data
        create_initial_data()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating initial data: {e}")
        return False

def verify_setup():
    """Verify the database setup"""
    print("\n🔍 Verifying database setup...")
    
    try:
        engine = create_engine(RENDER_DATABASE_URL)
        with engine.connect() as conn:
            # Check tables exist
            tables_result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in tables_result]
            print(f"📊 Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
            
            # Check user count
            if 'users' in tables:
                user_count = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
                print(f"👥 Users in database: {user_count}")
            
            # Check tenant count
            if 'tenants' in tables:
                tenant_count = conn.execute(text("SELECT COUNT(*) FROM tenants")).fetchone()[0]
                print(f"🏢 Tenants in database: {tenant_count}")
            
            print("✅ Database verification completed!")
            return True
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 MSAFIRI - RENDER DATABASE SETUP")
    print("=" * 60)
    print(f"🎯 Target Database: Render PostgreSQL")
    print(f"🌐 Host: dpg-d29gte2li9vc73fncigg-a.oregon-postgres.render.com")
    print(f"💾 Database: msafiri_db")
    print("=" * 60)
    
    # Step 1: Test connection
    if not test_connection():
        print("\n❌ Setup failed. Check your database credentials.")
        return
    
    # Step 2: Run migrations
    if not run_migrations():
        print("\n❌ Migration failed. Check the errors above.")
        return
    
    # Step 3: Create initial data
    if not create_initial_data():
        print("\n⚠️  Initial data creation failed, but database is set up.")
        print("You can create test data manually later.")
    
    # Step 4: Verify setup
    verify_setup()
    
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("1. Start your API: uvicorn app.main:app --reload")
    print("2. Visit: http://localhost:8000/docs")
    print("3. Test login with these credentials:")
    print("   • Super Admin: superadmin@msafiri.org / admin123")
    print("   • MT Admin: mtadmin@msf-kenya.org / admin123")
    print("   • Staff: staff@msf-kenya.org / staff123")
    print("\n🌐 Your database is now hosted on Render!")

if __name__ == "__main__":
    main()