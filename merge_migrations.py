#!/usr/bin/env python3
"""
Script to merge multiple migration heads
"""
import subprocess
import sys

def run_command(cmd):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("🔧 Merging migration heads...")
    
    # Create merge migration
    success, stdout, stderr = run_command("alembic merge heads -m 'merge_migration_heads'")
    
    if success:
        print("✅ Merge migration created successfully")
        print("📝 Output:", stdout)
        
        # Now upgrade to head
        print("🚀 Upgrading to head...")
        success2, stdout2, stderr2 = run_command("alembic upgrade head")
        
        if success2:
            print("✅ Database upgraded successfully")
            print("📝 Output:", stdout2)
        else:
            print("❌ Failed to upgrade database")
            print("📝 Error:", stderr2)
    else:
        print("❌ Failed to create merge migration")
        print("📝 Error:", stderr)

if __name__ == "__main__":
    main()