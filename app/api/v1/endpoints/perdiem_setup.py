from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.models.perdiem_setup import PerDiemSetup
from app.api.deps import get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

router = APIRouter()

class PerDiemSetupCreate(BaseModel):
    daily_rate: float
    currency: str = "USD"

class PerDiemSetupUpdate(BaseModel):
    daily_rate: Optional[float] = None
    currency: Optional[str] = None

class PerDiemSetupResponse(BaseModel):
    id: int
    tenant_id: int
    daily_rate: float
    currency: str
    modified_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

def check_finance_admin_role(current_user: User):
    """Check if user has Finance Admin role"""
    # Check primary role
    if current_user.role and current_user.role.value in ['FINANCE_ADMIN', 'finance_admin']:
        return
    
    # Check user_roles relationship
    user_roles = getattr(current_user, 'user_roles', [])
    role_names = [role.role for role in user_roles] if user_roles else []
    
    is_finance_admin = any(role in ['FINANCE_ADMIN', 'finance_admin'] for role in role_names)
    
    if not is_finance_admin:
        raise HTTPException(
            status_code=403, 
            detail="Only Finance Admin users can modify per diem setup"
        )

@router.get("/{tenant_slug}/per-diem-setup", response_model=PerDiemSetupResponse)
def get_perdiem_setup(
    tenant_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get per diem setup for specified tenant"""
    # Use tenant slug from URL path
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    setup = db.query(PerDiemSetup).filter(
        PerDiemSetup.tenant_id == tenant.id
    ).first()
    
    if not setup:
        raise HTTPException(status_code=404, detail="Per diem setup not found")
    
    return setup

@router.post("/{tenant_slug}/per-diem-setup", response_model=PerDiemSetupResponse)
def create_perdiem_setup(
    tenant_slug: str,
    setup_data: PerDiemSetupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create per diem setup for specified tenant"""
    check_finance_admin_role(current_user)
    
    # Use tenant slug from URL path
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Check if setup already exists
    existing_setup = db.query(PerDiemSetup).filter(
        PerDiemSetup.tenant_id == tenant.id
    ).first()
    
    if existing_setup:
        raise HTTPException(status_code=400, detail="Per diem setup already exists")
    
    setup = PerDiemSetup(
        tenant_id=tenant.id,
        daily_rate=Decimal(str(setup_data.daily_rate)),
        currency=setup_data.currency,
        modified_by=current_user.email or current_user.username,
        updated_at=datetime.utcnow()
    )
    
    db.add(setup)
    db.commit()
    db.refresh(setup)
    
    return setup

@router.put("/{tenant_slug}/per-diem-setup/{setup_id}", response_model=PerDiemSetupResponse)
def update_perdiem_setup(
    tenant_slug: str,
    setup_id: int,
    setup_data: PerDiemSetupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update per diem setup"""
    check_finance_admin_role(current_user)
    
    # Use tenant slug from URL path
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    setup = db.query(PerDiemSetup).filter(
        PerDiemSetup.id == setup_id,
        PerDiemSetup.tenant_id == tenant.id
    ).first()
    
    if not setup:
        raise HTTPException(status_code=404, detail="Per diem setup not found")
    
    if setup_data.daily_rate is not None:
        setup.daily_rate = Decimal(str(setup_data.daily_rate))
    if setup_data.currency is not None:
        setup.currency = setup_data.currency

    setup.modified_by = current_user.email or current_user.username
    setup.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(setup)
    
    return setup

@router.delete("/{tenant_slug}/per-diem-setup/{setup_id}")
def delete_perdiem_setup(
    tenant_slug: str,
    setup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete per diem setup"""
    check_finance_admin_role(current_user)
    
    # Use tenant slug from URL path
    tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    setup = db.query(PerDiemSetup).filter(
        PerDiemSetup.id == setup_id,
        PerDiemSetup.tenant_id == tenant.id
    ).first()
    
    if not setup:
        raise HTTPException(status_code=404, detail="Per diem setup not found")
    
    db.delete(setup)
    db.commit()
    
    return {"message": "Per diem setup deleted successfully"}
