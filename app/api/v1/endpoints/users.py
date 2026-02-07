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
        
        # Group tenants and collect all roles for each tenant
        tenant_roles = {}
        for ut in user_tenants:
            tenant_id = ut.tenant_id
            if tenant_id not in tenant_roles:
                tenant_roles[tenant_id] = {
                    "tenant_id": tenant_id,
                    "tenant_name": ut.tenant.name if ut.tenant else tenant_id,
                    "roles": [],
                    "is_active": ut.is_active,
                    "is_primary": ut.is_primary
                }
            
            # Add role if not already present
            role_value = ut.role.value if ut.role else None
            if role_value and role_value not in tenant_roles[tenant_id]["roles"]:
                tenant_roles[tenant_id]["roles"].append(role_value)
        
        tenants = []
        for tenant_data in tenant_roles.values():
            # Set primary role as the first role, or use the first role available
            primary_role = tenant_data["roles"][0] if tenant_data["roles"] else None

            tenants.append({
                "tenant_id": tenant_data["tenant_id"],
                "tenant_slug": tenant_data["tenant_id"],  # Add tenant_slug for frontend compatibility
                "tenant_name": tenant_data["tenant_name"],
                "role": primary_role,  # Keep for backward compatibility
                "roles": tenant_data["roles"],  # All roles for this tenant
                "is_active": tenant_data["is_active"],
                "is_primary": tenant_data["is_primary"]
            })
        
        # If user has no tenant associations from user_tenants, check user_roles table
        if not tenants:
            from app.models.user_roles import UserRole as UserRoleModel

            # Get all roles with tenant_id from user_roles table
            user_role_tenants = db.query(UserRoleModel).filter(
                UserRoleModel.user_id == current_user.id,
                UserRoleModel.tenant_id.isnot(None)
            ).all()

            # Group by tenant_id
            role_tenant_map = {}
            for ur in user_role_tenants:
                if ur.tenant_id not in role_tenant_map:
                    role_tenant_map[ur.tenant_id] = []
                role_tenant_map[ur.tenant_id].append(ur.role)

            # Create tenant entries from user_roles
            for tenant_slug, roles in role_tenant_map.items():
                tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
                if tenant:
                    tenants.append({
                        "tenant_id": tenant.slug,
                        "tenant_slug": tenant.slug,
                        "tenant_name": tenant.name,
                        "role": roles[0] if roles else None,
                        "roles": roles,
                        "is_active": True,
                        "is_primary": tenant.slug == current_user.tenant_id
                    })

            print(f"DEBUG: Found {len(tenants)} tenants from user_roles table")

        # If still no tenants but user has a primary tenant_id (and it's not 'default'), include it
        if not tenants and current_user.tenant_id and current_user.tenant_id != 'default':
            tenant = db.query(Tenant).filter(Tenant.slug == current_user.tenant_id).first()
            if tenant:
                # Include all user roles from session if available
                user_roles = []
                if hasattr(current_user, 'all_roles') and current_user.all_roles:
                    user_roles = current_user.all_roles
                elif current_user.role:
                    user_roles = [current_user.role.value]

                tenants.append({
                    "tenant_id": tenant.slug,
                    "tenant_slug": tenant.slug,
                    "tenant_name": tenant.name,
                    "role": current_user.role.value if current_user.role else None,
                    "roles": user_roles,
                    "is_active": True,
                    "is_primary": True
                })
        
        # If we have tenants but they don't include all session roles, merge them
        elif tenants and hasattr(current_user, 'all_roles') and current_user.all_roles:
            print(f"DEBUG: Merging session roles. User: {current_user.email}, Session roles: {current_user.all_roles}")
            for tenant in tenants:
                # Add any missing roles from session to each tenant
                session_roles = current_user.all_roles if isinstance(current_user.all_roles, list) else []
                existing_roles = tenant.get('roles', [])
                
                print(f"DEBUG: Tenant {tenant['tenant_id']} - Existing roles: {existing_roles}, Session roles: {session_roles}")
                
                # Merge session roles with existing tenant roles
                all_roles = list(set(existing_roles + session_roles))
                tenant['roles'] = all_roles
                
                print(f"DEBUG: Merged roles for tenant {tenant['tenant_id']}: {all_roles}")
                
                # Update primary role if needed
                if not tenant.get('role') and all_roles:
                    tenant['role'] = all_roles[0]
        
        print(f"DEBUG: Final tenants response: {tenants}")
        
        return tenants
        
    except Exception as e:
        print(f"Error fetching user tenants: {e}")
        # Fallback: return user's primary tenant if available (and it's not 'default')
        if current_user.tenant_id and current_user.tenant_id != 'default':
            try:
                from app.models.tenant import Tenant
                tenant = db.query(Tenant).filter(Tenant.slug == current_user.tenant_id).first()
                if tenant:
                    # Include all user roles from session if available
                    user_roles = []
                    if hasattr(current_user, 'all_roles') and current_user.all_roles:
                        user_roles = current_user.all_roles
                    elif current_user.role:
                        user_roles = [current_user.role.value]

                    return [{
                        "tenant_id": tenant.slug,
                        "tenant_slug": tenant.slug,
                        "tenant_name": tenant.name,
                        "role": current_user.role.value if current_user.role else None,
                        "roles": user_roles,
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

@router.post("/create-staff", response_model=schemas.User)
def create_staff_user(
    *,
    db: Session = Depends(get_db),
    user_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Create staff user directly without invitation."""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    email = user_data.get("email", "").strip()
    full_name = user_data.get("full_name", "").strip()
    tenant_id = user_data.get("tenant_id")
    
    if not email or not full_name or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email, full name, and tenant are required"
        )
    
    # Validate MSF email
    if ".msf.org" not in email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Staff members must have an @msf.org email address"
        )
    
    # Check if user already exists
    existing_user = crud.user.get_by_email(db, email=email)
    
    if existing_user:
        # User exists, add them to this tenant with STAFF role
        from app.models.user_roles import UserRole as UserRoleModel
        
        # Check if user already has STAFF role in this tenant
        existing_role = db.query(UserRoleModel).filter(
            UserRoleModel.user_id == existing_user.id,
            UserRoleModel.role == "STAFF",
            UserRoleModel.tenant_id == tenant_id
        ).first()
        
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has STAFF role in this tenant"
            )
        
        # Add STAFF role for this tenant
        staff_role = UserRoleModel(
            user_id=existing_user.id,
            role="STAFF",
            tenant_id=tenant_id
        )
        db.add(staff_role)
        db.commit()
        db.refresh(existing_user)
        
        return existing_user
    
    # Create new user with STAFF role
    from app.core.security import get_password_hash
    import secrets
    from app.models.user import AuthProvider
    
    temp_password = secrets.token_urlsafe(16)
    
    user_create = schemas.UserCreate(
        email=email,
        full_name=full_name,
        password=temp_password,
        role=UserRole.GUEST,
        tenant_id=tenant_id,
        status=UserStatus.ACTIVE,
        auth_provider=AuthProvider.MICROSOFT_SSO
    )
    
    user = crud.user.create(db, obj_in=user_create)
    
    # Add STAFF role via user_roles table
    from app.models.user_roles import UserRole as UserRoleModel
    
    staff_role = UserRoleModel(
        user_id=user.id,
        role="STAFF",
        tenant_id=tenant_id
    )
    db.add(staff_role)
    db.commit()
    db.refresh(user)
    
    return user

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
    db.refresh(updated_user)
    return updated_user
