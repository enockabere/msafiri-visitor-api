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
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.EVENT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create code of conduct"
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

@router.get("/", response_model=CodeOfConductResponse)
def get_active_code_of_conduct(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get active code of conduct for tenant"""
    
    code = crud_code.get_code_of_conduct_by_tenant(db, current_user.tenant_id)
    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active code of conduct found"
        )
    
    return code

@router.get("/all", response_model=List[CodeOfConductResponse])
def get_all_codes_of_conduct(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all codes of conduct for tenant (Admin only)"""
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.EVENT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view all codes"
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
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.EVENT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update code of conduct"
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
    
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.EVENT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete code of conduct"
        )
    
    success = crud_code.delete_code_of_conduct(db, code_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Code of conduct not found"
        )
    
    return {"message": "Code of conduct deleted successfully"}