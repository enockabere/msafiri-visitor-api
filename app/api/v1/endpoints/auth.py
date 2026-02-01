# File: app/api/v1/endpoints/auth.py
# Copy this EXACT content to replace your current auth.py file

from datetime import timedelta, datetime
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

def get_user_all_roles(db: Session, user) -> list:
    """Get all roles for a user (primary + secondary)"""
    roles = [user.role.value]  # Primary role
    
    try:
        # Secondary roles from user_roles table
        from app.models.user_roles import UserRole as UserRoleModel
        user_roles = db.query(UserRoleModel).filter(
            UserRoleModel.user_id == user.id
        ).all()
        roles.extend([role.role for role in user_roles])
        
    except Exception as e:
        logger.warning(f"Error getting user roles: {e}")
    
    return list(set(roles))  # Remove duplicates

def get_user_tenants(db: Session, user) -> list:
    """Get all tenant associations for a user"""
    try:
        from app.models.user_tenants import UserTenant
        from app.models.tenant import Tenant
        
        user_tenants = db.query(UserTenant).join(Tenant).filter(
            UserTenant.user_id == user.id
        ).all()
        
        return [{
            "tenant_id": ut.tenant_id,
            "tenant_name": ut.tenant.name if ut.tenant else ut.tenant_id,
            "tenant_slug": ut.tenant.slug if ut.tenant else ut.tenant_id,
            "role": ut.role.value if ut.role else None
        } for ut in user_tenants]
        
    except Exception as e:
        logger.warning(f"Error getting user tenants: {e}")
        return []

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
        
        # Debug: Print all roles for this user
        try:
            from app.models.user_roles import UserRole as UserRoleModel
            
            # Get relationship-based roles
            user_roles = db.query(UserRoleModel).filter(
                UserRoleModel.user_id == user.id
            ).all()
            
            print(f"DEBUG: Primary role: {user.role}")
            print(f"DEBUG: Secondary roles: {[role.role for role in user_roles]}")
            
        except Exception as e:
            print(f"DEBUG: Error getting roles: {e}")
    
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
    
    # Get all user roles (primary + secondary + vetting)
    all_roles = get_user_all_roles(db, user)
    
    # Get user's tenant associations
    user_tenants = get_user_tenants(db, user)
    
    # If user has no primary tenant (or invalid like 'default') but has tenant associations, set the first one as primary
    if (not user.tenant_id or user.tenant_id == 'default' or user.tenant_id == '') and user_tenants:
        primary_tenant = user_tenants[0]
        user.tenant_id = primary_tenant["tenant_slug"]
        db.commit()
        print(f"DEBUG: Set primary tenant for user {user.id}: {user.tenant_id}")

    # Also check user_roles table for tenant associations if user_tenants is empty
    if (not user.tenant_id or user.tenant_id == 'default' or user.tenant_id == '') and not user_tenants:
        from app.models.user_roles import UserRole as UserRoleModel
        user_role_tenants = db.query(UserRoleModel.tenant_id).filter(
            UserRoleModel.user_id == user.id,
            UserRoleModel.tenant_id.isnot(None)
        ).distinct().all()
        if user_role_tenants:
            user.tenant_id = user_role_tenants[0][0]
            db.commit()
            print(f"DEBUG: Set primary tenant from user_roles for user {user.id}: {user.tenant_id}")
    
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,  # Primary role
        "all_roles": all_roles,  # All roles including vetting
        "tenant_id": user.tenant_id,
        "user_tenants": user_tenants,  # All tenant associations
        "full_name": user.full_name,
        "email": user.email
    }
    
    print(f"DEBUG: Response data - all_roles: {all_roles}")
    
    # Add first login flag for frontend
    if is_first_login:
        response_data["first_login"] = True
        response_data["welcome_message"] = f"Welcome to the system, {user.full_name}!"
    
    # Check if password must be changed (use database flag)
    must_change = (hasattr(user, 'must_change_password') and user.must_change_password)
    if must_change:
        response_data["must_change_password"] = True
    
    return response_data

@router.post("/refresh", response_model=schemas.Token)
def refresh_access_token(
    db: Session = Depends(get_db),
    current_user=Depends(deps.get_current_user_allow_expired)
) -> Any:
    """
    Refresh access token for authenticated users.
    Requires a valid (non-expired or recently expired) access token.
    """
    try:
        # Generate new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            subject=current_user.email,
            tenant_id=current_user.tenant_id,
            expires_delta=access_token_expires
        )

        # Get all user roles
        all_roles = get_user_all_roles(db, current_user)

        # Get user's tenant associations
        user_tenants = get_user_tenants(db, current_user)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": current_user.id,
            "role": current_user.role.value,
            "all_roles": all_roles,
            "tenant_id": current_user.tenant_id,
            "user_tenants": user_tenants,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
        }
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )

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
        user_data["email"] = user_data["email"].lower()
        
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
        
        logger.info(f"🔍 DEBUG: Checking invitation for {user_data['email']} in tenant {tenant_id}")
        logger.info(f"🔍 DEBUG: Found invitation: {pending_invitation is not None}")
        if pending_invitation:
            logger.info(f"🔍 DEBUG: Invitation details - ID: {pending_invitation.id}, Role: {pending_invitation.role}, Accepted: {pending_invitation.is_accepted}")
        
        if pending_invitation and pending_invitation.is_accepted == "false":
            logger.info(f"Found pending invitation for {user_data['email']} with role {pending_invitation.role}")
            # Use invitation role instead of default GUEST
            user_data["role"] = pending_invitation.role
            
            # Mark invitation as accepted
            pending_invitation.is_accepted = "true"
            pending_invitation.accepted_at = datetime.utcnow()
            db.commit()
            logger.info(f"✅ Marked invitation as accepted for {user_data['email']}")
        
        logger.info(f"🔍 DEBUG: About to create/update SSO user with data: {user_data}")
        user = crud.user.create_or_update_sso_user(
            db, user_data=user_data, tenant_id=tenant_id
        )
        logger.info(f"🔍 DEBUG: Created/updated user - ID: {user.id}, Role: {user.role}, Email: {user.email}")
        
        # If there was a pending invitation, ensure the role is properly assigned
        if pending_invitation and pending_invitation.is_accepted == "true":
            from app.models.user_roles import UserRole as UserRoleModel
            
            logger.info(f"🔍 DEBUG: Processing accepted invitation for user {user.id}")
            
            # Check if user already has this role in UserRole table
            existing_role = db.query(UserRoleModel).filter(
                UserRoleModel.user_id == user.id,
                UserRoleModel.role == pending_invitation.role.upper()
            ).first()
            
            logger.info(f"🔍 DEBUG: Existing role check - Role: {pending_invitation.role.upper()}, Found: {existing_role is not None}")
            
            if not existing_role:
                # Remove any Guest roles first
                guest_roles = db.query(UserRoleModel).filter(
                    UserRoleModel.user_id == user.id,
                    UserRoleModel.role == "GUEST"
                ).all()
                logger.info(f"🔍 DEBUG: Found {len(guest_roles)} guest roles to remove")
                for guest_role in guest_roles:
                    db.delete(guest_role)
                
                # Add the invitation role
                new_role = UserRoleModel(
                    user_id=user.id,
                    role=pending_invitation.role.upper()
                )
                db.add(new_role)
                db.commit()
                logger.info(f"✅ Added role {pending_invitation.role} to user {user.email} from invitation")
            else:
                logger.info(f"🔍 DEBUG: User already has role {pending_invitation.role}")
        
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
    """Microsoft SSO for mobile app - allows login regardless of tenant roles"""
    try:
        logger.info(f"Mobile SSO login attempt started")
        ms_sso = MicrosoftSSO()
        user_data = await ms_sso.verify_token(microsoft_access_token)
        user_data["email"] = user_data["email"].lower()
        
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
        
        # Auto-approve MSF users for mobile access
        if user.status == UserStatus.PENDING_APPROVAL and is_msf_user:
            user = crud.user.approve_user(
                db, user_id=user.id, approved_by="mobile_auto_approval"
            )
            logger.info(f"Auto-approved user {user.email} for mobile access")
        
        # For mobile app, allow access even if user is not fully active in web portal
        # as long as they are MSF staff
        if not user.is_active and is_msf_user:
            # Temporarily activate for mobile access
            user.is_active = True
            db.commit()
            logger.info(f"Activated user {user.email} for mobile access")
        
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
            response_data["welcome_message"] = f"Welcome to the mobile app, {user.full_name}!"
        
        logger.info(f"Mobile SSO login successful for {user.email}")
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

@router.post("/select-tenant", response_model=schemas.Token)
def select_tenant(
    tenant_data: dict,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Select tenant for multi-tenant users"""
    
    tenant_slug = tenant_data.get("tenant_slug")
    if not tenant_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant slug is required"
        )
    
    # Verify user has access to this tenant
    user_tenants = get_user_tenants(db, current_user)
    valid_tenant = next((t for t in user_tenants if t["tenant_slug"] == tenant_slug), None)
    
    if not valid_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )
    
    # Generate new token with selected tenant
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=current_user.email,
        tenant_id=tenant_slug,
        expires_delta=access_token_expires
    )
    
    # Get roles specific to this tenant
    all_roles = get_user_all_roles(db, current_user)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": current_user.id,
        "role": current_user.role.value,
        "all_roles": all_roles,
        "tenant_id": tenant_slug,
        "selected_tenant": valid_tenant,
        "full_name": current_user.full_name,
        "email": current_user.email
    }

@router.post("/check-user")
def check_user(
    user_data: dict,
    db: Session = Depends(get_db)
) -> Any:
    """Check user for SSO authentication and return user data with access token"""
    email = user_data.get("email")
    provider = user_data.get("provider", "azure-ad")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    # Find user by email
    user = crud.user.get_by_email(db, email=email.lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Generate access token for SSO user
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email,
        tenant_id=user.tenant_id,
        expires_delta=access_token_expires
    )
    
    # Get all user roles
    all_roles = get_user_all_roles(db, user)
    
    # For SSO users, prioritize non-GUEST roles as primary role
    primary_role = user.role.value
    if primary_role == "GUEST" and all_roles:
        # Find first non-GUEST role to use as primary
        non_guest_roles = [role for role in all_roles if role != "GUEST"]
        if non_guest_roles:
            primary_role = non_guest_roles[0]
    
    # Get user's tenant associations
    user_tenants = get_user_tenants(db, user)
    
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": primary_role,
        "all_roles": all_roles,
        "tenant_id": user.tenant_id,
        "user_tenants": user_tenants,
        "is_active": user.is_active,
        "access_token": access_token,
        "refresh_token": access_token,  # Use same token for refresh
        "first_login": crud.user.is_first_login(user)
    }