from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole as UserRoleEnum, User
from app.models.user_roles import UserRole
from app.models.user_tenants import UserTenant
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

from pydantic import BaseModel
from typing import Optional

class AddRoleRequest(BaseModel):
    user_id: int
    role: str
    tenant_id: Optional[str] = None  # Tenant context for per-tenant roles

class RemoveRoleRequest(BaseModel):
    user_id: int
    role: str
    tenant_id: Optional[str] = None  # Tenant context - if provided, only removes from this tenant

class RemoveUserRequest(BaseModel):
    user_id: int
    tenant_id: str

@router.post("/", response_model=dict)
def add_user_role(
    *,
    db: Session = Depends(get_db),
    request: AddRoleRequest,
    current_user = Depends(deps.get_current_user)
) -> Any:
    """Add a role to a user (optionally for a specific tenant)."""
    logger.info(f"🎯 Adding role {request.role} to user {request.user_id} for tenant {request.tenant_id} by {current_user.email}")

    try:
        # Check permissions
        if current_user.role not in [UserRoleEnum.SUPER_ADMIN, UserRoleEnum.MT_ADMIN, UserRoleEnum.HR_ADMIN]:
            print(f"DEBUG: Permission denied - User role: {current_user.role}, Required: [SUPER_ADMIN, MT_ADMIN, HR_ADMIN]")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )

        # Check if user already has this role for this tenant
        query = db.query(UserRole).filter(
            UserRole.user_id == request.user_id,
            UserRole.role == request.role
        )
        # If tenant_id is provided, check within that tenant only
        if request.tenant_id:
            query = query.filter(UserRole.tenant_id == request.tenant_id)
        else:
            query = query.filter(UserRole.tenant_id.is_(None))

        existing_role = query.first()

        if existing_role:
            logger.warning(f"❌ User {request.user_id} already has role {request.role} for tenant {request.tenant_id}")
            return {"message": "User already has this role for this tenant"}

        # Add new role with tenant context
        new_role = UserRole(
            user_id=request.user_id,
            role=request.role,
            tenant_id=request.tenant_id  # Associate role with specific tenant
        )

        db.add(new_role)
        db.commit()

        logger.info(f"✅ Role {request.role} added to user {request.user_id} for tenant {request.tenant_id}")
        return {"message": "Role added successfully", "tenant_id": request.tenant_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Error adding role: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add role: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=list)
def get_user_roles(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    tenant_id: Optional[str] = None,  # Optional filter by tenant
    current_user = Depends(deps.get_current_user)
) -> Any:
    """Get all active roles for a user. Optionally filter by tenant."""
    try:
        query = db.query(UserRole).filter(UserRole.user_id == user_id)

        # If tenant_id is provided, filter to that tenant's roles
        if tenant_id:
            query = query.filter(UserRole.tenant_id == tenant_id)

        user_roles = query.all()

        # Filter out inactive roles if the column exists
        active_roles = []
        for role in user_roles:
            if hasattr(role, 'is_active'):
                if role.is_active:
                    active_roles.append(role)
            else:
                # If no is_active column, include all roles
                active_roles.append(role)

        return [{
            "id": role.id,
            "role": role.role,
            "tenant_id": role.tenant_id,  # Include tenant context in response
            "created_at": role.created_at
        } for role in active_roles]

    except Exception as e:
        logger.error(f"💥 Error fetching user roles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user roles: {str(e)}"
        )

@router.delete("/remove", response_model=dict)
def remove_user_role(
    *,
    db: Session = Depends(get_db),
    request: RemoveRoleRequest,
    current_user = Depends(deps.get_current_user)
) -> Any:
    """Remove a role from a user. If tenant_id is provided, only removes from that tenant."""
    print(f"DEBUG: Role removal request - User: {request.user_id}, Role: {request.role}, Tenant: {request.tenant_id}, By: {current_user.email}")
    logger.info(f"🗑️ Removing role {request.role} from user {request.user_id} for tenant {request.tenant_id} by {current_user.email}")

    try:
        # Check permissions
        if current_user.role not in [UserRoleEnum.SUPER_ADMIN, UserRoleEnum.MT_ADMIN, UserRoleEnum.HR_ADMIN]:
            print(f"DEBUG: Permission denied - User role: {current_user.role}, Required: [SUPER_ADMIN, MT_ADMIN, HR_ADMIN]")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )

        # Find the role to remove - IMPORTANT: filter by tenant_id if provided
        print(f"DEBUG: Looking for role {request.role} for user {request.user_id} in tenant {request.tenant_id}")
        query = db.query(UserRole).filter(
            UserRole.user_id == request.user_id,
            UserRole.role == request.role
        )
        # If tenant_id is provided, only remove from that specific tenant
        if request.tenant_id:
            query = query.filter(UserRole.tenant_id == request.tenant_id)

        role_to_remove = query.first()
        
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        print(f"DEBUG: Role found in user_roles: {role_to_remove is not None}")
        print(f"DEBUG: User's primary role: {user.role}")

        # Check if the role being removed is the user's PRIMARY role (in users table)
        is_primary_role = str(user.role.value).upper() == request.role.upper()

        if not role_to_remove and not is_primary_role:
            print(f"DEBUG: Role {request.role} not found for user {request.user_id}")
            logger.warning(f"❌ Role {request.role} not found for user {request.user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found for this user"
            )

        # Delete the role record from user_roles if it exists
        if role_to_remove:
            db.delete(role_to_remove)
            logger.info(f"🗑️ Deleted role {request.role} from user_roles table")

        # If removing the PRIMARY role, we need to update the user's primary role
        if is_primary_role:
            logger.info(f"🔄 Removing PRIMARY role {request.role} from user {user.email}")

            # Find another role to set as primary (prefer admin roles)
            other_roles = db.query(UserRole).filter(
                UserRole.user_id == request.user_id,
                UserRole.role != 'GUEST',
                UserRole.role != request.role.upper()
            ).all()

            if other_roles:
                # Prioritize admin roles for the new primary role
                admin_priority = ['MT_ADMIN', 'HR_ADMIN', 'EVENT_ADMIN', 'FINANCE_ADMIN', 'STAFF']
                new_primary = None
                for priority_role in admin_priority:
                    for r in other_roles:
                        if r.role == priority_role:
                            new_primary = priority_role
                            break
                    if new_primary:
                        break

                if not new_primary:
                    new_primary = other_roles[0].role

                # Update primary role
                try:
                    user.role = UserRoleEnum[new_primary]
                    logger.info(f"✅ Updated primary role to {new_primary}")
                except KeyError:
                    user.role = UserRoleEnum.GUEST
                    logger.warning(f"⚠️ Could not set {new_primary} as primary, defaulting to GUEST")
            else:
                # No other roles, set to GUEST
                user.role = UserRoleEnum.GUEST
                logger.info(f"👤 No other roles found, setting primary to GUEST")

        # Check if user has any remaining active non-guest roles FOR THIS TENANT
        remaining_roles_query = db.query(UserRole).filter(
            UserRole.user_id == request.user_id,
            UserRole.role != 'GUEST',
            UserRole.role != request.role.upper()  # Exclude the role being removed
        )
        # Exclude the deleted role by id if it existed
        if role_to_remove:
            remaining_roles_query = remaining_roles_query.filter(UserRole.id != role_to_remove.id)
        # If we removed from a specific tenant, only check remaining roles in that tenant
        if request.tenant_id:
            remaining_roles_query = remaining_roles_query.filter(UserRole.tenant_id == request.tenant_id)

        remaining_tenant_roles = remaining_roles_query.all()

        # Check ALL remaining roles across all tenants (for primary role decision)
        all_remaining_query = db.query(UserRole).filter(
            UserRole.user_id == request.user_id,
            UserRole.role != 'GUEST',
            UserRole.role != request.role.upper()
        )
        if role_to_remove:
            all_remaining_query = all_remaining_query.filter(UserRole.id != role_to_remove.id)
        all_remaining_roles = all_remaining_query.all()

        # If no more roles in THIS tenant, remove user from this specific tenant
        if len(remaining_tenant_roles) == 0 and request.tenant_id:
            user_tenant = db.query(UserTenant).filter(
                UserTenant.user_id == request.user_id,
                UserTenant.tenant_id == request.tenant_id,
                UserTenant.is_active == True
            ).first()

            if user_tenant:
                user_tenant.is_active = False
                user_tenant.deactivated_at = datetime.utcnow()
                logger.info(f"🏢 User {request.user_id} removed from tenant {request.tenant_id}")

            # If this was the user's primary tenant, clear it
            if user and user.tenant_id == request.tenant_id:
                # Find another active tenant for the user
                other_tenant = db.query(UserTenant).filter(
                    UserTenant.user_id == request.user_id,
                    UserTenant.is_active == True,
                    UserTenant.tenant_id != request.tenant_id
                ).first()
                user.tenant_id = other_tenant.tenant_id if other_tenant else None

        # If no remaining roles in user_roles table, ensure GUEST role exists
        if len(all_remaining_roles) == 0:
            existing_guest = db.query(UserRole).filter(
                UserRole.user_id == request.user_id,
                UserRole.role == 'GUEST'
            ).first()

            if not existing_guest:
                guest_role = UserRole(
                    user_id=request.user_id,
                    role='GUEST',
                    tenant_id=None  # GUEST is a global role
                )
                db.add(guest_role)
                logger.info(f"👤 Added GUEST role to user_roles table")
        
        db.commit()
        print(f"DEBUG: Role removal committed to database")

        logger.info(f"✅ Role {request.role} removed from user {request.user_id} for tenant {request.tenant_id}")

        # Build response message
        if len(remaining_tenant_roles) == 0 and request.tenant_id:
            if len(all_remaining_roles) == 0:
                return {"message": f"Role removed successfully. User has been removed from tenant {request.tenant_id} and assigned Guest role.", "tenant_id": request.tenant_id}
            else:
                return {"message": f"Role removed successfully from tenant {request.tenant_id}. User still has roles in other tenants.", "tenant_id": request.tenant_id}
        else:
            return {"message": "Role removed successfully", "tenant_id": request.tenant_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Error removing role: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove role: {str(e)}"
        )

@router.delete("/remove-user", response_model=dict)
def remove_user_from_tenant(
    *,
    db: Session = Depends(get_db),
    request: RemoveUserRequest,
    current_user = Depends(deps.get_current_user)
) -> Any:
    """Remove user from tenant and deactivate all their roles."""
    logger.info(f"🗑️ Removing user {request.user_id} from tenant {request.tenant_id} by {current_user.email}")
    
    try:
        # Check permissions
        if current_user.role not in [UserRoleEnum.SUPER_ADMIN, UserRoleEnum.MT_ADMIN, UserRoleEnum.HR_ADMIN]:
            print(f"DEBUG: Permission denied - User role: {current_user.role}, Required: [SUPER_ADMIN, MT_ADMIN, HR_ADMIN]")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Deactivate all user roles
        user_roles = db.query(UserRole).filter(
            UserRole.user_id == request.user_id
        ).all()
        
        for role in user_roles:
            if hasattr(role, 'is_active'):
                role.is_active = False
            if hasattr(role, 'revoked_at'):
                role.revoked_at = datetime.utcnow()
            if hasattr(role, 'revoked_by'):
                role.revoked_by = current_user.email
        
        # Deactivate user-tenant relationship
        user_tenant = db.query(UserTenant).filter(
            UserTenant.user_id == request.user_id,
            UserTenant.tenant_id == request.tenant_id,
            UserTenant.is_active == True
        ).first()
        
        if user_tenant:
            user_tenant.is_active = False
            user_tenant.deactivated_at = datetime.utcnow()
        
        # Assign Guest role
        guest_role = UserRole(
            user_id=request.user_id,
            role='GUEST'
        )
        db.add(guest_role)
        
        # Update user's primary role to Guest
        user = db.query(User).filter(User.id == request.user_id).first()
        if user:
            user.role = UserRoleEnum.GUEST
            user.tenant_id = None  # Remove tenant association
        
        db.commit()
        
        logger.info(f"✅ User {request.user_id} removed from tenant {request.tenant_id}")
        return {"message": "User removed from tenant successfully"}
        
    except Exception as e:
        logger.error(f"💥 Error removing user from tenant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove user from tenant: {str(e)}"
        )
