from typing import Any
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

class AddRoleRequest(BaseModel):
    user_id: int
    role: str

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
    """Add a role to a user."""
    logger.info(f"🎯 Adding role {request.role} to user {request.user_id} by {current_user.email}")
    
    try:
        # Check permissions
        if current_user.role not in [UserRoleEnum.SUPER_ADMIN, UserRoleEnum.MT_ADMIN, UserRoleEnum.HR_ADMIN]:
            print(f"DEBUG: Permission denied - User role: {current_user.role}, Required: [SUPER_ADMIN, MT_ADMIN, HR_ADMIN]")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Check if user already has this role
        existing_role = db.query(UserRole).filter(
            UserRole.user_id == request.user_id,
            UserRole.role == request.role,
            UserRole.is_active == True
        ).first()
        
        if existing_role:
            logger.warning(f"❌ User {request.user_id} already has role {request.role}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has this role"
            )
        
        # Add new role
        new_role = UserRole(
            user_id=request.user_id,
            role=request.role,
            granted_by=current_user.email,
            granted_at=datetime.utcnow(),
            is_active=True
        )
        
        db.add(new_role)
        db.commit()
        
        logger.info(f"✅ Role {request.role} added to user {request.user_id}")
        return {"message": "Role added successfully"}
        
    except Exception as e:
        logger.error(f"💥 Error adding role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add role: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=list)
def get_user_roles(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user = Depends(deps.get_current_user)
) -> Any:
    """Get all active roles for a user."""
    try:
        user_roles = db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.is_active == True
        ).all()
        
        return [{
            "id": role.id,
            "role": role.role,
            "granted_by": role.granted_by,
            "granted_at": role.granted_at
        } for role in user_roles]
        
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
    request: AddRoleRequest,
    current_user = Depends(deps.get_current_user)
) -> Any:
    """Remove a role from a user."""
    print(f"DEBUG: Role removal request - User: {request.user_id}, Role: {request.role}, By: {current_user.email}")
    logger.info(f"🗑️ Removing role {request.role} from user {request.user_id} by {current_user.email}")
    
    try:
        # Check permissions
        if current_user.role not in [UserRoleEnum.SUPER_ADMIN, UserRoleEnum.MT_ADMIN, UserRoleEnum.HR_ADMIN]:
            print(f"DEBUG: Permission denied - User role: {current_user.role}, Required: [SUPER_ADMIN, MT_ADMIN, HR_ADMIN]")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Find the role to remove
        print(f"DEBUG: Looking for role {request.role} for user {request.user_id}")
        role_to_remove = db.query(UserRole).filter(
            UserRole.user_id == request.user_id,
            UserRole.role == request.role,
            UserRole.is_active == True
        ).first()
        
        print(f"DEBUG: Role found: {role_to_remove is not None}")
        if not role_to_remove:
            print(f"DEBUG: Role {request.role} not found for user {request.user_id}")
            logger.warning(f"❌ Role {request.role} not found for user {request.user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found for this user"
            )
        
        # Mark role as inactive
        role_to_remove.is_active = False
        role_to_remove.revoked_at = datetime.utcnow()
        role_to_remove.revoked_by = current_user.email
        
        # Check if user has any remaining active non-guest roles
        remaining_roles = db.query(UserRole).filter(
            UserRole.user_id == request.user_id,
            UserRole.is_active == True,
            UserRole.id != role_to_remove.id,
            UserRole.role != 'GUEST'
        ).all()
        
        user = db.query(User).filter(User.id == request.user_id).first()
        
        # If removing the last non-guest role and user is not a tenant admin
        if len(remaining_roles) == 0 and user and not user.role == UserRoleEnum.MT_ADMIN:
            # Check if user has tenant admin role in their primary role
            if "TENANT_ADMIN" not in str(user.role):
                # Remove user from tenant - deactivate user-tenant relationship
                user_tenant = db.query(UserTenant).filter(
                    UserTenant.user_id == request.user_id,
                    UserTenant.is_active == True
                ).first()
                
                if user_tenant:
                    user_tenant.is_active = False
                    user_tenant.deactivated_at = datetime.utcnow()
                    logger.info(f"🏢 User {request.user_id} removed from tenant {user_tenant.tenant_id}")
                
                # Remove tenant association from user
                user.tenant_id = None
            
            # Assign Guest role if no guest role exists
            existing_guest = db.query(UserRole).filter(
                UserRole.user_id == request.user_id,
                UserRole.role == 'GUEST',
                UserRole.is_active == True
            ).first()
            
            if not existing_guest:
                guest_role = UserRole(
                    user_id=request.user_id,
                    role='GUEST',
                    granted_by="system",
                    granted_at=datetime.utcnow(),
                    is_active=True
                )
                db.add(guest_role)
            
            # Update user's primary role to Guest
            if user:
                user.role = UserRoleEnum.GUEST
            
            logger.info(f"👤 User {request.user_id} assigned Guest role (no active roles remaining)")
        
        db.commit()
        print(f"DEBUG: Role removal committed to database")
        
        logger.info(f"✅ Role {request.role} removed from user {request.user_id}")
        # Check if user was removed from tenant
        if len(remaining_roles) == 0 and user and not user.role == UserRoleEnum.MT_ADMIN and "TENANT_ADMIN" not in str(user.role):
            return {"message": "Role removed successfully. User has been removed from tenant and assigned Guest role."}
        else:
            return {"message": "Role removed successfully"}
        
    except Exception as e:
        logger.error(f"💥 Error removing role: {str(e)}")
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
            role='GUEST',
            granted_by="system",
            granted_at=datetime.utcnow(),
            is_active=True
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