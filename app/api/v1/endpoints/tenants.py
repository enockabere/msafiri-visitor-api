from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole

router = APIRouter()

@router.get("/", response_model=List[schemas.Tenant])
def read_tenants(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Retrieve tenants."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    tenants = crud.tenant.get_multi(db, skip=skip, limit=limit)
    return tenants

@router.post("/", response_model=schemas.Tenant)
def create_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_in: schemas.TenantCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Create new tenant."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    existing_tenant = crud.tenant.get_by_slug(db, slug=tenant_in.slug)
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant with this slug already exists"
        )
    
    tenant = crud.tenant.create(db, obj_in=tenant_in)
    
    # TODO: Send tenant creation notification here
    
    return tenant

@router.post("/activate/{tenant_id}", response_model=schemas.Tenant)
def activate_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Activate a tenant."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant = crud.tenant.get(db, id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    updated_tenant = crud.tenant.update(db, db_obj=tenant, obj_in={"is_active": True})
    
    # TODO: Send tenant activation notification here
    
    return updated_tenant

@router.post("/deactivate/{tenant_id}", response_model=schemas.Tenant)
def deactivate_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Deactivate a tenant."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant = crud.tenant.get(db, id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    updated_tenant = crud.tenant.update(db, db_obj=tenant, obj_in={"is_active": False})
    
    # TODO: Send tenant deactivation notification here
    
    return updated_tenant

@router.get("/{tenant_id}", response_model=schemas.Tenant)
def read_tenant(
    *,
    db: Session = Depends(get_db),
    tenant_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
) -> Any:
    """Get tenant by ID."""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant = crud.tenant.get(db, id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    return tenant