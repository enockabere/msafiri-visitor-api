# File: app/api/v1/api.py (UPDATED WITH PASSWORD ENDPOINTS)
from fastapi import APIRouter
from app.api.v1.endpoints import auth, tenants, users, notifications, password

# Create main API router
api_router = APIRouter()

# Include all endpoint routers with proper configuration
api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["authentication"]
)

api_router.include_router(
    password.router, 
    prefix="/password", 
    tags=["password-management"]
)

api_router.include_router(
    tenants.router, 
    prefix="/tenants", 
    tags=["tenants"]
)

api_router.include_router(
    users.router, 
    prefix="/users", 
    tags=["users"]
)

api_router.include_router(
    notifications.router, 
    prefix="/notifications", 
    tags=["notifications"]
)

# Add a test endpoint to verify the router works
@api_router.get("/", tags=["root"])
async def api_root():
    """API v1 root endpoint"""
    return {
        "message": "Msafiri API v1",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth - Authentication endpoints",
            "password": "/password - Password management",
            "users": "/users - User management", 
            "tenants": "/tenants - Tenant management",
            "notifications": "/notifications - Notification system"
        }
    }