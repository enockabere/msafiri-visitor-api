#!/usr/bin/env python3
"""
Script to run the chat messages cascade delete migration
"""
import subprocess
import sys
import os

def run_migration():
    """Run the alembic migration to fix chat messages cascade delete"""
    try:
        # Change to the API directory
        api_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(api_dir)
        
        print("🔄 Running chat messages cascade delete migration...")
        
        # Run the migration
        result = subprocess.run([
            sys.executable, "-m", "alembic", "upgrade", "fix_chat_messages_cascade_delete"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migration completed successfully!")
            print(result.stdout)
        else:
            print("❌ Migration failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error running migration: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)