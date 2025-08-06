from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Header
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

# ========== REGULAR LOGIN ENDPOINTS (ENHANCED) ==========

@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login for LOCAL AUTH users (username/password)
    Enhanced with first login detection and notifications
    """
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
    }
    
    # Add first login flag for frontend
    if is_first_login:
        response_data["first_login"] = True
        response_data["welcome_message"] = f"Welcome to the system, {user.full_name}!"
    
    return response_data

@router.post("/login/tenant", response_model=schemas.Token)
def login_with_tenant(
    login_data: schemas.LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Login with explicit tenant specification (JSON format)
    Enhanced with first login detection and notifications
    """
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
    
    # ENHANCED: Record login and handle first login notifications
    is_first_login = crud.user.is_first_login(user)
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
    }
    
    # Add first login flag for frontend
    if is_first_login:
        response_data["first_login"] = True
        response_data["welcome_message"] = f"Welcome to the system, {user.full_name}!"
    
    return response_data

@router.post("/test-token", response_model=schemas.User)
def test_token(current_user: schemas.User = Depends(deps.get_current_user)) -> Any:
    """
    Test access token - see who you're logged in as
    """
    return current_user

# ========== SSO ENDPOINTS (ENHANCED) ==========

@router.post("/sso/microsoft", response_model=schemas.Token)
async def microsoft_sso_login(
    microsoft_access_token: str = Header(..., alias="X-Microsoft-Token"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Microsoft SSO authentication with AUTO-REGISTRATION
    Enhanced with first login detection and notifications
    """
    try:
        # Initialize Microsoft SSO handler
        ms_sso = MicrosoftSSO()
        
        # Verify token and get user data from Microsoft
        user_data = await ms_sso.verify_token(microsoft_access_token)
        
        # Check if this is an MSF email (auto-allow) or external (needs approval)
        is_msf_user = ms_sso.is_msf_email(user_data["email"])
        
        # Determine tenant from email domain
        tenant_id = ms_sso.get_tenant_from_email(user_data["email"])
        
        if not tenant_id and is_msf_user:
            # Default to global tenant for MSF users without specific tenant
            tenant_id = "msf-global"
        
        # Track if this is a new user (for first login detection)
        existing_user = crud.user.get_by_email(db, email=user_data["email"])
        is_new_user = existing_user is None
        
        # Create or update user in our database (AUTO-REGISTRATION happens here)
        user = crud.user.create_or_update_sso_user(
            db, user_data=user_data, tenant_id=tenant_id
        )
        
        # Check user status
        if user.status == UserStatus.PENDING_APPROVAL:
            # User auto-registered but needs admin approval
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
        
        # ENHANCED: Record login and handle first login notifications
        is_first_login = crud.user.is_first_login(user) or is_new_user
        crud.user.record_login(db, user=user)
        
        # Generate our application token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            subject=user.email,
            tenant_id=user.tenant_id,
            expires_delta=access_token_expires
        )
        
        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
        }
        
        # Add first login flag for frontend
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

@router.post("/sso/microsoft/mobile", response_model=schemas.Token)
async def microsoft_sso_mobile_login(
    microsoft_access_token: str = Header(..., alias="X-Microsoft-Token"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Microsoft SSO for mobile app - more permissive for news/updates access
    Enhanced with first login detection and notifications
    """
    try:
        ms_sso = MicrosoftSSO()
        user_data = await ms_sso.verify_token(microsoft_access_token)
        
        # More lenient for mobile - allow any MSF user immediate access
        is_msf_user = ms_sso.is_msf_email(user_data["email"])
        
        if not is_msf_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only MSF staff can access the mobile app"
            )
        
        tenant_id = ms_sso.get_tenant_from_email(user_data["email"]) or "msf-global"
        
        # Track if this is a new user (for first login detection)
        existing_user = crud.user.get_by_email(db, email=user_data["email"])
        is_new_user = existing_user is None
        
        # Auto-register with immediate access for mobile
        user = crud.user.create_or_update_sso_user(
            db, user_data=user_data, tenant_id=tenant_id
        )
        
        # For mobile, MSF staff get immediate access (no approval needed)
        if user.status == UserStatus.PENDING_APPROVAL and is_msf_user:
            # Auto-approve MSF staff for mobile access
            user = crud.user.approve_user(
                db, user_id=user.id, approved_by="system_auto_approval"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account access denied. Contact administrator."
            )
        
        # ENHANCED: Record login and handle first login notifications
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
        }
        
        # Add first login flag for frontend
        if is_first_login:
            response_data["first_login"] = True
            response_data["welcome_message"] = f"Welcome to the system, {user.full_name}!"
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mobile SSO authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Mobile SSO authentication failed: {str(e)}"
        )