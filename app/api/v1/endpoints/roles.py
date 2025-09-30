# File: app/api/v1/endpoints/roles.py
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole

router = APIRouter()

@router.post("/", response_model=schemas.Role)
def create_role(
    *,
    db: Session = Depends(get_db),
    role_in: schemas.RoleCreate,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Create new role for a tenant."""
    # Check permissions - only super admin or tenant admin can create roles
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # If not super admin, can only create roles for own tenant
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != role_in.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only create roles for your own tenant"
        )
    
    # Check if role already exists for this tenant
    existing_role = crud.role.get_by_name_and_tenant(
        db, name=role_in.name, tenant_id=role_in.tenant_id
    )
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists for this tenant"
        )
    
    # Create role
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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🎯 === ROLES GET REQUEST START ===")
        logger.info(f"🏢 Tenant param: {tenant}")
        
        if tenant:
            logger.info(f"✅ Fetching roles for tenant: {tenant}")
            roles = crud.role.get_by_tenant(db, tenant_id=tenant)
            logger.info(f"📊 Found {len(roles)} roles for tenant {tenant}")
        else:
            logger.info(f"✅ Fetching all roles")
            roles = crud.role.get_multi(db)
            logger.info(f"📊 Found {len(roles)} total roles")
        
        # Log each role for debugging
        for i, role in enumerate(roles, 1):
            logger.info(f"🔐 Role {i}: name='{role.name}', tenant_id='{role.tenant_id}', active={role.is_active}")
        
        logger.info(f"🎯 === ROLES GET REQUEST END ===")
        return roles
        
    except Exception as e:
        logger.error(f"💥 ROLES GET ERROR: {str(e)}")
        logger.exception("Full traceback:")
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
    
    # Check permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # If not super admin, can only update roles for own tenant
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != role.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update roles for your own tenant"
        )
    
    # Add updated_by field
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
    
    # Check permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # If not super admin, can only delete roles for own tenant
    if current_user.role != UserRole.SUPER_ADMIN and current_user.tenant_id != role.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete roles for your own tenant"
        )
    
    # Soft delete by setting is_active to False
    crud.role.update(db, db_obj=role, obj_in={"is_active": False})
    return {"message": "Role deleted successfully"}