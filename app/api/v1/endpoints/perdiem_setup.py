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
    
    class Config:
        from_attributes = True

@router.get("/per-diem-setup", response_model=PerDiemSetupResponse)
def get_perdiem_setup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get per diem setup for current tenant"""
    # Get tenant ID from tenant_id (which might be a slug)
    tenant_id = current_user.tenant_id
    
    # If tenant_id is a string (slug), resolve it to numeric ID
    if isinstance(tenant_id, str) and not tenant_id.isdigit():
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        tenant_id = tenant.id
    
    setup = db.query(PerDiemSetup).filter(
        PerDiemSetup.tenant_id == tenant_id
    ).first()
    
    if not setup:
        raise HTTPException(status_code=404, detail="Per diem setup not found")
    
    return setup

@router.post("/per-diem-setup", response_model=PerDiemSetupResponse)
def create_perdiem_setup(
    setup_data: PerDiemSetupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create per diem setup for current tenant"""
    # Get tenant ID from tenant_id (which might be a slug)
    tenant_id = current_user.tenant_id
    
    # If tenant_id is a string (slug), resolve it to numeric ID
    if isinstance(tenant_id, str) and not tenant_id.isdigit():
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        tenant_id = tenant.id
    
    # Check if setup already exists
    existing_setup = db.query(PerDiemSetup).filter(
        PerDiemSetup.tenant_id == tenant_id
    ).first()
    
    if existing_setup:
        raise HTTPException(status_code=400, detail="Per diem setup already exists")
    
    setup = PerDiemSetup(
        tenant_id=tenant_id,
        daily_rate=Decimal(str(setup_data.daily_rate)),
        currency=setup_data.currency
    )
    
    db.add(setup)
    db.commit()
    db.refresh(setup)
    
    return setup

@router.put("/per-diem-setup/{setup_id}", response_model=PerDiemSetupResponse)
def update_perdiem_setup(
    setup_id: int,
    setup_data: PerDiemSetupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update per diem setup"""
    # Get tenant ID from tenant_id (which might be a slug)
    tenant_id = current_user.tenant_id
    
    # If tenant_id is a string (slug), resolve it to numeric ID
    if isinstance(tenant_id, str) and not tenant_id.isdigit():
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        tenant_id = tenant.id
    
    setup = db.query(PerDiemSetup).filter(
        PerDiemSetup.id == setup_id,
        PerDiemSetup.tenant_id == tenant_id
    ).first()
    
    if not setup:
        raise HTTPException(status_code=404, detail="Per diem setup not found")
    
    if setup_data.daily_rate is not None:
        setup.daily_rate = Decimal(str(setup_data.daily_rate))
    if setup_data.currency is not None:
        setup.currency = setup_data.currency
    
    db.commit()
    db.refresh(setup)
    
    return setup

@router.delete("/per-diem-setup/{setup_id}")
def delete_perdiem_setup(
    setup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete per diem setup"""
    # Get tenant ID from tenant_id (which might be a slug)
    tenant_id = current_user.tenant_id
    
    # If tenant_id is a string (slug), resolve it to numeric ID
    if isinstance(tenant_id, str) and not tenant_id.isdigit():
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        tenant_id = tenant.id
    
    setup = db.query(PerDiemSetup).filter(
        PerDiemSetup.id == setup_id,
        PerDiemSetup.tenant_id == tenant_id
    ).first()
    
    if not setup:
        raise HTTPException(status_code=404, detail="Per diem setup not found")
    
    db.delete(setup)
    db.commit()
    
    return {"message": "Per diem setup deleted successfully"}