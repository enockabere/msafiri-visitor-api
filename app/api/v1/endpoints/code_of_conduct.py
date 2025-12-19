# File: app/api/v1/endpoints/code_of_conduct.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas.code_of_conduct import (
    CodeOfConductCreate, CodeOfConductUpdate, CodeOfConductResponse
)
from app.crud import code_of_conduct as crud_code

router = APIRouter()

@router.post("/", response_model=CodeOfConductResponse)
def create_code_of_conduct(
    code_data: CodeOfConductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create code of conduct (Admin only)"""
    
    # Allow all admin roles to create code of conduct
    # Check if user has admin role (handle both enum and string)
    admin_roles = ["super_admin", "mt_admin", "hr_admin", "event_admin"]
    user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role).lower()
    
    # Also check enum directly
    is_admin = (user_role_str in admin_roles or 
                current_user.role == UserRole.SUPER_ADMIN or
                current_user.role == UserRole.MT_ADMIN or
                current_user.role == UserRole.HR_ADMIN or
                current_user.role == UserRole.EVENT_ADMIN)
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only admins can create code of conduct. Your role: {current_user.role}"
        )
    
    # Deactivate existing active code
    existing = crud_code.get_code_of_conduct_by_tenant(db, current_user.tenant_id)
    if existing:
        crud_code.update_code_of_conduct(
            db, existing.id, 
            CodeOfConductUpdate(is_active=False),
            current_user.email
        )
    
    code = crud_code.create_code_of_conduct(
        db=db,
        code_data=code_data,
        tenant_id=current_user.tenant_id,
        created_by=current_user.email
    )
    
    return code

@router.get("/public/{tenant_slug}")
def get_public_code_of_conduct(
    tenant_slug: str,
    db: Session = Depends(get_db)
):
    """Get active code of conduct for tenant - public access (no auth required)"""

    # Get tenant by slug
    from app.models.tenant import Tenant
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    code = crud_code.get_code_of_conduct_by_tenant(db, tenant.id)
    if not code:
        return None  # Return null instead of 404 for frontend to handle

    return code

@router.get("/")
def get_active_code_of_conduct(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get active code of conduct for tenant - accessible to all authenticated users"""

    code = crud_code.get_code_of_conduct_by_tenant(db, current_user.tenant_id)
    if not code:
        return None  # Return null instead of 404 for frontend to handle

    return code

@router.get("/all", response_model=List[CodeOfConductResponse])
def get_all_codes_of_conduct(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all codes of conduct for tenant (Admin only)"""
    
    # Check if user has admin role (handle both enum and string)
    admin_roles = ["super_admin", "mt_admin", "hr_admin", "event_admin"]
    user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role).lower()
    
    # Also check enum directly
    is_admin = (user_role_str in admin_roles or 
                current_user.role == UserRole.SUPER_ADMIN or
                current_user.role == UserRole.MT_ADMIN or
                current_user.role == UserRole.HR_ADMIN or
                current_user.role == UserRole.EVENT_ADMIN)
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only admins can view all codes. Your role: {current_user.role}"
        )
    
    codes = crud_code.get_all_codes_by_tenant(db, current_user.tenant_id)
    return codes

@router.put("/{code_id}", response_model=CodeOfConductResponse)
def update_code_of_conduct(
    code_id: int,
    code_data: CodeOfConductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update code of conduct (Admin only)"""
    
    # Allow all admin roles to update code of conduct
    # Check if user has admin role (handle both enum and string)
    admin_roles = ["super_admin", "mt_admin", "hr_admin", "event_admin"]
    user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role).lower()
    
    # Also check enum directly
    is_admin = (user_role_str in admin_roles or 
                current_user.role == UserRole.SUPER_ADMIN or
                current_user.role == UserRole.MT_ADMIN or
                current_user.role == UserRole.HR_ADMIN or
                current_user.role == UserRole.EVENT_ADMIN)
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only admins can update code of conduct. Your role: {current_user.role}"
        )
    
    code = crud_code.update_code_of_conduct(
        db=db,
        code_id=code_id,
        code_data=code_data,
        updated_by=current_user.email
    )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code of conduct not found"
        )
    
    return code

@router.delete("/{code_id}")
def delete_code_of_conduct(
    code_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete code of conduct (Admin only)"""
    
    # Check if user has admin role (handle both enum and string)
    admin_roles = ["super_admin", "mt_admin", "hr_admin", "event_admin"]
    user_role_str = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role).lower()
    
    # Also check enum directly
    is_admin = (user_role_str in admin_roles or 
                current_user.role == UserRole.SUPER_ADMIN or
                current_user.role == UserRole.MT_ADMIN or
                current_user.role == UserRole.HR_ADMIN or
                current_user.role == UserRole.EVENT_ADMIN)
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only admins can delete code of conduct. Your role: {current_user.role}"
        )
    
    success = crud_code.delete_code_of_conduct(db, code_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code of conduct not found"
        )
    
    return {"message": "Code of conduct deleted successfully"}