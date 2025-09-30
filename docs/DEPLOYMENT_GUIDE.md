# MSafiri Visitor API - Production Deployment Guide

## 🚀 **Overview**
This guide covers deploying the MSafiri Visitor API to production while maintaining development capabilities and data safety.

## 📋 **Pre-Deployment Checklist**

### 1. **Environment Configuration**
- [ ] Production environment variables configured
- [ ] Database connection strings updated
- [ ] SSL certificates configured
- [ ] Domain/subdomain configured
- [ ] CORS settings updated for production domains

### 2. **Database Preparation**
- [ ] Production database created
- [ ] Database migrations tested
- [ ] Backup strategy implemented
- [ ] Connection pooling configured

### 3. **Security Hardening**
- [ ] Debug mode disabled
- [ ] Secret keys rotated
- [ ] Rate limiting configured
- [ ] Input validation reviewed
- [ ] HTTPS enforced

## 🗂️ **Files to Clean Up for Production**

### **Development Scripts to Remove/Archive:**
```bash
# Create a dev-scripts directory for archival
mkdir dev-scripts

# Move development-only files
mv *.py dev-scripts/  # All root-level Python scripts
mv *.sql dev-scripts/ # All SQL files
mv *.bat dev-scripts/ # Windows batch files
mv *.sh dev-scripts/  # Shell scripts (except start.sh)
mv test_*.py dev-scripts/
mv check_*.py dev-scripts/
mv create_*.py dev-scripts/
mv fix_*.py dev-scripts/
mv add_*.py dev-scripts/
mv *.md dev-scripts/ # Documentation files (keep main README.md)

# Keep these essential files:
# - requirements.txt
# - gunicorn.conf.py
# - Procfile
# - alembic.ini
# - start.sh (if needed)
# - .env (production version)
# - .gitignore
# - README.md
```

### **Production-Ready File Structure:**
```
msafiri-visitor-api/
├── app/                    # Core application
├── alembic/               # Database migrations
├── uploads/               # File uploads (ensure proper permissions)
├── requirements.txt       # Python dependencies
├── gunicorn.conf.py      # WSGI server config
├── Procfile              # Process file for deployment
├── alembic.ini           # Alembic configuration
├── .env                  # Production environment variables
├── .gitignore           # Git ignore rules
├── README.md            # Production documentation
└── dev-scripts/         # Archived development scripts
```

## 🔧 **Production Environment Setup**

### **1. Environment Variables (.env)**
```bash
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
MAX_FILE_SIZE=10485760  # 10MB

# Email Configuration (if applicable)
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USER=your-email@domain.com
SMTP_PASSWORD=your-email-password

# Microsoft SSO Configuration
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# Redis Configuration (if using)
REDIS_URL=redis://your-redis-host:6379/0

# Monitoring & Logging
LOG_LEVEL=INFO
SENTRY_DSN=your-sentry-dsn  # Optional error tracking
```

### **2. Production Requirements**
Create `requirements-prod.txt`:
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
gunicorn==21.2.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
redis==5.0.1  # If using Redis
sentry-sdk[fastapi]==1.38.0  # Optional error tracking
```

## 🐳 **Docker Configuration**

### **Dockerfile**
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads && chmod 755 /app/uploads

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
```

### **docker-compose.yml**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/msafiri
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: msafiri
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
```

## 🗄️ **Database Migration Strategy**

### **Safe Migration Process:**
```bash
# 1. Backup current database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Test migrations on staging
alembic upgrade head --sql > migration_preview.sql
# Review the SQL before applying

# 3. Apply migrations with rollback plan
alembic upgrade head

# 4. Verify migration success
python -c "from app.db.database import engine; print('Database connection successful')"
```

### **Rollback Strategy:**
```bash
# If migration fails, rollback to previous version
alembic downgrade -1

# Or restore from backup
psql $DATABASE_URL < backup_YYYYMMDD_HHMMSS.sql
```

## 🔄 **Continuous Deployment Setup**

### **GitHub Actions Workflow (.github/workflows/deploy.yml):**
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        
    - name: Run tests
      run: |
        pytest tests/
        
    - name: Database backup
      run: |
        # Backup production database before deployment
        
    - name: Deploy to server
      run: |
        # Your deployment script here
        
    - name: Run migrations
      run: |
        alembic upgrade head
        
    - name: Health check
      run: |
        curl -f https://your-api-domain.com/health
```

## 📊 **Monitoring & Logging**

### **Health Check Endpoint:**
Add to `app/main.py`:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }
```

### **Logging Configuration:**
```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
```

## 🔒 **Security Checklist**

- [ ] HTTPS enforced (SSL/TLS certificates)
- [ ] Environment variables secured
- [ ] Database credentials rotated
- [ ] CORS properly configured
- [ ] Rate limiting implemented
- [ ] Input validation in place
- [ ] File upload restrictions
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF protection

## 🚀 **Deployment Platforms**

### **Recommended Platforms:**
1. **Railway** - Easy Python deployment
2. **Render** - Free tier available
3. **DigitalOcean App Platform** - Managed deployment
4. **AWS ECS/Fargate** - Enterprise scale
5. **Google Cloud Run** - Serverless option

### **Platform-Specific Configurations:**

#### **Railway:**
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn app.main:app -c gunicorn.conf.py",
    "healthcheckPath": "/health"
  }
}
```

#### **Render:**
```yaml
services:
  - type: web
    name: msafiri-api
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn app.main:app -c gunicorn.conf.py"
    healthCheckPath: "/health"
```

## 📈 **Performance Optimization**

### **Gunicorn Configuration (gunicorn.conf.py):**
```python
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
```

### **Database Optimization:**
- Connection pooling
- Query optimization
- Proper indexing
- Regular VACUUM and ANALYZE

## 🔄 **Maintenance Procedures**

### **Regular Tasks:**
1. **Database backups** (daily)
2. **Log rotation** (weekly)
3. **Security updates** (monthly)
4. **Performance monitoring** (continuous)
5. **Dependency updates** (monthly)

### **Emergency Procedures:**
1. **Rollback process**
2. **Database restoration**
3. **Service restart procedures**
4. **Incident response plan**

## 📞 **Support & Troubleshooting**

### **Common Issues:**
- Database connection failures
- Migration conflicts
- File upload issues
- CORS errors
- SSL certificate problems

### **Monitoring Tools:**
- Application logs
- Database performance metrics
- Server resource usage
- Error tracking (Sentry)
- Uptime monitoring

This deployment guide ensures a smooth transition to production while maintaining development agility and data safety.