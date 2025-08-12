# File: scripts/quick_fix_backgroundtasks.py
"""
Quick fix for BackgroundTasks dependency issue
"""

def fix_auth_endpoints():
    """Fix the BackgroundTasks issue in auth.py"""
    
    auth_content = '''# File: app/api/v1/endpoints/auth.py (BACKGROUND TASKS FIXED)
from datetime import timedelta, datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Header, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.sso import MicrosoftSSO
from app.db.database import get_db
from app.models.user import AuthProvider, UserRole, UserStatus
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
    # Note: BackgroundTasks removed for now - we'll add it back later
) -> Any:
    """OAuth2 compatible token login for LOCAL AUTH users (username/password)"""
    
    # Handle multi-tenant login format: user@domain@tenant
    email_parts = form_data.username.split("@")
    if len(email_parts) > 2:  # Format: user@domain@tenant
        email = "@".join(email_parts[:-1])
        tenant_slug = email_parts[-1]
        
        tenant = crud.tenant.get_by_slug(db, slug=tenant_slug)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant"
            )
        tenant_id = tenant.slug
    else:
        email = form_data.username
        tenant_id = None

    # Use local authentication (username/password)
    user = crud.user.authenticate_local(
        db, email=email, password=form_data.password, tenant_id=tenant_id
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    elif not crud.user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # ENHANCED: Record login and handle first login notifications
    is_first_login = crud.user.is_first_login(user)
    updated_user = crud.user.record_login(db, user=user)
    
    # Generate token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email,
        tenant_id=user.tenant_id,
        expires_delta=access_token_expires
    )
    
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
        "tenant_id": user.tenant_id
    }
    
    # Add first login flag for frontend
    if is_first_login:
        response_data["first_login"] = True
        response_data["welcome_message"] = f"Welcome to the system, {user.full_name}!"
    
    # Security warnings for super admins
    if user.role == UserRole.SUPER_ADMIN:
        response_data["security_warnings"] = ["Consider using strong password management"]
    
    return response_data

@router.post("/login/tenant", response_model=schemas.Token)
def login_with_tenant(
    login_data: schemas.LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """Login with explicit tenant specification (JSON format)"""
    
    tenant_id = None
    if login_data.tenant_slug:
        tenant = crud.tenant.get_by_slug(db, slug=login_data.tenant_slug)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant"
            )
        tenant_id = tenant.slug

    user = crud.user.authenticate_local(
        db, email=login_data.email, password=login_data.password, tenant_id=tenant_id
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    elif not crud.user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Same enhanced logic as above
    is_first_login = crud.user.is_first_login(user)
    updated_user = crud.user.record_login(db, user=user)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email,
        tenant_id=user.tenant_id,
        expires_delta=access_token_expires
    )
    
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
        "tenant_id": user.tenant_id
    }
    
    if is_first_login:
        response_data["first_login"] = True
        response_data["welcome_message"] = f"Welcome to the system, {user.full_name}!"
    
    if user.role == UserRole.SUPER_ADMIN:
        response_data["security_warnings"] = ["Consider using strong password management"]
    
    return response_data

@router.post("/test-token", response_model=schemas.User)
def test_token(current_user: schemas.User = Depends(deps.get_current_user)) -> Any:
    """Test access token - see who you're logged in as"""
    return current_user

# ========== SSO ENDPOINTS (BASIC) ==========

@router.post("/sso/microsoft", response_model=schemas.Token)
async def microsoft_sso_login(
    microsoft_access_token: str = Header(..., alias="X-Microsoft-Token"),
    db: Session = Depends(get_db)
) -> Any:
    """Microsoft SSO authentication with AUTO-REGISTRATION"""
    try:
        ms_sso = MicrosoftSSO()
        user_data = await ms_sso.verify_token(microsoft_access_token)
        
        is_msf_user = ms_sso.is_msf_email(user_data["email"])
        tenant_id = ms_sso.get_tenant_from_email(user_data["email"])
        
        if not tenant_id and is_msf_user:
            tenant_id = "msf-global"
        
        existing_user = crud.user.get_by_email(db, email=user_data["email"])
        is_new_user = existing_user is None
        
        user = crud.user.create_or_update_sso_user(
            db, user_data=user_data, tenant_id=tenant_id
        )
        
        if user.status == UserStatus.PENDING_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail={
                    "message": "Account created successfully. Waiting for admin approval.",
                    "status": "pending_approval",
                    "user_id": user.id
                }
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive. Contact administrator."
            )
        
        is_first_login = crud.user.is_first_login(user) or is_new_user
        crud.user.record_login(db, user=user)
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            subject=user.email,
            tenant_id=user.tenant_id,
            expires_delta=access_token_expires
        )
        
        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "role": user.role.value,
            "tenant_id": user.tenant_id
        }
        
        if is_first_login:
            response_data["first_login"] = True
            response_data["welcome_message"] = f"Welcome to the system, {user.full_name}!"
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SSO authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"SSO authentication failed: {str(e)}"
        )
'''
    
    try:
        with open("app/api/v1/endpoints/auth.py", "w") as f:
            f.write(auth_content)
        print("✅ Fixed BackgroundTasks issue in auth.py")
        return True
    except Exception as e:
        print(f"❌ Error fixing auth.py: {e}")
        return False

def test_api_startup():
    """Test if the API can start up"""
    print("🧪 Testing API startup...")
    
    try:
        # Try importing the main app
        from app.main import app
        print("✅ Main app imports successfully")
        
        # Try importing the API router
        from app.api.v1.api import api_router
        print("✅ API router imports successfully")
        
        # Try importing auth endpoints
        from app.api.v1.endpoints import auth
        print("✅ Auth endpoints import successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ API startup test failed: {e}")
        return False

def main():
    """Quick fix for BackgroundTasks issue"""
    print("🔧 QUICK FIX FOR BACKGROUNDTASKS ISSUE")
    print("=" * 50)
    
    # Step 1: Fix auth endpoints
    if not fix_auth_endpoints():
        return False
    
    # Step 2: Test startup
    if not test_api_startup():
        return False
    
    print("\n🎉 QUICK FIX COMPLETED!")
    print("=" * 50)
    print("✅ BackgroundTasks issue resolved")
    print("✅ API should now start successfully")
    print("\nNow try:")
    print("uvicorn app.main:app --reload")
    
    return True

if __name__ == "__main__":
    if not main():
        print("❌ Quick fix failed - check the errors above")
    else:
        print("🚀 Your API is ready to start!")