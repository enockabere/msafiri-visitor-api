from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole

router = APIRouter()

@router.get("/me", response_model=schemas.User)
def read_user_me(
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.post("/", response_model=schemas.User)
def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: schemas.UserCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new user.
    """
    # Only admins can create users
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if user exists
    existing_user = crud.user.get_by_email(db, email=user_in.email, tenant_id=user_in.tenant_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists in this tenant"
        )
    
    # Validate tenant assignment
    if user_in.tenant_id and current_user.role != UserRole.SUPER_ADMIN:
        # Non-super admins can only create users in their own tenant
        if current_user.tenant_id != user_in.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create user in different tenant"
            )
    
    user = crud.user.create(db, obj_in=user_in)
    return user

@router.get("/", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """
    Retrieve users.
    """
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super admin can see users from any tenant based on context
        users = crud.user.get_by_tenant(db, tenant_id=tenant_context, skip=skip, limit=limit)
    elif current_user.role in [UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        # Admins can see users in their tenant
        users = crud.user.get_by_tenant(db, tenant_id=current_user.tenant_id, skip=skip, limit=limit)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return users