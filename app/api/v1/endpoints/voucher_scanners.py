from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.tenant import Tenant
from app.models.event import Event
from app.models.user_roles import UserRole
from app.models.role import Role
from app.schemas.user import UserCreate
from app.crud.user import create_user, get_user_by_email
from app.crud.role import get_role_by_name
from app.crud.user_roles import create_user_role
from pydantic import BaseModel, EmailStr
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class VoucherScannerCreate(BaseModel):
    event_id: int
    email: EmailStr
    name: Optional[str] = None

class VoucherScannerResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    is_active: bool
    created_at: datetime
    created_by: str
    event_id: int

class VoucherScannerStatusUpdate(BaseModel):
    is_active: bool

@router.post("/voucher-scanners", response_model=VoucherScannerResponse)
async def create_voucher_scanner(
    scanner_data: VoucherScannerCreate,
    tenant_id: int = Query(...),
    created_by: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a voucher scanner for an event"""
    try:
        # Verify tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Verify event exists and belongs to tenant
        event = db.query(Event).filter(
            Event.id == scanner_data.event_id,
            Event.tenant_id == tenant_id
        ).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check if user exists
        existing_user = get_user_by_email(db, scanner_data.email)
        
        if not existing_user:
            # Create new user with scanner role
            user_create = UserCreate(
                email=scanner_data.email,
                full_name=scanner_data.name or scanner_data.email,
                password="TempPassword123!",  # Temporary password
                is_active=True
            )
            new_user = create_user(db, user_create)
            user_id = new_user.id
            
            # Get or create voucher_scanner role
            scanner_role = get_role_by_name(db, "voucher_scanner")
            if not scanner_role:
                scanner_role = Role(
                    name="voucher_scanner",
                    description="Can scan and redeem vouchers",
                    tenant_id=tenant_id
                )
                db.add(scanner_role)
                db.commit()
                db.refresh(scanner_role)
            
            # Assign scanner role to user for this tenant
            user_role = create_user_role(db, user_id, scanner_role.id, tenant_id)
            
        else:
            user_id = existing_user.id
            
            # Check if user already has scanner role for this tenant
            scanner_role = get_role_by_name(db, "voucher_scanner")
            if scanner_role:
                existing_role = db.query(UserRole).filter(
                    UserRole.user_id == user_id,
                    UserRole.role_id == scanner_role.id,
                    UserRole.tenant_id == tenant_id
                ).first()
                
                if not existing_role:
                    # Assign scanner role
                    user_role = create_user_role(db, user_id, scanner_role.id, tenant_id)
        
        # Create scanner record (we'll use a simple approach with user_roles table)
        # For now, we'll return the user info as scanner info
        scanner_response = VoucherScannerResponse(
            id=user_id,
            email=scanner_data.email,
            name=scanner_data.name,
            is_active=True,
            created_at=datetime.utcnow(),
            created_by=created_by,
            event_id=scanner_data.event_id
        )
        
        return scanner_response
        
    except Exception as e:
        logger.error(f"Error creating voucher scanner: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create scanner: {str(e)}")

@router.get("/voucher-scanners/event/{event_id}", response_model=List[VoucherScannerResponse])
async def get_event_scanners(
    event_id: int,
    tenant_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all voucher scanners for an event"""
    try:
        # Verify event exists and belongs to tenant
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.tenant_id == tenant_id
        ).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get voucher_scanner role
        scanner_role = get_role_by_name(db, "voucher_scanner")
        if not scanner_role:
            return []
        
        # Get all users with scanner role for this tenant
        scanner_users = db.query(User, UserRole).join(
            UserRole, User.id == UserRole.user_id
        ).filter(
            UserRole.role_id == scanner_role.id,
            UserRole.tenant_id == tenant_id,
            User.is_active == True
        ).all()
        
        scanners = []
        for user, user_role in scanner_users:
            scanner = VoucherScannerResponse(
                id=user.id,
                email=user.email,
                name=user.full_name,
                is_active=user.is_active,
                created_at=user_role.created_at or datetime.utcnow(),
                created_by="admin",  # We don't track this in user_roles
                event_id=event_id
            )
            scanners.append(scanner)
        
        return scanners
        
    except Exception as e:
        logger.error(f"Error fetching event scanners: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch scanners: {str(e)}")

@router.patch("/voucher-scanners/{scanner_id}/toggle-status")
async def toggle_scanner_status(
    scanner_id: int,
    status_update: VoucherScannerStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle scanner active status"""
    try:
        # Get the user (scanner)
        scanner_user = db.query(User).filter(User.id == scanner_id).first()
        if not scanner_user:
            raise HTTPException(status_code=404, detail="Scanner not found")
        
        # Update user active status
        scanner_user.is_active = status_update.is_active
        db.commit()
        
        return {"message": f"Scanner {'activated' if status_update.is_active else 'deactivated'} successfully"}
        
    except Exception as e:
        logger.error(f"Error toggling scanner status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update scanner status: {str(e)}")

@router.delete("/voucher-scanners/{scanner_id}")
async def delete_scanner(
    scanner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a voucher scanner"""
    try:
        # Get the user (scanner)
        scanner_user = db.query(User).filter(User.id == scanner_id).first()
        if not scanner_user:
            raise HTTPException(status_code=404, detail="Scanner not found")
        
        # Get voucher_scanner role
        scanner_role = get_role_by_name(db, "voucher_scanner")
        if scanner_role:
            # Remove scanner role from user
            user_role = db.query(UserRole).filter(
                UserRole.user_id == scanner_id,
                UserRole.role_id == scanner_role.id
            ).first()
            
            if user_role:
                db.delete(user_role)
                db.commit()
        
        return {"message": "Scanner deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting scanner: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete scanner: {str(e)}")