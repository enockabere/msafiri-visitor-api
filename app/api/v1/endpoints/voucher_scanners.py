from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.tenant import Tenant
from app.models.event import Event
from app.models.user_roles import UserRole, RoleType
from app.models.role import Role
from app.schemas.user import UserCreate
# Direct database operations - no CRUD imports needed
from pydantic import BaseModel, EmailStr
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class VoucherScannerCreate(BaseModel):
    event_id: int
    emails: List[EmailStr]  # Support multiple emails
    
class SingleScannerCreate(BaseModel):
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

@router.post("/voucher-scanners/bulk", response_model=List[VoucherScannerResponse])
async def create_voucher_scanners_bulk(
    scanner_data: VoucherScannerCreate,
    tenant_id: int = Query(...),
    created_by: str = Query(...),
    db: Session = Depends(get_db)
):
    """Create multiple voucher scanners for an event"""
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
        
        # Get voucher_scanner role
        scanner_role = db.query(Role).filter(Role.name == "voucher_scanner").first()
        if not scanner_role:
            raise HTTPException(status_code=404, detail="Scanner role not found")
        
        created_scanners = []
        
        for email in scanner_data.emails:
            try:
                # Check if user exists
                existing_user = db.query(User).filter(User.email == email).first()
                
                if not existing_user:
                    # Create new user with scanner role
                    from app.core.security import get_password_hash
                    
                    new_user = User(
                        email=email,
                        full_name=email.split('@')[0],  # Use email prefix as name
                        hashed_password=get_password_hash("TempPassword123!"),
                        is_active=True
                    )
                    db.add(new_user)
                    db.commit()
                    db.refresh(new_user)
                    user_id = new_user.id
                    user_name = new_user.full_name
                    is_new_user = True
                else:
                    user_id = existing_user.id
                    user_name = existing_user.full_name
                    is_new_user = False
                
                # Check if user already has scanner role
                existing_role = db.query(UserRole).filter(
                    UserRole.user_id == user_id,
                    UserRole.role == RoleType.VOUCHER_SCANNER
                ).first()
                
                if not existing_role:
                    # Assign scanner role (additional role for existing users)
                    from datetime import datetime
                    user_role = UserRole(
                        user_id=user_id,
                        role=RoleType.VOUCHER_SCANNER,
                        granted_by=created_by,
                        granted_at=datetime.utcnow()
                    )
                    db.add(user_role)
                    db.commit()
                
                # Create event-specific scanner record
                from sqlalchemy import text
                try:
                    # Insert into event_voucher_scanners table to track event-specific assignments
                    db.execute(text("""
                        INSERT INTO event_voucher_scanners (user_id, event_id, tenant_id, created_by, created_at, is_active)
                        VALUES (:user_id, :event_id, :tenant_id, :created_by, :created_at, :is_active)
                        ON CONFLICT (user_id, event_id) DO NOTHING
                    """), {
                        "user_id": user_id,
                        "event_id": scanner_data.event_id,
                        "tenant_id": tenant_id,
                        "created_by": created_by,
                        "created_at": datetime.utcnow(),
                        "is_active": True
                    })
                    db.commit()
                except Exception as table_error:
                    logger.warning(f"Event-specific scanner table not available: {str(table_error)}")
                    # Continue without event-specific tracking for now
                
                # Send email notification
                try:
                    from app.core.email_service import email_service
                    
                    scanner_url = f"http://41.90.97.253:3000/scanner?event_id={scanner_data.event_id}&tenant_id={tenant_id}"
                    
                    if is_new_user:
                        message = f"""
Hello {user_name},

You have been assigned as a voucher scanner for an MSF event.

Your scanner credentials:
• Email: {email}
• Temporary Password: TempPassword123!

To start scanning vouchers:
1. Visit: {scanner_url}
2. Login with your credentials
3. Start scanning participant vouchers

Please change your password after first login for security.

Best regards,
MSF Kenya Team
                        """
                    else:
                        message = f"""
Hello {user_name},

You have been assigned as a voucher scanner for an MSF event.

You can now access the voucher scanner with your existing account:
• Email: {email}
• Use your current password

To start scanning vouchers:
1. Visit: {scanner_url}
2. Login with your existing credentials
3. Start scanning participant vouchers

Best regards,
MSF Kenya Team
                        """
                    
                    email_service.send_notification_email(
                        to_email=email,
                        user_name=user_name,
                        title="MSafiri Voucher Scanner Access",
                        message=message
                    )
                    logger.info(f"Scanner notification email sent to {email}")
                except Exception as e:
                    logger.error(f"Failed to send scanner notification email to {email}: {str(e)}")
                
                # Add to response list
                scanner_response = VoucherScannerResponse(
                    id=user_id,
                    email=email,
                    name=user_name,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    created_by=created_by,
                    event_id=scanner_data.event_id
                )
                created_scanners.append(scanner_response)
                
            except Exception as e:
                logger.error(f"Error processing scanner {email}: {str(e)}")
                # Continue with other emails
                continue
        
        return created_scanners
        
    except Exception as e:
        logger.error(f"Error creating voucher scanners: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create scanners: {str(e)}")

@router.post("/voucher-scanners", response_model=VoucherScannerResponse)
async def create_voucher_scanner(
    scanner_data: SingleScannerCreate,
    tenant_id: int = Query(...),
    created_by: str = Query(...),
    db: Session = Depends(get_db)
):
    """Create a single voucher scanner for an event"""
    # Use bulk endpoint with single email
    bulk_data = VoucherScannerCreate(
        event_id=scanner_data.event_id,
        emails=[scanner_data.email]
    )
    
    result = await create_voucher_scanners_bulk(
        bulk_data, tenant_id, created_by, db
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create scanner")
    
    return result[0]

@router.get("/voucher-scanners/event/{event_id}", response_model=List[VoucherScannerResponse])
async def get_event_scanners(
    event_id: int,
    tenant_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Get voucher scanners specifically created for this event"""
    try:
        # Verify event exists and belongs to tenant
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.tenant_id == tenant_id
        ).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Create event_voucher_scanners table if it doesn't exist to track event-specific scanners
        from sqlalchemy import text
        try:
            # Check if we have event-specific scanner tracking
            result = db.execute(text("""
                SELECT u.id, u.email, u.full_name, u.is_active, u.created_at, evs.created_by, evs.event_id
                FROM users u
                JOIN event_voucher_scanners evs ON u.id = evs.user_id
                WHERE evs.event_id = :event_id AND evs.tenant_id = :tenant_id
            """), {"event_id": event_id, "tenant_id": tenant_id})
            
            scanners = []
            for row in result:
                scanner = VoucherScannerResponse(
                    id=row.id,
                    email=row.email,
                    name=row.full_name,
                    is_active=row.is_active,
                    created_at=row.created_at or datetime.utcnow(),
                    created_by=row.created_by or "admin",
                    event_id=row.event_id
                )
                scanners.append(scanner)
            
            return scanners
            
        except Exception as table_error:
            logger.warning(f"Event-specific scanner table not found, falling back to role-based lookup: {str(table_error)}")
            # Fallback: return empty list since we want event-specific scanners only
            return []
        
    except Exception as e:
        logger.error(f"Error fetching event scanners: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch scanners: {str(e)}")

@router.patch("/voucher-scanners/{scanner_id}/toggle-status")
async def toggle_scanner_status(
    scanner_id: int,
    status_update: VoucherScannerStatusUpdate,
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
):
    """Delete a voucher scanner"""
    try:
        # Get the user (scanner)
        scanner_user = db.query(User).filter(User.id == scanner_id).first()
        if not scanner_user:
            raise HTTPException(status_code=404, detail="Scanner not found")
        
        # Get voucher_scanner role
        scanner_role = db.query(Role).filter(Role.name == "voucher_scanner").first()
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