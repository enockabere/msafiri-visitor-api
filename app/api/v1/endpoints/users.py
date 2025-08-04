from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole, UserStatus

router = APIRouter()

@router.get("/me", response_model=schemas.User)
def read_user_me(
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get current user."""
    return current_user

@router.post("/", response_model=schemas.User)
def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: schemas.UserCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Create new user."""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    existing_user = crud.user.get_by_email(db, email=user_in.email, tenant_id=user_in.tenant_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists in this tenant"
        )
    
    if user_in.tenant_id and current_user.role != UserRole.SUPER_ADMIN:
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
    """Retrieve users."""
    if current_user.role == UserRole.SUPER_ADMIN:
        users = crud.user.get_by_tenant(db, tenant_id=tenant_context, skip=skip, limit=limit)
    elif current_user.role in [UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        users = crud.user.get_by_tenant(db, tenant_id=current_user.tenant_id, skip=skip, limit=limit)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return users

@router.post("/activate/{user_id}", response_model=schemas.User)
def activate_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Activate a user account."""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Non-super admins can only manage users in their tenant
    if current_user.role != UserRole.SUPER_ADMIN and user.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot manage user from different tenant"
        )
    
    updated_user = crud.user.update(db, db_obj=user, obj_in={
        "is_active": True,
        "status": UserStatus.ACTIVE
    })
    
    # TODO: Send notification here
    
    return updated_user

@router.post("/deactivate/{user_id}", response_model=schemas.User)
def deactivate_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Deactivate a user account."""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deactivation
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Non-super admins can only manage users in their tenant
    if current_user.role != UserRole.SUPER_ADMIN and user.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot manage user from different tenant"
        )
    
    updated_user = crud.user.update(db, db_obj=user, obj_in={
        "is_active": False,
        "status": UserStatus.INACTIVE
    })
    
    # TODO: Send notification here
    
    return updated_user

@router.post("/change-role/{user_id}", response_model=schemas.User)
def change_user_role(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    new_role: UserRole,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Change user role."""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Non-super admins can't create other admins
    if current_user.role != UserRole.SUPER_ADMIN and new_role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign admin roles"
        )
    
    old_role = user.role
    updated_user = crud.user.update(db, db_obj=user, obj_in={"role": new_role})
    
    # TODO: Send role change notification here
    
    return updated_user