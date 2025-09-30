#!/usr/bin/env python3
"""
Production Preparation Script for MSafiri Visitor API
This script helps prepare the API for production deployment by organizing development files.
"""

import os
import shutil
import glob
from pathlib import Path

def create_dev_scripts_directory():
    """Create dev-scripts directory for archiving development files."""
    dev_scripts_dir = Path("dev-scripts")
    dev_scripts_dir.mkdir(exist_ok=True)
    print(f"✅ Created {dev_scripts_dir} directory")
    return dev_scripts_dir

def move_development_files(dev_scripts_dir):
    """Move development-specific files to dev-scripts directory."""
    
    # Files to move (development scripts and utilities)
    files_to_move = [
        # Python scripts (except essential ones)
        "add_*.py",
        "check_*.py", 
        "create_*.py",
        "fix_*.py",
        "test_*.py",
        "run_*.py",
        "delete_*.py",
        "update_*.py",
        "migrate_*.py",
        "assign_*.py",
        "restore_*.py",
        "reset_*.py",
        "cleanup_*.py",
        "print_*.py",
        "verify_*.py",
        
        # SQL files
        "*.sql",
        
        # Batch and shell scripts (except essential ones)
        "*.bat",
        "run_*.sh",
        
        # Documentation files (except main ones)
        "*_SUMMARY.md",
        "*_FIXES.md", 
        "RELATIONSHIP_FIXES.md",
        "VENDOR_ACCOMMODATIONS_FIX_SUMMARY.md",
        "TRANSPORT_MANAGEMENT_SYSTEM.md",
        "SUPER_ADMIN_FEATURES.md",
        "FINAL_SETUP_STEPS.md",
        "SETUP_COMPLETE.md",
        
        # Other development files
        "invoice.html",
        "backup_*.sql",
    ]
    
    # Essential files to keep in root
    essential_files = {
        "requirements.txt",
        "requirements_clean.txt", 
        "gunicorn.conf.py",
        "Procfile",
        "alembic.ini",
        "start.sh",
        ".env",
        ".gitignore",
        ".dockerignore",
        "README.md",
        "build.sh",
        "DEPLOYMENT_GUIDE.md",
        "prepare_for_production.py"
    }
    
    moved_files = []
    
    for pattern in files_to_move:
        for file_path in glob.glob(pattern):
            file_name = os.path.basename(file_path)
            
            # Skip if it's an essential file
            if file_name in essential_files:
                continue
                
            # Skip if it's a directory
            if os.path.isdir(file_path):
                continue
                
            try:
                destination = dev_scripts_dir / file_name
                shutil.move(file_path, destination)
                moved_files.append(file_name)
                print(f"📦 Moved {file_name} to dev-scripts/")
            except Exception as e:
                print(f"❌ Error moving {file_name}: {e}")
    
    return moved_files

def create_production_readme():
    """Create a production-focused README."""
    readme_content = """# MSafiri Visitor API - Production

## 🚀 Quick Start

### Environment Setup
1. Copy `.env.example` to `.env`
2. Configure production environment variables
3. Set up production database

### Database Setup
```bash
# Run migrations
alembic upgrade head
```

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Start the application
gunicorn app.main:app -c gunicorn.conf.py
```

### Health Check
```bash
curl https://your-api-domain.com/health
```

## 📚 Documentation
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Complete production deployment guide
- [API Documentation](https://your-api-domain.com/docs) - Interactive API docs

## 🔧 Development Files
Development scripts and utilities have been moved to `dev-scripts/` directory.

## 📞 Support
For production issues, check the deployment guide or contact the development team.
"""
    
    with open("README_PRODUCTION.md", "w") as f:
        f.write(readme_content)
    print("📝 Created README_PRODUCTION.md")

def create_production_env_example():
    """Create production environment example."""
    env_example = """# Production Environment Configuration

# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/database
POSTGRES_USER=production_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=msafiri_prod
POSTGRES_HOST=your-db-host.com
POSTGRES_PORT=5432

# Application Settings
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-super-secure-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256

# CORS Settings
ALLOWED_ORIGINS=["https://your-frontend-domain.com", "https://admin.your-domain.com"]
ALLOWED_HOSTS=["your-api-domain.com", "api.your-domain.com"]

# File Upload Settings
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=10485760

# Microsoft SSO Configuration
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# Optional: Monitoring
LOG_LEVEL=INFO
SENTRY_DSN=your-sentry-dsn
"""
    
    with open(".env.production.example", "w") as f:
        f.write(env_example)
    print("📝 Created .env.production.example")

def update_gitignore():
    """Update .gitignore for production."""
    gitignore_additions = """
# Development scripts (archived)
dev-scripts/

# Production environment files
.env.production
.env.staging

# Deployment artifacts
*.tar.gz
*.zip
deployment/

# Logs
*.log
logs/

# Backups
backups/
*.sql.backup
"""
    
    try:
        with open(".gitignore", "a") as f:
            f.write(gitignore_additions)
        print("📝 Updated .gitignore")
    except Exception as e:
        print(f"❌ Error updating .gitignore: {e}")

def main():
    """Main function to prepare the API for production."""
    print("🚀 Preparing MSafiri Visitor API for Production Deployment")
    print("=" * 60)
    
    # Create dev-scripts directory
    dev_scripts_dir = create_dev_scripts_directory()
    
    # Move development files
    moved_files = move_development_files(dev_scripts_dir)
    
    # Create production documentation
    create_production_readme()
    create_production_env_example()
    
    # Update .gitignore
    update_gitignore()
    
    print("\n" + "=" * 60)
    print("✅ Production preparation completed!")
    print(f"📦 Moved {len(moved_files)} development files to dev-scripts/")
    print("\n📋 Next Steps:")
    print("1. Review DEPLOYMENT_GUIDE.md for complete deployment instructions")
    print("2. Configure production environment variables")
    print("3. Set up production database")
    print("4. Test the deployment in staging environment")
    print("5. Deploy to production")
    
    print("\n🔧 Essential Files Kept in Root:")
    essential_files = [
        "app/", "alembic/", "uploads/", "requirements.txt", 
        "gunicorn.conf.py", "Procfile", "alembic.ini", 
        ".env", ".gitignore", "DEPLOYMENT_GUIDE.md"
    ]
    for file in essential_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
    
    print(f"\n📁 Development files archived in: {dev_scripts_dir}/")

if __name__ == "__main__":
    main()