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

router = APIRouter()

# ========== REGULAR LOGIN ENDPOINTS (MISSING FROM YOUR SWAGGER) ==========

@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login for LOCAL AUTH users (username/password)
    This is what you need for testing regular users!
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
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email,
        tenant_id=user.tenant_id,
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.post("/login/tenant", response_model=schemas.Token)
def login_with_tenant(
    login_data: schemas.LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Login with explicit tenant specification (JSON format)
    Better for testing different user types
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
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email,
        tenant_id=user.tenant_id,
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.post("/test-token", response_model=schemas.User)
def test_token(current_user: schemas.User = Depends(deps.get_current_user)) -> Any:
    """
    Test access token - see who you're logged in as
    """
    return current_user

# ========== SSO ENDPOINTS (ALREADY EXIST) ==========

@router.post("/sso/microsoft", response_model=schemas.Token)
async def microsoft_sso_login(
    microsoft_access_token: str = Header(..., alias="X-Microsoft-Token"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Microsoft SSO authentication with AUTO-REGISTRATION
    Any MSF staff can login without being pre-invited
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
        
        # Generate our application token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            subject=user.email,
            tenant_id=user.tenant_id,
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
        
    except HTTPException:
        raise
    except Exception as e:
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
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            subject=user.email,
            tenant_id=user.tenant_id,
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Mobile SSO authentication failed: {str(e)}"
        )