# MSafiri API - Server Deployment Guide (IP Address)

## 🎯 **Overview**
This guide covers deploying the MSafiri API on a server using only an IP address (no domain).

## 📋 **Prerequisites**
- ✅ Server with Python installed
- ✅ PostgreSQL installed and running
- ✅ Database created
- ✅ Project pulled from GitHub

## 🚀 **Step-by-Step Deployment**

### **Step 1: Install Python Dependencies**
```bash
# Navigate to project directory
cd /path/to/msafiri-visitor-api

# Install pip if not available
sudo apt update
sudo apt install python3-pip python3-venv -y

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### **Step 2: Configure Environment Variables**
```bash
# Create environment file
cp .env.example .env

# Edit environment file
nano .env
```

**Configure `.env` file:**
```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=your_database_name
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Application Settings
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-super-secure-secret-key-change-this
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256

# Server Configuration
HOST=0.0.0.0
PORT=8000

# CORS Settings (replace with your server IP)
ALLOWED_ORIGINS=["http://YOUR_SERVER_IP:3000", "http://YOUR_SERVER_IP:8000"]
ALLOWED_HOSTS=["YOUR_SERVER_IP", "localhost", "127.0.0.1"]

# Microsoft SSO Configuration
AZURE_CLIENT_ID=ee68d31d-bf74-48ef-bbdf-51e0a5d1f65d
AZURE_CLIENT_SECRET=your-azure-client-secret
AZURE_TENANT_ID=4d9dd1af-83ce-4e9b-b090-b0543ccc2b31

# File Upload Settings
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=10485760
```

### **Step 3: Set Up Database**
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user (if not done)
CREATE DATABASE msafiri_db;
CREATE USER msafiri_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE msafiri_db TO msafiri_user;
\q

# Test database connection
python3 -c "
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
print('Database connection successful!')
"
```

### **Step 4: Run Database Migrations**
```bash
# Ensure you're in the project directory and venv is activated
source venv/bin/activate

# Run migrations
alembic upgrade head

# Verify tables were created
python3 -c "
from app.db.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f'Created {len(tables)} tables: {tables[:5]}...')
"
```

### **Step 5: Create Initial Admin User**
```bash
# Create a simple script to add admin user
cat > create_admin.py << 'EOF'
import asyncio
from sqlalchemy.orm import sessionmaker
from app.db.database import engine
from app.models.user import User, UserRole, UserStatus
from app.core.security import get_password_hash

def create_admin():
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.email == "admin@msf.org").first()
        if admin:
            print("Admin user already exists")
            return
        
        # Create admin user
        admin_user = User(
            email="admin@msf.org",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            is_active=True,
            tenant_id="msf-global"
        )
        
        db.add(admin_user)
        db.commit()
        print("Admin user created successfully!")
        print("Email: admin@msf.org")
        print("Password: admin123")
        print("Please change the password after first login!")
        
    except Exception as e:
        print(f"Error creating admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
EOF

# Run the script
python3 create_admin.py
```

### **Step 6: Test the Application**
```bash
# Test run the application
python3 -c "
from app.main import app
print('Application imports successfully!')
"

# Start the server for testing
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Test endpoints:**
- Health check: `http://YOUR_SERVER_IP:8000/health`
- API docs: `http://YOUR_SERVER_IP:8000/docs`
- Login test: `http://YOUR_SERVER_IP:8000/api/v1/auth/login`

### **Step 7: Set Up Production Server**
```bash
# Stop test server (Ctrl+C)

# Install production server
pip install gunicorn

# Create gunicorn configuration if not exists
cat > gunicorn.conf.py << 'EOF'
bind = "0.0.0.0:8000"
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
timeout = 30
keepalive = 2
preload_app = True
EOF

# Start production server
gunicorn app.main:app -c gunicorn.conf.py
```

### **Step 8: Set Up as System Service (Optional)**
```bash
# Create systemd service file
sudo tee /etc/systemd/system/msafiri-api.service > /dev/null << EOF
[Unit]
Description=MSafiri API
After=network.target

[Service]
Type=exec
User=$USER
WorkingDirectory=/path/to/msafiri-visitor-api
Environment=PATH=/path/to/msafiri-visitor-api/venv/bin
ExecStart=/path/to/msafiri-visitor-api/venv/bin/gunicorn app.main:app -c gunicorn.conf.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable msafiri-api
sudo systemctl start msafiri-api

# Check status
sudo systemctl status msafiri-api
```

## 🔧 **Firewall Configuration**
```bash
# Allow port 8000 through firewall
sudo ufw allow 8000
sudo ufw status
```

## 🧪 **Testing the Deployment**

### **1. Health Check**
```bash
curl http://YOUR_SERVER_IP:8000/health
```

### **2. API Documentation**
Open in browser: `http://YOUR_SERVER_IP:8000/docs`

### **3. Login Test**
```bash
curl -X POST "http://YOUR_SERVER_IP:8000/api/v1/auth/login/tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@msf.org",
    "password": "admin123"
  }'
```

## 🔍 **Troubleshooting**

### **Common Issues:**

#### **Database Connection Error**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check database exists
sudo -u postgres psql -l | grep msafiri

# Test connection
python3 -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://user:pass@localhost/db')
print('Connection successful!')
"
```

#### **Port Already in Use**
```bash
# Check what's using port 8000
sudo netstat -tlnp | grep :8000

# Kill process if needed
sudo kill -9 PID_NUMBER
```

#### **Permission Errors**
```bash
# Fix file permissions
chmod +x start.sh
chown -R $USER:$USER /path/to/msafiri-visitor-api
```

#### **Module Import Errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📊 **Monitoring**

### **Check Logs**
```bash
# If using systemd service
sudo journalctl -u msafiri-api -f

# If running manually
tail -f /var/log/msafiri-api.log
```

### **Check Process**
```bash
# Check if API is running
ps aux | grep gunicorn

# Check port usage
sudo netstat -tlnp | grep :8000
```

## 🔄 **Updates and Maintenance**

### **Updating the Application**
```bash
# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install any new dependencies
pip install -r requirements.txt

# Run new migrations
alembic upgrade head

# Restart service
sudo systemctl restart msafiri-api
```

### **Database Backup**
```bash
# Create backup
pg_dump -U msafiri_user -h localhost msafiri_db > backup_$(date +%Y%m%d).sql

# Restore backup (if needed)
psql -U msafiri_user -h localhost msafiri_db < backup_YYYYMMDD.sql
```

## 📞 **Quick Reference**

### **Important URLs**
- API Base: `http://YOUR_SERVER_IP:8000`
- Health Check: `http://YOUR_SERVER_IP:8000/health`
- API Docs: `http://YOUR_SERVER_IP:8000/docs`
- Admin Login: Email: `admin@msf.org`, Password: `admin123`

### **Important Commands**
```bash
# Start API
source venv/bin/activate && gunicorn app.main:app -c gunicorn.conf.py

# Check status
curl http://YOUR_SERVER_IP:8000/health

# View logs
sudo journalctl -u msafiri-api -f

# Restart service
sudo systemctl restart msafiri-api
```

Replace `YOUR_SERVER_IP` with your actual server IP address throughout this guide.