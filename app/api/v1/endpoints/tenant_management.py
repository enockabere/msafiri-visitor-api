from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.models.user_tenants import UserTenantRole
from pydantic import BaseModel, EmailStr

router = APIRouter()

class AssignUserToTenantRequest(BaseModel):
    user_email: EmailStr
    role: UserTenantRole
    is_primary: bool = False

class TenantUsersResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    users: List[dict]
    
    class Config:
        from_attributes = True

@router.post("/{tenant_id}/assign-user")
def assign_user_to_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_id: str,
    request: AssignUserToTenantRequest,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Assign a user to a tenant with specific role"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can assign users to tenants"
        )
    
    # Check if tenant exists
    tenant = crud.tenant.get_by_slug(db, slug=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Check if user exists
    user = crud.user.get_by_email(db, email=request.user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Assign user to tenant
    user_tenant = crud.user_tenant.assign_user_to_tenant(
        db,
        user_id=user.id,
        tenant_id=tenant_id,
        role=request.role,
        assigned_by=current_user.email,
        is_primary=request.is_primary
    )
    
    return {
        "message": f"User {request.user_email} assigned to tenant {tenant_id} with role {request.role.value}",
        "user_tenant_id": user_tenant.id
    }

@router.get("/{tenant_id}/users", response_model=TenantUsersResponse)
def get_tenant_users(
    *,
    db: Session = Depends(get_db),
    tenant_id: str,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get all users assigned to a tenant"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can view tenant users"
        )
    
    # Check if tenant exists
    tenant = crud.tenant.get_by_slug(db, slug=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Get all user-tenant relationships for this tenant
    user_tenants = crud.user_tenant.get_tenant_users(db, tenant_id=tenant_id)
    
    # Build response with user details
    users = []
    for ut in user_tenants:
        user = crud.user.get(db, id=ut.user_id)
        if user:
            users.append({
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": ut.role.value,
                "is_primary": ut.is_primary,
                "is_active": ut.is_active,
                "assigned_at": ut.assigned_at,
                "assigned_by": ut.assigned_by
            })
    
    return TenantUsersResponse(
        tenant_id=tenant_id,
        tenant_name=tenant.name,
        users=users
    )

@router.delete("/{tenant_id}/users/{user_id}")
def remove_user_from_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_id: str,
    user_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Remove a user from a tenant"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can remove users from tenants"
        )
    
    # Check if tenant exists
    tenant = crud.tenant.get_by_slug(db, slug=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Check if user exists
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove user from tenant
    success = crud.user_tenant.remove_user_from_tenant(
        db,
        user_id=user_id,
        tenant_id=tenant_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not assigned to this tenant"
        )
    
    return {"message": f"User {user.email} removed from tenant {tenant_id}"}

@router.get("/users/{user_id}/tenants")
def get_user_tenants(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get all tenants for a user"""
    if current_user.role != UserRole.SUPER_ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if user exists
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get all user-tenant relationships for this user
    user_tenants = crud.user_tenant.get_user_tenants(db, user_id=user_id)
    
    # Build response with tenant details
    tenants = []
    for ut in user_tenants:
        tenant = crud.tenant.get_by_slug(db, slug=ut.tenant_id)
        if tenant:
            tenants.append({
                "tenant_id": tenant.slug,
                "tenant_name": tenant.name,
                "role": ut.role.value,
                "is_primary": ut.is_primary,
                "is_active": ut.is_active,
                "assigned_at": ut.assigned_at,
                "assigned_by": ut.assigned_by
            })
    
    return {
        "user_id": user_id,
        "user_email": user.email,
        "tenants": tenants
    }
