# File: app/main.py (CORS SECTION FIX)
import os
import time
import logging
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from app.api.v1.api import api_router
from app.core.config import settings

# Configure logging - Set to INFO to see debug messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS CONFIGURATION
allowed_origins = []

# Get allowed origins from environment variable
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [url.strip() for url in allowed_origins_env.split(",") if url.strip()]
else:
    # Fallback for development only
    if settings.ENVIRONMENT == "development":
        allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

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

# Request logging middleware (AFTER CORS) - MINIMAL LOGGING
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    """Log requests with minimal output"""
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # Only log server errors (500+)
        if response.status_code >= 500:
            logger.error(f"SERVER ERROR: {request.method} {request.url.path} - Status: {response.status_code}")

        return response
        
    except Exception as e:
        logger.error(f"REQUEST ERROR: {request.method} {request.url.path} - Error: {str(e)}")
        
        if "ValidationError" in str(type(e)) or "validation" in str(e).lower():
            return JSONResponse(
                status_code=422,
                content={"error": "Validation error", "message": str(e), "detail": str(e)},
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "message": str(e)},
            headers={"Access-Control-Allow-Origin": "*"}
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

@app.get("/test-connection")
def test_connection():
    """Test endpoint to verify API connectivity"""
    return {
        "message": "API connection is working!",
        "timestamp": time.time(),
        "host": "localhost:8000",
        "environment": settings.ENVIRONMENT
    }

def create_default_roles():
    """Create default system roles for all tenants"""
    try:
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
                {"name": "Facilitator", "description": "Can facilitate events and manage participants"},
                {"name": "Organizer", "description": "Can organize and coordinate events"},
                {"name": "Visitor", "description": "Default role for event participants"}
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
            
            conn.commit()
            
    except Exception as e:
        # Don't fail startup if role creation fails
        pass

# Auto-migration function
def run_auto_migration():
    """Run database migrations automatically on startup"""
    try:
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
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS ticket_document VARCHAR(500)",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS participant_role VARCHAR(50) DEFAULT 'visitor'",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS accommodation_type VARCHAR(100)",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS participant_name VARCHAR(255)",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS participant_email VARCHAR(255)"
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
                        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS country VARCHAR(100)",
                        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS timezone VARCHAR(50)"
                    ]
                    for sql in tenant_columns:
                        conn.execute(text(sql))
                    
                    # Auto-set timezones for existing tenants based on country
                    from app.utils.timezone_utils import get_timezone_for_country
                    
                    # Get all tenants with country but no timezone
                    result = conn.execute(text("""
                        SELECT id, slug, country 
                        FROM tenants 
                        WHERE country IS NOT NULL 
                        AND (timezone IS NULL OR timezone = '')
                    """))
                    
                    tenants_to_update = result.fetchall()
                    updated_count = 0
                    
                    for tenant in tenants_to_update:
                        timezone = get_timezone_for_country(tenant.country)
                        if timezone:
                            conn.execute(text("""
                                UPDATE tenants 
                                SET timezone = :timezone 
                                WHERE id = :tenant_id
                            """), {"timezone": timezone, "tenant_id": tenant.id})
                            updated_count += 1
                    
                    # Create inventory table
                    create_inventory_table = """
                    CREATE TABLE IF NOT EXISTS inventory (
                        id SERIAL PRIMARY KEY,
                        tenant_id INTEGER NOT NULL,
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
                    
                    # Fix tenant_id data type if table exists
                    try:
                        conn.execute(text("ALTER TABLE inventory ALTER COLUMN tenant_id TYPE INTEGER USING tenant_id::INTEGER"))
                    except Exception:
                        pass  # Column might already be correct type
                    
                    # Create event_allocations table
                    create_event_allocations_table = """
                    CREATE TABLE IF NOT EXISTS event_allocations (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                        inventory_item_id INTEGER REFERENCES inventory(id) ON DELETE SET NULL,
                        quantity_per_participant INTEGER DEFAULT 0,
                        drink_vouchers_per_participant INTEGER DEFAULT 0,
                        status VARCHAR(50) DEFAULT 'pending',
                        notes TEXT,
                        tenant_id INTEGER NOT NULL,
                        created_by VARCHAR(255),
                        approved_by VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        approved_at TIMESTAMP WITH TIME ZONE
                    )
                    """
                    conn.execute(text(create_event_allocations_table))
                    
                    # Fix tenant_id data type if table exists
                    try:
                        conn.execute(text("ALTER TABLE event_allocations ALTER COLUMN tenant_id TYPE INTEGER USING tenant_id::INTEGER"))
                    except Exception:
                        pass  # Column might already be correct type
                    
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
                        start_datetime TIMESTAMP WITH TIME ZONE,
                        end_datetime TIMESTAMP WITH TIME ZONE,
                        speaker VARCHAR(255),
                        session_number VARCHAR(50),
                        created_by VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """

                    
                    # Add new columns to existing event_agenda table
                    agenda_columns = [
                        "ALTER TABLE event_agenda ADD COLUMN IF NOT EXISTS start_datetime TIMESTAMP WITH TIME ZONE",
                        "ALTER TABLE event_agenda ADD COLUMN IF NOT EXISTS end_datetime TIMESTAMP WITH TIME ZONE",
                        "ALTER TABLE event_agenda ADD COLUMN IF NOT EXISTS speaker VARCHAR(255)",
                        "ALTER TABLE event_agenda ADD COLUMN IF NOT EXISTS session_number VARCHAR(50)"
                    ]
                    for sql in agenda_columns:
                        conn.execute(text(sql))
                    
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
                    
                    # Create event_attachments table
                    create_attachments_table = """
                    CREATE TABLE IF NOT EXISTS event_attachments (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                        name VARCHAR(255) NOT NULL,
                        url VARCHAR(500) NOT NULL,
                        uploaded_by VARCHAR(255) NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_attachments_table))
                    
                    # Create event_attachments table
                    create_attachments_table = """
                    CREATE TABLE IF NOT EXISTS event_attachments (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                        name VARCHAR(255) NOT NULL,
                        url VARCHAR(500) NOT NULL,
                        uploaded_by VARCHAR(255) NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_attachments_table))
                    
                    # Create event_feedback table (enhanced)
                    create_feedback_table = """
                    CREATE TABLE IF NOT EXISTS event_feedback (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                        agenda_item_id INTEGER REFERENCES event_agenda(id) ON DELETE SET NULL,
                        participant_id INTEGER REFERENCES event_participants(id) ON DELETE SET NULL,
                        participant_email VARCHAR(255) NOT NULL,
                        participant_name VARCHAR(255) NOT NULL,
                        feedback_type VARCHAR(50) DEFAULT 'event',
                        overall_rating INTEGER CHECK (overall_rating >= 1 AND overall_rating <= 5),
                        content_rating INTEGER CHECK (content_rating >= 1 AND content_rating <= 5),
                        organization_rating INTEGER CHECK (organization_rating >= 1 AND organization_rating <= 5),
                        venue_rating INTEGER CHECK (venue_rating >= 1 AND venue_rating <= 5),
                        accommodation_rating INTEGER CHECK (accommodation_rating >= 1 AND accommodation_rating <= 5),
                        transport_rating INTEGER CHECK (transport_rating >= 1 AND transport_rating <= 5),
                        food_rating INTEGER CHECK (food_rating >= 1 AND food_rating <= 5),
                        session_rating INTEGER CHECK (session_rating >= 1 AND session_rating <= 5),
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
                    
                    # Create event_food_menu table
                    create_food_menu_table = """
                    CREATE TABLE IF NOT EXISTS event_food_menu (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                        day_number INTEGER NOT NULL,
                        meal_type VARCHAR(50) NOT NULL,
                        menu_items TEXT NOT NULL,
                        dietary_notes TEXT,
                        created_by VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_food_menu_table))
                    
                    # Add dietary requirements to event_participants
                    dietary_columns = [
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS dietary_requirements TEXT",
                        "ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS allergies TEXT"
                    ]
                    for sql in dietary_columns:
                        conn.execute(text(sql))
                    
                    # Add missing columns to public_registrations table
                    public_reg_columns = [
                        "ALTER TABLE public_registrations ADD COLUMN IF NOT EXISTS travelling_internationally VARCHAR(10)",
                        "ALTER TABLE public_registrations ADD COLUMN IF NOT EXISTS accommodation_type VARCHAR(100)",
                        "ALTER TABLE public_registrations ADD COLUMN IF NOT EXISTS dietary_requirements TEXT",
                        "ALTER TABLE public_registrations ADD COLUMN IF NOT EXISTS accommodation_needs TEXT",
                        "ALTER TABLE public_registrations ADD COLUMN IF NOT EXISTS daily_meals TEXT",
                        "ALTER TABLE public_registrations ADD COLUMN IF NOT EXISTS certificate_name VARCHAR(255)",
                        "ALTER TABLE public_registrations ADD COLUMN IF NOT EXISTS code_of_conduct_confirm VARCHAR(10)",
                        "ALTER TABLE public_registrations ADD COLUMN IF NOT EXISTS travel_requirements_confirm VARCHAR(10)"
                    ]
                    for sql in public_reg_columns:
                        conn.execute(text(sql))
                    
                    # Add feedback type columns to existing feedback table
                    feedback_columns = [
                        "ALTER TABLE event_feedback ADD COLUMN IF NOT EXISTS agenda_item_id INTEGER REFERENCES event_agenda(id) ON DELETE SET NULL",
                        "ALTER TABLE event_feedback ADD COLUMN IF NOT EXISTS feedback_type VARCHAR(50) DEFAULT 'event'",
                        "ALTER TABLE event_feedback ADD COLUMN IF NOT EXISTS accommodation_rating INTEGER CHECK (accommodation_rating >= 1 AND accommodation_rating <= 5)",
                        "ALTER TABLE event_feedback ADD COLUMN IF NOT EXISTS transport_rating INTEGER CHECK (transport_rating >= 1 AND transport_rating <= 5)",
                        "ALTER TABLE event_feedback ADD COLUMN IF NOT EXISTS food_rating INTEGER CHECK (food_rating >= 1 AND food_rating <= 5)",
                        "ALTER TABLE event_feedback ADD COLUMN IF NOT EXISTS session_rating INTEGER CHECK (session_rating >= 1 AND session_rating <= 5)"
                    ]
                    for sql in feedback_columns:
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
                        msf_email VARCHAR(255),
                        hrco_email VARCHAR(255),
                        career_manager_email VARCHAR(255),
                        ld_manager_email VARCHAR(255),
                        line_manager_email VARCHAR(255),
                        phone_number VARCHAR(50) NOT NULL,
                        travelling_internationally VARCHAR(10),
                        accommodation_type VARCHAR(100),
                        dietary_requirements TEXT,
                        accommodation_needs TEXT,
                        daily_meals TEXT,
                        certificate_name VARCHAR(255),
                        code_of_conduct_confirm VARCHAR(10),
                        travel_requirements_confirm VARCHAR(10),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_public_registrations_table))
                    
                    # Create security_briefings table
                    create_security_briefings_table = """
                    CREATE TABLE IF NOT EXISTS security_briefings (
                        id SERIAL PRIMARY KEY,
                        event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                        title VARCHAR(255) NOT NULL,
                        content TEXT,
                        document_url VARCHAR(500),
                        video_url VARCHAR(500),
                        created_by VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_security_briefings_table))
                    
                    # Create security_briefs table (general security briefings)
                    create_security_briefs_table = """
                    CREATE TABLE IF NOT EXISTS security_briefs (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        brief_type VARCHAR(50) DEFAULT 'general',
                        content_type VARCHAR(50) DEFAULT 'text',
                        content TEXT NOT NULL,
                        event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
                        status VARCHAR(50) DEFAULT 'draft',
                        publish_start_date TIMESTAMP WITH TIME ZONE,
                        publish_end_date TIMESTAMP WITH TIME ZONE,
                        is_active BOOLEAN DEFAULT TRUE,
                        tenant_id VARCHAR(50) NOT NULL,
                        created_by VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_security_briefs_table))
                    
                    # Add new columns to existing security_briefs table
                    security_briefs_columns = [
                        "ALTER TABLE security_briefs ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'draft'",
                        "ALTER TABLE security_briefs ADD COLUMN IF NOT EXISTS publish_start_date TIMESTAMP WITH TIME ZONE",
                        "ALTER TABLE security_briefs ADD COLUMN IF NOT EXISTS publish_end_date TIMESTAMP WITH TIME ZONE",
                        "ALTER TABLE security_briefs ADD COLUMN IF NOT EXISTS category VARCHAR(100)",
                        "ALTER TABLE security_briefs ADD COLUMN IF NOT EXISTS location VARCHAR(255)",
                        "ALTER TABLE security_briefs ADD COLUMN IF NOT EXISTS latitude DECIMAL(10,8)",
                        "ALTER TABLE security_briefs ADD COLUMN IF NOT EXISTS longitude DECIMAL(11,8)"
                    ]
                    for sql in security_briefs_columns:
                        conn.execute(text(sql))
                    
                    # Create user_brief_acknowledgments table
                    create_user_brief_acknowledgments_table = """
                    CREATE TABLE IF NOT EXISTS user_brief_acknowledgments (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        brief_id INTEGER REFERENCES security_briefs(id) ON DELETE CASCADE,
                        acknowledged_at VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                    conn.execute(text(create_user_brief_acknowledgments_table))
                    
                    # Create indexes
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_roles_tenant_id ON roles(tenant_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_inventory_tenant_id ON inventory(tenant_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_event_allocations_event_id ON event_allocations(event_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_event_allocations_tenant_id ON event_allocations(tenant_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_security_briefings_event_id ON security_briefings(event_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_security_briefs_tenant_id ON security_briefs(tenant_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_security_briefs_event_id ON security_briefs(event_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_user_brief_acknowledgments_user_id ON user_brief_acknowledgments(user_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_user_brief_acknowledgments_brief_id ON user_brief_acknowledgments(brief_id)
                    """))
                    
                    # Add new columns to accommodation tables
                    guesthouse_columns = [
                        "ALTER TABLE guesthouses ADD COLUMN IF NOT EXISTS latitude VARCHAR(20)",
                        "ALTER TABLE guesthouses ADD COLUMN IF NOT EXISTS longitude VARCHAR(20)"
                    ]
                    for sql in guesthouse_columns:
                        conn.execute(text(sql))
                    
                    vendor_accommodation_columns = [
                        "ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS latitude VARCHAR(20)",
                        "ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS longitude VARCHAR(20)",
                        "ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS single_rooms INTEGER DEFAULT 0",
                        "ALTER TABLE vendor_accommodations ADD COLUMN IF NOT EXISTS double_rooms INTEGER DEFAULT 0"
                    ]
                    for sql in vendor_accommodation_columns:
                        conn.execute(text(sql))
                    
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
                    
                    # Create default roles after successful migration
                    create_default_roles()
                    return
                except Exception as e:
                    trans.rollback()
                    raise e
        except Exception as e:
            pass  # Try alembic fallback
        
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
            # Create default roles after successful alembic migration
            create_default_roles()
        else:
            pass  # Migration failed
            
    except Exception as e:
        # Don't fail startup if migration fails
        pass

# Database connection test on startup
@app.on_event("startup")
async def startup_event():
    """Test database connection and run migrations on startup"""
    try:
        # Test database connection
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version_info = result.fetchone()[0]
        
        # Run auto-migration in production
        if settings.ENVIRONMENT == "production":
            run_auto_migration()
        
        # Start agenda notification scheduler
        from app.core.agenda_scheduler import agenda_scheduler
        import asyncio
        asyncio.create_task(agenda_scheduler.start())
        
        # Start background tasks
        from app.tasks.background_tasks import background_task_manager
        await background_task_manager.start_background_tasks()

        # Start vetting deadline scheduler
        from app.core.scheduler import start_scheduler
        start_scheduler()
        
    except Exception as e:
        # Don't exit in production - let the app start anyway
        if settings.ENVIRONMENT != "production":
            raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Stop agenda notification scheduler
    from app.core.agenda_scheduler import agenda_scheduler
    agenda_scheduler.stop()

    # Stop vetting deadline scheduler
    from app.core.scheduler import stop_scheduler
    stop_scheduler()

    # Stop background tasks
    from app.tasks.background_tasks import background_task_manager
    await background_task_manager.stop_background_tasks()

# Add a test endpoint to verify error handling
@app.put("/test-validation")
def test_validation_endpoint(data: dict):
    """Test endpoint to verify validation error handling"""
    return {"message": "Test validation successful", "data": data}

# Add a test endpoint for EventUpdate schema
@app.put("/test-event-update")
def test_event_update_endpoint(event_data: dict):
    """Test endpoint to verify EventUpdate schema validation"""
    return {"message": "EventUpdate validation successful", "data": event_data}

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Include vetting router
from app.api.v1.vetting import router as vetting_router
app.include_router(vetting_router, prefix=settings.API_V1_STR, tags=["vetting"])

# Include per diem router
from app.api.v1.perdiem import router as perdiem_router
app.include_router(perdiem_router, prefix=f"{settings.API_V1_STR}/perdiem", tags=["perdiem"])

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

@app.exception_handler(422)
async def validation_error_handler(request: Request, exc: Exception):
    """Handle validation errors"""
    logger.error(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "message": str(exc),
            "status_code": 422
        }
    )

@app.exception_handler(400)
async def bad_request_handler(request: Request, exc: Exception):
    """Handle bad request errors"""
    logger.error(f"Bad request error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Bad request",
            "message": str(exc) or getattr(exc, 'detail', 'Unknown error'),
            "status_code": 400
        }
    )

@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors"""
    logger.error(f"FastAPI validation error: {str(exc)}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Request validation error",
            "message": "Invalid request data",
            "details": exc.errors(),
            "status_code": 422
        }
    )

@app.exception_handler(ValidationError)
async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    logger.error(f"Pydantic validation error: {str(exc)}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Data validation error",
            "message": "Invalid data format",
            "details": exc.errors(),
            "status_code": 422
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
    
    print(f">> Starting server on {host}:{port}")
    print(f">> CORS configured for: {allowed_origins}")
    uvicorn.run(
        app, 
        host=host, 
        port=port,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.ENVIRONMENT == "development"
    )