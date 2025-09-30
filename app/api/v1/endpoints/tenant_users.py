# File: app/api/v1/endpoints/tenant_users.py
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole, UserStatus, AuthProvider
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class TenantUserCreate(schemas.UserBase):
    """Schema for creating users within a tenant"""
    tenant_role: str  # Custom role name for the tenant
    send_welcome_email: bool = True

class TenantUserRoleUpdate(BaseModel):
    """Schema for updating user role within tenant"""
    tenant_role: str

@router.post("/{tenant_id}/users", response_model=schemas.User)
def add_user_to_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_id: str,
    user_in: TenantUserCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """Add a new user to a specific tenant."""
    # Check permissions - only tenant admin can add users to their tenant
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # If not super admin, can only add users to own tenant
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only add users to your own tenant"
        )
    
    # Check if tenant exists
    tenant = crud.tenant.get_by_slug(db, slug=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Check if user already exists
    existing_user = crud.user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Verify the tenant role exists
    tenant_role = crud.role.get_by_name_and_tenant(
        db, name=user_in.tenant_role, tenant_id=tenant_id
    )
    if not tenant_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{user_in.tenant_role}' does not exist for this tenant"
        )
    
    # Create user for SSO authentication
    user_data = {
        "email": user_in.email,
        "full_name": user_in.full_name,
        "phone_number": user_in.phone_number,
        "department": user_in.department,
        "job_title": user_in.job_title,
        "password": None,  # No password for SSO users
        "tenant_id": tenant_id,
        "role": UserRole.STAFF,  # Default system role
        "auth_provider": AuthProvider.MICROSOFT_SSO,
        "status": UserStatus.ACTIVE  # Active immediately for SSO
    }
    
    user = crud.user.create(db, obj_in=schemas.UserCreate(**user_data))
    
    # Store the tenant-specific role (you might want to create a user_roles table for this)
    # For now, we'll store it in a custom field or handle it separately
    
    # Send welcome email without credentials
    if user_in.send_welcome_email:
        background_tasks.add_task(
            send_user_welcome_email,
            user.email, user.full_name, tenant.name, user_in.tenant_role
        )
    
    logger.info(f"User {user.email} added to tenant {tenant_id} by {current_user.email}")
    
    return user

@router.get("/{tenant_id}/users", response_model=List[schemas.User])
def get_tenant_users(
    *,
    db: Session = Depends(get_db),
    tenant_id: str,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get all users for a specific tenant."""
    users = crud.user.get_by_tenant(db, tenant_id=tenant_id, skip=skip, limit=limit)
    return users

@router.put("/{tenant_id}/users/{user_id}/role", response_model=schemas.User)
def update_user_tenant_role(
    *,
    db: Session = Depends(get_db),
    tenant_id: str,
    user_id: int,
    role_update: TenantUserRoleUpdate,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update a user's role within a tenant."""
    # Check permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # If not super admin, can only update users in own tenant
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update users in your own tenant"
        )
    
    # Get user
    user = crud.user.get(db, id=user_id)
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this tenant"
        )
    
    # Verify the new role exists
    tenant_role = crud.role.get_by_name_and_tenant(
        db, name=role_update.tenant_role, tenant_id=tenant_id
    )
    if not tenant_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role_update.tenant_role}' does not exist for this tenant"
        )
    
    # Update user (you might want to store tenant role separately)
    # For now, we'll just log the change
    logger.info(f"User {user.email} role updated to {role_update.tenant_role} in tenant {tenant_id} by {current_user.email}")
    
    return user

def send_user_welcome_email(email: str, full_name: str, tenant_name: str, role: str):
    """Send welcome email to new user"""
    try:
        from app.core.email_service import email_service
        
        subject = f"Welcome to {tenant_name} - Msafiri System"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #007bff;">Welcome to {tenant_name}</h1>
            
            <p>Hello {full_name},</p>
            
            <p>You have been added to the Msafiri system for <strong>{tenant_name}</strong>.</p>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Your Account Details:</h3>
                <ul>
                    <li><strong>Email:</strong> {email}</li>
                    <li><strong>Role:</strong> {role}</li>
                    <li><strong>Authentication:</strong> Microsoft SSO</li>
                </ul>
            </div>
            
            <p><strong>Login Instructions:</strong> Use your Microsoft account to sign in to the system.</p>
            
            <p>You can access the system at: <a href="http://localhost:3000">http://localhost:3000</a></p>
            
            <p>If you have any questions, please contact your administrator.</p>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            
            <p style="color: #666; font-size: 14px;">
                This is an automated notification from the Msafiri System.
            </p>
        </body>
        </html>
        """
        
        email_service.send_email([email], subject, html_content)
        logger.info(f"Welcome email sent to {email}")
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")