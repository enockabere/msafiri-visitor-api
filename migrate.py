#!/usr/bin/env python3
"""
Auto-migration script for Msafiri Visitor API
Runs Alembic migrations automatically
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run Alembic migration"""
    try:
        # Get the project root directory
        project_root = Path(__file__).parent
        
        logger.info("🔄 Starting database migration...")
        logger.info(f"📁 Project root: {project_root}")
        
        # Change to project directory
        os.chdir(project_root)
        
        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Migration completed successfully!")
            if result.stdout:
                logger.info(f"Output: {result.stdout}")
        else:
            logger.error(f"❌ Migration failed!")
            logger.error(f"Error: {result.stderr}")
            sys.exit(1)
            
    except FileNotFoundError:
        logger.error("❌ Alembic not found. Please install alembic: pip install alembic")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Migration error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()