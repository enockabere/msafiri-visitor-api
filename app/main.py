# File: app/main.py (FINAL FIXED VERSION)
import os
import time
import logging
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from app.api.v1.api import api_router
from app.core.config import settings

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENVIRONMENT == "development" else None,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

# CORS middleware - Updated for production
allowed_origins = [
    "http://localhost:3000",  # Local development
    "http://localhost:3001",  # Alternative local port
    "https://your-nextjs-app.vercel.app",  # Your deployed Next.js app
    "https://msafiri-admin.vercel.app",  # Example production URL
]

# In production, get allowed origins from environment
if settings.ENVIRONMENT == "production":
    frontend_urls = os.getenv("ALLOWED_ORIGINS", "").split(",")
    if frontend_urls and frontend_urls[0]:  # If environment variable exists
        allowed_origins = [url.strip() for url in frontend_urls if url.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Request logging middleware (FIXED)
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    """Log all requests with timing"""
    start_time = time.time()  # FIXED: Use time.time() instead of logging.time()
    
    # Log request details
    logger.info(f"🌐 {request.method} {request.url.path} - Client: {request.client.host}")
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response details
        logger.info(
            f"✅ {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s"
        )
        
        # Add processing time to response headers
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        # Log errors
        process_time = time.time() - start_time
        logger.error(
            f"❌ {request.method} {request.url.path} - "
            f"Error: {str(e)} - "
            f"Time: {process_time:.4f}s"
        )
        raise

# Database connection test on startup (FIXED - use lifespan instead of deprecated on_event)
@app.on_event("startup")
async def startup_event():
    """Test database connection on startup"""
    logger.info("🚀 Starting Msafiri Visitor System")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"📡 API V1 prefix: {settings.API_V1_STR}")
    logger.info(f"💾 Database URL: {settings.DATABASE_URL[:50]}...")
    
    try:
        # Test database connection
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version_info = result.fetchone()[0]
            logger.info(f"✅ Database connected: {version_info[:50]}...")
        
        logger.info("🎉 Application startup completed!")
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        # Don't exit in production - let the app start anyway
        if settings.ENVIRONMENT != "production":
            raise

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Basic routes
@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.ENVIRONMENT == "development" else "disabled",
        "status": "running"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        # Quick database check
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "database": "connected",
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "environment": settings.ENVIRONMENT,
            "database": f"error: {str(e)}",
            "timestamp": time.time()
        }

@app.get("/api/status")
def api_status():
    """Detailed API status for monitoring"""
    return {
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "log_level": settings.LOG_LEVEL,
        "database_connected": True,
        "endpoints": {
            "auth": f"{settings.API_V1_STR}/auth",
            "users": f"{settings.API_V1_STR}/users",
            "tenants": f"{settings.API_V1_STR}/tenants",
            "notifications": f"{settings.API_V1_STR}/notifications"
        }
    }

# Error handlers (FIXED - return JSONResponse instead of dict)
@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "Something went wrong on our end",
            "status_code": 500
        }
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not found", 
            "message": f"The requested resource {request.url.path} was not found",
            "status_code": 404
        }
    )

# For local development and Render deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0" if settings.ENVIRONMENT == "production" else "127.0.0.1"
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    uvicorn.run(
        app, 
        host=host, 
        port=port,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.ENVIRONMENT == "development"
    )