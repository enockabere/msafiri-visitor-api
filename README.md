# MSafiri Visitor API

## 🚀 Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Configure .env file

# Run database migrations
alembic upgrade head

# Start production server
gunicorn app.main:app -c gunicorn.conf.py
```

## 📚 Documentation
- [Server Deployment Guide](docs/SERVER_DEPLOYMENT.md) - Deploy on server with IP address
- [Production Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Complete production setup

## 🔧 API Endpoints
- **Health Check**: `GET /health`
- **API Documentation**: `GET /docs` (Swagger UI)
- **API Schema**: `GET /redoc` (ReDoc)

## 🗄️ Database
- PostgreSQL database required
- Migrations managed with Alembic
- Run `alembic upgrade head` to apply migrations

## 📞 Support
For deployment issues, check the documentation in the `docs/` directory.