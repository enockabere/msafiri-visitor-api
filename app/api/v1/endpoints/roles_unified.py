from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole as UserRoleEnum, User
from app.models.user_roles import UserRole, RoleType
from app.models.user_tenants import UserTenant
from datetime import datetime
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models for user role management
class AddRoleRequest(BaseModel):
    user_id: int
    role: str

class RemoveUserRequest(BaseModel):
    user_id: int
    tenant_id: str

# ============= ROLE DEFINITIONS MANAGEMENT =============

@router.post("/", response_model=schemas.Role)
def create_role(
    *,
    db: Session = Depends(get_db),
    role_in: schemas.RoleCreate,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Create new role for a tenant."""
    if current_user.role not in [UserRoleEnum.SUPER_ADMIN, UserRoleEnum.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    if current_user.role != UserRoleEnum.SUPER_ADMIN and current_user.tenant_id != role_in.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only create roles for your own tenant"
        )
    
    existing_role = crud.role.get_by_name_and_tenant(
        db, name=role_in.name, tenant_id=role_in.tenant_id
    )
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists for this tenant"
        )
    
    role_data = role_in.dict()
    role_data["created_by"] = current_user.email
    role = crud.role.create(db, obj_in=schemas.RoleCreate(**role_data))
    
    return role

@router.get("/", response_model=List[schemas.Role])
def get_roles(
    *,
    db: Session = Depends(get_db),
    tenant: str = None
) -> Any:
    """Get all roles, optionally filtered by tenant."""
    try:
        logger.info(f"Fetching roles for tenant: {tenant}")
        
        if tenant:
            roles = crud.role.get_by_tenant(db, tenant_id=tenant)
            logger.info(f"Found {len(roles)} roles for tenant {tenant}")
        else:
            roles = crud.role.get_multi(db)
            logger.info(f"Found {len(roles)} total roles")
        
        return roles
        
    except Exception as e:
        logger.error(f"Error fetching roles: {str(e)}")
        raise

@router.put("/{role_id}", response_model=schemas.Role)
def update_role(
    *,
    db: Session = Depends(get_db),
    role_id: int,
    role_update: schemas.RoleUpdate,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update a role."""
    role = crud.role.get(db, id=role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    if current_user.role not in [UserRoleEnum.SUPER_ADMIN, UserRoleEnum.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    if current_user.role != UserRoleEnum.SUPER_ADMIN and current_user.tenant_id != role.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update roles for your own tenant"
        )
    
    role_data = role_update.dict(exclude_unset=True)
    role_data["updated_by"] = current_user.email
    
    updated_role = crud.role.update(db, db_obj=role, obj_in=role_data)
    return updated_role

@router.delete("/{role_id}", response_model=dict)
def delete_role(
    *,
    db: Session = Depends(get_db),
    role_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Delete a role."""
    role = crud.role.get(db, id=role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    if current_user.role not in [UserRoleEnum.SUPER_ADMIN, UserRoleEnum.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    if current_user.role != UserRoleEnum.SUPER_ADMIN and current_user.tenant_id != role.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete roles for your own tenant"
        )
    
    crud.role.update(db, db_obj=role, obj_in={"is_active": False})
    return {"message": "Role deleted successfully"}

# ============= USER ROLE ASSIGNMENTS =============

@router.post("/assign", response_model=dict)
def assign_user_role(
    *,
    db: Session = Depends(get_db),
    request: AddRoleRequest,
    current_user = Depends(deps.get_current_user)
) -> Any:
    """Assign a role to a user."""
    logger.info(f"Assigning role {request.role} to user {request.user_id} by {current_user.email}")
    
    try:
        if current_user.role not in [UserRoleEnum.SUPER_ADMIN, UserRoleEnum.MT_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        existing_role = db.query(UserRole).filter(
            UserRole.user_id == request.user_id,
            UserRole.role == RoleType(request.role),
            UserRole.is_active == True
        ).first()
        
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has this role"
            )
        
        new_role = UserRole(
            user_id=request.user_id,
            role=RoleType(request.role),
            granted_by=current_user.email,
            granted_at=datetime.utcnow(),
            is_active=True
        )
        
        db.add(new_role)
        db.commit()
        
        logger.info(f"Role {request.role} assigned to user {request.user_id}")
        return {"message": "Role assigned successfully"}
        
    except Exception as e:
        logger.error(f"Error assigning role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign role: {str(e)}"
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
            "role": role.role.value,
            "granted_by": role.granted_by,
            "granted_at": role.granted_at
        } for role in user_roles]
        
    except Exception as e:
        logger.error(f"Error fetching user roles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user roles: {str(e)}"
        )

@router.delete("/revoke", response_model=dict)
def revoke_user_role(
    *,
    db: Session = Depends(get_db),
    request: AddRoleRequest,
    current_user = Depends(deps.get_current_user)
) -> Any:
    """Revoke a role from a user."""
    logger.info(f"Revoking role {request.role} from user {request.user_id} by {current_user.email}")
    
    try:
        if current_user.role not in [UserRoleEnum.SUPER_ADMIN, UserRoleEnum.MT_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        role_to_remove = db.query(UserRole).filter(
            UserRole.user_id == request.user_id,
            UserRole.role == RoleType(request.role),
            UserRole.is_active == True
        ).first()
        
        if not role_to_remove:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found for this user"
            )
        
        role_to_remove.is_active = False
        role_to_remove.revoked_at = datetime.utcnow()
        role_to_remove.revoked_by = current_user.email
        
        remaining_roles = db.query(UserRole).filter(
            UserRole.user_id == request.user_id,
            UserRole.is_active == True,
            UserRole.id != role_to_remove.id,
            UserRole.role != RoleType.GUEST
        ).all()
        
        user = db.query(User).filter(User.id == request.user_id).first()
        
        if len(remaining_roles) == 0 and user and not user.role == UserRoleEnum.MT_ADMIN:
            if "TENANT_ADMIN" not in str(user.role):
                user_tenant = db.query(UserTenant).filter(
                    UserTenant.user_id == request.user_id,
                    UserTenant.is_active == True
                ).first()
                
                if user_tenant:
                    user_tenant.is_active = False
                    user_tenant.deactivated_at = datetime.utcnow()
                
                user.tenant_id = None
            
            existing_guest = db.query(UserRole).filter(
                UserRole.user_id == request.user_id,
                UserRole.role == RoleType.GUEST,
                UserRole.is_active == True
            ).first()
            
            if not existing_guest:
                guest_role = UserRole(
                    user_id=request.user_id,
                    role=RoleType.GUEST,
                    granted_by="system",
                    granted_at=datetime.utcnow(),
                    is_active=True
                )
                db.add(guest_role)
            
            if user:
                user.role = UserRoleEnum.GUEST
        
        db.commit()
        
        logger.info(f"Role {request.role} revoked from user {request.user_id}")
        return {"message": "Role revoked successfully"}
        
    except Exception as e:
        logger.error(f"Error revoking role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke role: {str(e)}"
        )

@router.delete("/remove-user", response_model=dict)
def remove_user_from_tenant(
    *,
    db: Session = Depends(get_db),
    request: RemoveUserRequest,
    current_user = Depends(deps.get_current_user)
) -> Any:
    """Remove user from tenant and deactivate all their roles."""
    logger.info(f"Removing user {request.user_id} from tenant {request.tenant_id} by {current_user.email}")
    
    try:
        if current_user.role not in [UserRoleEnum.SUPER_ADMIN, UserRoleEnum.MT_ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        user_roles = db.query(UserRole).filter(
            UserRole.user_id == request.user_id,
            UserRole.is_active == True
        ).all()
        
        for role in user_roles:
            role.is_active = False
            role.revoked_at = datetime.utcnow()
            role.revoked_by = current_user.email
        
        user_tenant = db.query(UserTenant).filter(
            UserTenant.user_id == request.user_id,
            UserTenant.tenant_id == request.tenant_id,
            UserTenant.is_active == True
        ).first()
        
        if user_tenant:
            user_tenant.is_active = False
            user_tenant.deactivated_at = datetime.utcnow()
        
        guest_role = UserRole(
            user_id=request.user_id,
            role=RoleType.GUEST,
            granted_by="system",
            granted_at=datetime.utcnow(),
            is_active=True
        )
        db.add(guest_role)
        
        user = db.query(User).filter(User.id == request.user_id).first()
        if user:
            user.role = UserRoleEnum.GUEST
            user.tenant_id = None
        
        db.commit()
        
        logger.info(f"User {request.user_id} removed from tenant {request.tenant_id}")
        return {"message": "User removed from tenant successfully"}
        
    except Exception as e:
        logger.error(f"Error removing user from tenant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove user from tenant: {str(e)}"
        )