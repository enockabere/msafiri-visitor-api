# File: app/api/v1/endpoints/auth.py
# Copy this EXACT content to replace your current auth.py file

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
from app.core.tenant_auto_assignment import auto_assign_tenant_admin
from app.db.database import get_db
from app.models.user import AuthProvider, UserRole, UserStatus
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 compatible token login for LOCAL AUTH users (username/password)"""
    print(f"DEBUG: Login attempt - Username: {form_data.username}")
    
    # Handle multi-tenant login format: user@domain@tenant
    email_parts = form_data.username.split("@")
    if len(email_parts) > 2:  # Format: user@domain@tenant
        email = "@".join(email_parts[:-1])
        tenant_slug = email_parts[-1]
        print(f"DEBUG: Multi-tenant login - Email: {email}, Tenant: {tenant_slug}")
        
        tenant = crud.tenant.get_by_slug(db, slug=tenant_slug)
        if not tenant:
            print(f"DEBUG: Tenant not found: {tenant_slug}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant"
            )
        tenant_id = tenant.slug
    else:
        email = form_data.username
        tenant_id = None
        print(f"DEBUG: Single login - Email: {email}, Tenant: {tenant_id}")

    # Use local authentication (username/password)
    print(f"DEBUG: Attempting authentication for email: {email}, tenant: {tenant_id}")
    user = crud.user.authenticate_local(
        db, email=email, password=form_data.password, tenant_id=tenant_id
    )
    print(f"DEBUG: Authentication result: {user is not None}")
    if user:
        print(f"DEBUG: User found - ID: {user.id}, Role: {user.role}, Active: {user.is_active}")
    
    if not user:
        print(f"DEBUG: Authentication failed - no user found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    elif not crud.user.is_active(user):
        print(f"DEBUG: User inactive - ID: {user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Auto-assign tenant admin users to their tenant
    auto_assign_tenant_admin(db, user)
    
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
        "tenant_id": user.tenant_id,
        "full_name": user.full_name,
        "email": user.email
    }
    
    # Add first login flag for frontend
    if is_first_login:
        response_data["first_login"] = True
        response_data["welcome_message"] = f"Welcome to the system, {user.full_name}!"
    
    # Check if password must be changed (either flag is set or using default password)
    must_change = (hasattr(user, 'must_change_password') and user.must_change_password) or form_data.password == "password@1234"
    if must_change:
        response_data["must_change_password"] = True
    
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
    
    # Auto-assign tenant admin users to their tenant
    auto_assign_tenant_admin(db, user)
    
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
        "tenant_id": user.tenant_id,
        "full_name": user.full_name,
        "email": user.email
    }
    
    if is_first_login:
        response_data["first_login"] = True
        response_data["welcome_message"] = f"Welcome to the system, {user.full_name}!"
    
    return response_data

@router.post("/test-token", response_model=schemas.User)
def test_token(current_user: schemas.User = Depends(deps.get_current_user)) -> Any:
    """Test access token - see who you're logged in as"""
    return current_user

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
        
        # Check if there's a pending invitation for this email
        from app.crud.invitation import invitation as crud_invitation
        pending_invitation = crud_invitation.get_by_email_and_tenant(
            db, email=user_data["email"], tenant_id=tenant_id
        )
        
        if pending_invitation and pending_invitation.is_accepted == "false":
            logger.info(f"Found pending invitation for {user_data['email']} with role {pending_invitation.role}")
            # Use invitation role instead of default GUEST
            user_data["role"] = pending_invitation.role
        
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
        
        # Auto-assign tenant admin users to their tenant
        auto_assign_tenant_admin(db, user)
        
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

@router.post("/login/mobile", response_model=schemas.Token)
def mobile_login(
    login_data: schemas.LoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """Mobile app login - allows access without tenant restrictions"""
    
    # Mobile users can login without tenant restrictions
    user = crud.user.authenticate_local(
        db, email=login_data.email, password=login_data.password, tenant_id=None
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
    
    # Record login
    is_first_login = crud.user.is_first_login(user)
    updated_user = crud.user.record_login(db, user=user)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email,
        tenant_id=None,  # Mobile users can access all tenants
        expires_delta=access_token_expires
    )
    
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
        "tenant_id": None,  # Mobile users can see all tenant data
        "full_name": user.full_name,
        "email": user.email
    }
    
    if is_first_login:
        response_data["first_login"] = True
        response_data["welcome_message"] = f"Welcome to the system, {user.full_name}!"
    
    return response_data

@router.post("/sso/microsoft/mobile", response_model=schemas.Token)
async def microsoft_sso_mobile_login(
    microsoft_access_token: str = Header(..., alias="X-Microsoft-Token"),
    db: Session = Depends(get_db)
) -> Any:
    """Microsoft SSO for mobile app"""
    try:
        logger.info(f"Mobile SSO login attempt started")
        ms_sso = MicrosoftSSO()
        user_data = await ms_sso.verify_token(microsoft_access_token)
        
        logger.info(f"User data retrieved: email={user_data.get('email')}, name={user_data.get('full_name')}")
        
        is_msf_user = ms_sso.is_msf_email(user_data["email"])
        logger.info(f"MSF email check: email={user_data['email']}, is_msf={is_msf_user}")
        
        if not is_msf_user:
            logger.warning(f"Non-MSF user rejected: {user_data['email']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only MSF staff can access the mobile app"
            )
        
        tenant_id = ms_sso.get_tenant_from_email(user_data["email"]) or "msf-global"
        
        existing_user = crud.user.get_by_email(db, email=user_data["email"])
        is_new_user = existing_user is None
        
        user = crud.user.create_or_update_sso_user(
            db, user_data=user_data, tenant_id=tenant_id
        )
        
        if user.status == UserStatus.PENDING_APPROVAL and is_msf_user:
            user = crud.user.approve_user(
                db, user_id=user.id, approved_by="system_auto_approval"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account access denied. Contact administrator."
            )
        
        # Auto-assign tenant admin users to their tenant
        auto_assign_tenant_admin(db, user)
        
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
        
    except HTTPException as he:
        logger.error(f"Mobile SSO HTTP error: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Mobile SSO authentication failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Mobile SSO authentication failed: {str(e)}"
        )

@router.post("/update-fcm-token")
def update_fcm_token(
    token_data: schemas.FCMTokenUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update FCM token for push notifications"""
    try:
        user = crud.user.get_by_email(db, email=current_user.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update FCM token
        user.fcm_token = token_data.fcm_token
        db.commit()
        
        logger.info(f"🔔 FCM token updated for user: {user.email}")
        return {"message": "FCM token updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update FCM token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update FCM token"
        )