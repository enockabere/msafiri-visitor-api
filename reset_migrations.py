#!/usr/bin/env python3
"""
Nuclear reset of Alembic migrations
"""
import os
import shutil

def reset_migrations():
    """Remove all migration files and reset"""
    versions_dir = "alembic/versions"
    
    # Remove all migration files
    if os.path.exists(versions_dir):
        for file in os.listdir(versions_dir):
            if file.endswith('.py') and file != '__init__.py':
                os.remove(os.path.join(versions_dir, file))
                print(f"Removed {file}")
    
    print("All migration files removed. Run 'alembic revision --autogenerate -m \"initial\"' to create new base migration.")

if __name__ == "__main__":
    reset_migrations()