# File: app/api/v1/endpoints/profile.py (BASIC VERSION)
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
def profile_test():
    """Test endpoint for profile management"""
    return {"message": "Profile management endpoints coming soon"}
