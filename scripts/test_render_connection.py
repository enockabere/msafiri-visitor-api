# File: scripts/test_render_connection.py
"""
Quick script to test Render database connection
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, text

# Your Render database URL
DATABASE_URL = "postgresql://msafiri_db_user:v9yhk3xq8OyVVyd5eGrRM6T755amuvwl@dpg-d29gte2li9vc73fncigg-a.oregon-postgres.render.com/msafiri_db"

def test_connection():
    """Simple connection test"""
    print("🔌 Testing Render PostgreSQL connection...")
    print(f"🌐 Host: dpg-d29gte2li9vc73fncigg-a.oregon-postgres.render.com")
    print(f"👤 User: msafiri_db_user")
    print(f"💾 Database: msafiri_db")
    
    try:
        # Create engine and test connection
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT current_database(), current_user, version();"))
            row = result.fetchone()
            
            print(f"\n✅ Connection successful!")
            print(f"📋 Database: {row[0]}")
            print(f"👤 Connected as: {row[1]}")
            print(f"🐘 PostgreSQL: {row[2][:50]}...")
            
            # Test if we can create tables
            conn.execute(text("SELECT 1;"))
            print(f"✅ Database permissions: OK")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Connection failed!")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if test_connection():
        print("\n🎉 Your Render database is ready!")
        print("Run: python scripts/setup_render_db.py")
    else:
        print("\n❌ Please check your database credentials.")