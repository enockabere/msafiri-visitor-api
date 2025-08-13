# File: scripts/smart_migration.py
"""
Smart migration script that checks if migration is needed before running
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import subprocess
from sqlalchemy import create_engine, text
from app.core.config import settings

def check_if_migration_needed():
    """Check if migration is actually needed"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Check if key enhanced columns exist
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name = 'date_of_birth'
                )
            """))
            
            if result.scalar():
                print("✅ Enhanced columns already exist - skipping migration")
                return False
            else:
                print("📋 Enhanced columns missing - migration needed")
                return True
                
    except Exception as e:
        print(f"⚠️  Could not check database state: {e}")
        print("📋 Proceeding with migration...")
        return True

def run_migration():
    """Run the actual migration"""
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Migration completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e.stderr}")
        return False

def main():
    """Main migration logic"""
    print("🔍 Smart Migration Check")
    print("=" * 30)
    
    if check_if_migration_needed():
        print("🚀 Running migration...")
        if run_migration():
            print("✅ All migrations completed successfully!")
            return True
        else:
            print("❌ Migration failed!")
            return False
    else:
        print("✅ No migration needed - database is up to date!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)