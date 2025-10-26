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
    """Create new user with notifications."""
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
    
    # ENHANCED: Use method with notifications
    try:
        user = crud.user.create_with_notifications(
            db, 
            obj_in=user_in, 
            created_by=current_user.email
        )
        return user
    except Exception as e:
        if "duplicate key value violates unique constraint" in str(e).lower() and "email" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists. Please use a different email."
            )
        raise e

@router.get("/", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    tenant: str = None
) -> Any:
    """Retrieve users."""

    if tenant:
        users = crud.user.get_by_tenant(db, tenant_id=tenant, skip=skip, limit=limit)
    else:
        users = crud.user.get_multi(db, skip=skip, limit=limit)
    
    return users

@router.post("/activate/{user_id}", response_model=schemas.User)
def activate_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Activate a user account with notifications."""
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
    
    # ENHANCED: Use method with notifications
    updated_user = crud.user.update_status_with_notifications(
        db,
        user=user,
        is_active=True,
        status=UserStatus.ACTIVE,
        changed_by=current_user.email
    )
    
    return updated_user

@router.post("/deactivate/{user_id}", response_model=schemas.User)
def deactivate_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Deactivate a user account with notifications."""
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
    
    # ENHANCED: Use method with notifications
    updated_user = crud.user.update_status_with_notifications(
        db,
        user=user,
        is_active=False,
        status=UserStatus.INACTIVE,
        changed_by=current_user.email
    )
    
    return updated_user

@router.post("/change-role/{user_id}", response_model=schemas.User)
def change_user_role(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    new_role: UserRole,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Change user role with notifications."""
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
    
    # ENHANCED: Use method with notifications
    updated_user = crud.user.update_role_with_notifications(
        db,
        user=user,
        new_role=new_role,
        changed_by=current_user.email
    )
    
    return updated_user

@router.put("/{user_id}/role", response_model=schemas.User)
def update_user_role(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    role_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Update user role with notifications."""
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
    
    new_role = role_data.get("new_role")
    if not new_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_role is required"
        )
    
    # Non-super admins can't create other admins
    if current_user.role != UserRole.SUPER_ADMIN and new_role in ["SUPER_ADMIN", "MT_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign admin roles"
        )
    
    # Update role and send notifications
    old_role = user.role
    updated_user = crud.user.update(db, db_obj=user, obj_in={"role": new_role})
    
    # Send email notification
    from app.core.email_service import email_service
    try:
        email_service.send_role_change_notification(
            email=user.email,
            full_name=user.full_name,
            old_role=old_role,
            new_role=new_role,
            changed_by=current_user.full_name or current_user.email
        )
    except Exception as e:
        print(f"Failed to send role change notification: {e}")
    
    return updated_user

@router.get("/by-email/{email}", response_model=schemas.User)
def get_user_by_email(
    *,
    db: Session = Depends(get_db),
    email: str,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get user by email address."""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = crud.user.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user