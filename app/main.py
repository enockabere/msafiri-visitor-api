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

def create_default_roles():
    """Create default system roles for all tenants"""
    try:
        logger.info("🔧 Creating default system roles...")
        
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Get all tenants
            tenants_result = conn.execute(text("SELECT slug FROM tenants"))
            tenants = [row[0] for row in tenants_result.fetchall()]
            
            # Default roles to create
            default_roles = [
                {"name": "Admin", "description": "Full administrative access to tenant resources"},
                {"name": "Event Manager", "description": "Can create and manage events"},
                {"name": "User Manager", "description": "Can manage users and their roles"},
                {"name": "Viewer", "description": "Read-only access to tenant resources"},
                {"name": "Facilitator", "description": "Can facilitate events and manage participants"}
            ]
            
            for tenant_id in tenants:
                for role_data in default_roles:
                    # Check if role already exists
                    check_sql = "SELECT id FROM roles WHERE name = :name AND tenant_id = :tenant_id"
                    existing = conn.execute(text(check_sql), {
                        "name": role_data["name"],
                        "tenant_id": tenant_id
                    }).fetchone()
                    
                    if not existing:
                        # Create the role
                        insert_sql = """
                        INSERT INTO roles (name, description, tenant_id, is_active, created_by, created_at)
                        VALUES (:name, :description, :tenant_id, true, 'system', CURRENT_TIMESTAMP)
                        """
                        conn.execute(text(insert_sql), {
                            "name": role_data["name"],
                            "description": role_data["description"],
                            "tenant_id": tenant_id
                        })
                        logger.info(f"✅ Created role '{role_data['name']}' for tenant '{tenant_id}'")
            
            conn.commit()
            logger.info("✅ Default roles creation completed")
            
    except Exception as e:
        logger.error(f"❌ Error creating default roles: {str(e)}")
        # Don't fail startup if role creation fails

# Auto-migration function
def run_auto_migration():
    """Run database migrations automatically on startup"""
    try:
        logger.info("🔄 Running auto-migration...")
        
        # Try direct SQL migration first (safer)
        try:
            # Run direct SQL migration
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                trans = conn.begin()
                try:
                    # Add columns to users table
                    user_columns = [
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(100)",
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS position VARCHAR(255)",
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS project VARCHAR(255)",
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(500)"
                    ]
                    for sql in user_columns:
                        conn.execute(text(sql))
                    
                    # Add columns to event_participants table
                    participant_columns = [
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS country VARCHAR(100)",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS position VARCHAR(255)",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS project VARCHAR(255)",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS gender VARCHAR(50)",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS eta VARCHAR(255)",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS requires_eta BOOLEAN DEFAULT FALSE",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS passport_document VARCHAR(500)",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS ticket_document VARCHAR(500)"
                    ]
                    for sql in participant_columns:
                        conn.execute(text(sql))
                    
                    # Add columns to events table
                    event_columns = [
                        "ALTER TABLE events ADD COLUMN IF NOT EXISTS country VARCHAR(100)",
                        "ALTER TABLE events ADD COLUMN IF NOT EXISTS registration_deadline DATE"
                    ]
                    for sql in event_columns:
                        conn.execute(text(sql))
                    
                    # Add columns to tenants table
                    tenant_columns = [
                        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS country VARCHAR(100)"
                    ]
                    for sql in tenant_columns:
                        conn.execute(text(sql))
                    
                    # Create inventory table
                    create_inventory_table = """
                    CREATE TABLE IF NOT EXISTS inventory (
                        id SERIAL PRIMARY KEY,
                        tenant_id VARCHAR NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        category VARCHAR(100),
                        quantity INTEGER DEFAULT 0,
                        condition VARCHAR(50) DEFAULT 'good',
                        is_active BOOLEAN DEFAULT TRUE,
                        created_by VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_inventory_table))
                    
                    # Create event_agenda table
                    create_agenda_table = """
                    CREATE TABLE IF NOT EXISTS event_agenda (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                        day_number INTEGER NOT NULL,
                        event_date DATE NOT NULL,
                        time VARCHAR(10) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        created_by VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_agenda_table))
                    
                    # Create roles table
                    create_roles_table = """
                    CREATE TABLE IF NOT EXISTS roles (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        description TEXT,
                        tenant_id VARCHAR NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_by VARCHAR(255),
                        updated_by VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_roles_table))
                    
                    # Create event_feedback table
                    create_feedback_table = """
                    CREATE TABLE IF NOT EXISTS event_feedback (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                        participant_id INTEGER REFERENCES event_participants(id) ON DELETE SET NULL,
                        participant_email VARCHAR(255) NOT NULL,
                        participant_name VARCHAR(255) NOT NULL,
                        overall_rating INTEGER CHECK (overall_rating >= 1 AND overall_rating <= 5),
                        content_rating INTEGER CHECK (content_rating >= 1 AND content_rating <= 5),
                        organization_rating INTEGER CHECK (organization_rating >= 1 AND organization_rating <= 5),
                        venue_rating INTEGER CHECK (venue_rating >= 1 AND venue_rating <= 5),
                        feedback_text TEXT,
                        suggestions TEXT,
                        would_recommend BOOLEAN,
                        submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        ip_address VARCHAR(45),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_feedback_table))
                    
                    # Add registration form fields to events table
                    registration_form_columns = [
                        "ALTER TABLE events ADD COLUMN IF NOT EXISTS registration_form_title VARCHAR(500)",
                        "ALTER TABLE events ADD COLUMN IF NOT EXISTS registration_form_description TEXT"
                    ]
                    for sql in registration_form_columns:
                        conn.execute(text(sql))
                    
                    # Create public_registrations table for detailed form data
                    create_public_registrations_table = """
                    CREATE TABLE IF NOT EXISTS public_registrations (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                        participant_id INTEGER REFERENCES event_participants(id) ON DELETE CASCADE,
                        first_name VARCHAR(255) NOT NULL,
                        last_name VARCHAR(255) NOT NULL,
                        oc VARCHAR(50) NOT NULL,
                        contract_status VARCHAR(100) NOT NULL,
                        contract_type VARCHAR(50) NOT NULL,
                        gender_identity VARCHAR(100) NOT NULL,
                        sex VARCHAR(50) NOT NULL,
                        pronouns VARCHAR(50) NOT NULL,
                        current_position VARCHAR(255) NOT NULL,
                        country_of_work VARCHAR(255),
                        project_of_work VARCHAR(255),
                        personal_email VARCHAR(255) NOT NULL,
                        msf_email VARCHAR(255) NOT NULL,
                        hrco_email VARCHAR(255),
                        career_manager_email VARCHAR(255),
                        ld_manager_email VARCHAR(255),
                        line_manager_email VARCHAR(255),
                        phone_number VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_public_registrations_table))
                    
                    # Create indexes
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_roles_tenant_id ON roles(tenant_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_inventory_tenant_id ON inventory(tenant_id)
                    """))
                    
                    # Add unique constraints (with error handling)
                    unique_constraints = [
                        ("users", "users_email_unique", "ALTER TABLE users ADD CONSTRAINT users_email_unique UNIQUE (email)"),
                        ("events", "events_title_unique", "ALTER TABLE events ADD CONSTRAINT events_title_unique UNIQUE (title)")
                    ]
                    
                    for table_name, constraint_name, sql in unique_constraints:
                        try:
                            check_sql = f"SELECT 1 FROM information_schema.table_constraints WHERE table_name = '{table_name}' AND constraint_name = '{constraint_name}'"
                            result = conn.execute(text(check_sql)).fetchone()
                            
                            if not result:
                                conn.execute(text(sql))
                        except Exception:
                            pass  # Constraint might already exist
                    
                    trans.commit()
                    logger.info("✅ Direct migration completed successfully")
                    
                    # Create default roles after successful migration
                    create_default_roles()
                    return
                except Exception as e:
                    trans.rollback()
                    raise e
        except Exception as e:
            logger.error(f"Direct migration failed: {str(e)}, trying alembic...")
        
        # Fallback to alembic
        import subprocess
        import sys
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent
        
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        if result.returncode == 0:
            logger.info("✅ Alembic migration completed successfully")
            if result.stdout:
                logger.info(f"Migration output: {result.stdout}")
            # Create default roles after successful alembic migration
            create_default_roles()
        else:
            logger.error(f"❌ Alembic migration failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"❌ Auto-migration error: {str(e)}")
        # Don't fail startup if migration fails

# Database connection test on startup
@app.on_event("startup")
async def startup_event():
    """Test database connection and run migrations on startup"""
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
        
        # Run auto-migration in production
        if settings.ENVIRONMENT == "production":
            run_auto_migration()
        
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