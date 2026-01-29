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

@router.get("/tenants")
def get_user_tenants(
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get current user's tenant associations."""
    try:
        from app.models.user_tenants import UserTenant
        from app.models.tenant import Tenant
        
        user_tenants = db.query(UserTenant).join(Tenant).filter(
            UserTenant.user_id == current_user.id,
            UserTenant.is_active == True
        ).all()
        
        tenants = []
        for ut in user_tenants:
            tenants.append({
                "tenant_id": ut.tenant_id,
                "tenant_name": ut.tenant.name if ut.tenant else ut.tenant_id,
                "role": ut.role.value if ut.role else None,
                "is_active": ut.is_active,
                "is_primary": ut.is_primary
            })
        
        # If user has no tenant associations but has a primary tenant_id, include it
        if not tenants and current_user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.slug == current_user.tenant_id).first()
            if tenant:
                tenants.append({
                    "tenant_id": tenant.slug,
                    "tenant_name": tenant.name,
                    "role": current_user.role.value if current_user.role else None,
                    "is_active": True,
                    "is_primary": True
                })
        
        return tenants
        
    except Exception as e:
        print(f"Error fetching user tenants: {e}")
        # Fallback: return user's primary tenant if available
        if current_user.tenant_id:
            try:
                from app.models.tenant import Tenant
                tenant = db.query(Tenant).filter(Tenant.slug == current_user.tenant_id).first()
                if tenant:
                    return [{
                        "tenant_id": tenant.slug,
                        "tenant_name": tenant.name,
                        "role": current_user.role.value if current_user.role else None,
                        "is_active": True,
                        "is_primary": True
                    }]
            except Exception as fallback_error:
                print(f"Fallback error: {fallback_error}")
        
        return []

@router.post("/set-active-tenant/{tenant_id}")
def set_active_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_id: str,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Set the active tenant for the current user session."""
    try:
        from app.models.user_tenants import UserTenant
        from app.models.tenant import Tenant
        
        # Verify user has access to this tenant
        user_tenant = db.query(UserTenant).filter(
            UserTenant.user_id == current_user.id,
            UserTenant.tenant_id == tenant_id,
            UserTenant.is_active == True
        ).first()
        
        # If no UserTenant record but user's primary tenant matches, allow it
        if not user_tenant and current_user.tenant_id == tenant_id:
            tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )
        elif not user_tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this tenant"
            )
        
        # Update user's active tenant
        current_user.tenant_id = tenant_id
        db.commit()
        
        return {"message": "Active tenant updated successfully", "tenant_id": tenant_id}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error setting active tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set active tenant"
        )

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

@router.patch("/profile", response_model=schemas.User)
def update_profile(
    *,
    db: Session = Depends(get_db),
    profile_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Update current user's profile."""
    
    # Only allow updating specific fields
    allowed_fields = ['avatar_url', 'full_name', 'phone']
    update_data = {k: v for k, v in profile_data.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    updated_user = crud.user.update(db, db_obj=current_user, obj_in=update_data)
    return updated_user