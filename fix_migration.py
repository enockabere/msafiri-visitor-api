#!/usr/bin/env python3
"""
Script to fix migration state when table already exists
"""
import subprocess
import sys

def run_command(cmd):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=".")
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("Fixing migration state...")
    
    # Mark the emergency_contacts migration as applied without running it
    success, stdout, stderr = run_command("alembic stamp emergency_contacts_001")
    
    if success:
        print("SUCCESS: Successfully marked emergency_contacts migration as applied")
        print("Now try running: alembic upgrade head")
    else:
        print("FAILED: Failed to stamp migration:")
        print(f"Error: {stderr}")
        
        # Alternative: Try to stamp head first
        print("\nTrying alternative approach...")
        success2, stdout2, stderr2 = run_command("alembic stamp head")
        if success2:
            print("SUCCESS: Successfully stamped head")
        else:
            print(f"FAILED: {stderr2}")

if __name__ == "__main__":
    main()