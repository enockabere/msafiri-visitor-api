# File: app/main.py (CORS SECTION FIX)
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
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# FIXED CORS CONFIGURATION
allowed_origins = [
    "http://localhost:3000",  # Next.js dev server
    "http://localhost:3001",  # Alternative local port
    "http://127.0.0.1:3000",  # Alternative localhost
    "http://192.168.200.66:3000",  # Server IP Next.js
    "http://192.168.200.66:8000",  # Server IP API
    "http://192.168.200.66",  # Server IP without port
]

# In production, get allowed origins from environment
if settings.ENVIRONMENT == "production":
    frontend_urls = os.getenv("ALLOWED_ORIGINS", "").split(",")
    if frontend_urls and frontend_urls[0]:  # If environment variable exists
        allowed_origins = [url.strip() for url in frontend_urls if url.strip()]

# CRITICAL: Add CORS middleware BEFORE other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (includes mobile apps)
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=[
        "*",  # Allow all headers (includes mobile app headers)
        "X-Microsoft-Token",  # Specifically allow Microsoft SSO token header
        "Authorization",  # Allow auth headers
        "Content-Type",  # Allow content type headers
    ],
    expose_headers=["X-Process-Time"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Request logging middleware (AFTER CORS)
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    """Log all requests with timing and CORS details"""
    start_time = time.time()
    
    # Log request details with headers
    origin = request.headers.get("origin", "No Origin")
    user_agent = request.headers.get("user-agent", "No User-Agent")[:100]
    
    logger.info(f"🌐 {request.method} {request.url.path}")
    logger.info(f"   📍 Origin: {origin}")
    logger.info(f"   💻 Client: {request.client.host}")
    logger.info(f"   🤖 User-Agent: {user_agent}")
    
    # Log query parameters if any
    if request.query_params:
        logger.info(f"   🔍 Query: {dict(request.query_params)}")
    
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
        
        # Log CORS headers in response
        cors_headers = {
            k: v for k, v in response.headers.items() 
            if k.lower().startswith('access-control')
        }
        if cors_headers:
            logger.info(f"   🔗 CORS Headers: {cors_headers}")
        
        return response
        
    except Exception as e:
        # Log errors with full details
        process_time = time.time() - start_time
        logger.error(
            f"❌ {request.method} {request.url.path} - "
            f"Error: {str(e)} - "
            f"Time: {process_time:.4f}s"
        )
        logger.exception("Full error traceback:")
        
        # Return proper error response with CORS headers
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(e),
                "path": request.url.path,
                "method": request.method
            },
            headers={
                "Access-Control-Allow-Origin": origin if origin in allowed_origins else "*",
                "Access-Control-Allow-Credentials": "true"
            }
        )

# Test CORS endpoint (for debugging)
@app.get("/test-cors")
def test_cors():
    """Test endpoint to verify CORS is working"""
    return {
        "message": "CORS is working!",
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT
    }

# Database connection test on startup
@app.on_event("startup")
async def startup_event():
    """Test database connection on startup"""
    logger.info("🚀 Starting Msafiri Visitor System")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"📡 API V1 prefix: {settings.API_V1_STR}")
    logger.info(f"💾 Database URL: {settings.DATABASE_URL[:50]}...")
    logger.info(f"🔗 Allowed CORS origins: {allowed_origins}")
    
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
        "docs_url": "/docs",
        "status": "running",
        "cors_origins": allowed_origins
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
            "timestamp": time.time(),
            "cors_configured": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "environment": settings.ENVIRONMENT,
            "database": f"error: {str(e)}",
            "timestamp": time.time(),
            "cors_configured": True
        }

# Error handlers
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
    logger.info(f"🔗 CORS configured for: {allowed_origins}")
    uvicorn.run(
        app, 
        host=host, 
        port=port,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.ENVIRONMENT == "development"
    )