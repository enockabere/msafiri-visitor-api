from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.db.database import get_db
from app.models.user import User
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.allocation import EventAllocation
from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
from app.models.user_roles import UserRole
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ParticipantVoucherInfo(BaseModel):
    participant_id: int
    participant_name: str
    participant_email: str
    allocated_vouchers: int
    redeemed_vouchers: int
    remaining_vouchers: int

class ScannerEventInfo(BaseModel):
    event_id: int
    event_name: str
    event_description: Optional[str]
    start_date: datetime
    end_date: datetime
    participants: List[ParticipantVoucherInfo]

# Removed duplicate /scanner/events endpoint - now handled by scanner.py

@router.post("/scanner/redeem-voucher")
async def redeem_voucher_scan(
    participant_id: int = Query(...),
    scanner_email: str = Query(...),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Redeem a voucher via QR scan"""
    try:
        # Get scanner user
        scanner = db.query(User).filter(User.email == scanner_email).first()
        if not scanner:
            raise HTTPException(status_code=404, detail="Scanner not found")
        
        # Verify scanner has voucher scanner role
        scanner_role = db.query(UserRole).filter(
            UserRole.user_id == scanner.id,
            UserRole.role == 'VOUCHER_SCANNER'
        ).first()
        
        if not scanner_role:
            raise HTTPException(status_code=403, detail="User is not authorized as voucher scanner")
        
        # Get participant
        participant = db.query(EventParticipant).filter(
            EventParticipant.id == participant_id
        ).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        # Get event from participant
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get voucher allocation for this event
        allocation = db.query(EventAllocation).filter(
            EventAllocation.event_id == event.id
        ).first()
        
        if not allocation:
            raise HTTPException(status_code=404, detail="No voucher allocation found for event")
        
        vouchers_per_participant = allocation.drink_vouchers_per_participant or 0
        
        # Check remaining vouchers
        total_redeemed = db.query(func.count(ParticipantVoucherRedemption.id)).filter(
            ParticipantVoucherRedemption.allocation_id == allocation.id,
            ParticipantVoucherRedemption.participant_id == participant_id
        ).scalar() or 0
        
        remaining = vouchers_per_participant - total_redeemed
        
        if remaining <= 0:
            raise HTTPException(status_code=400, detail="No vouchers remaining for this participant")
        
        # Get scanner user ID
        scanner_user = db.query(User).filter(User.email == scanner_email).first()
        if not scanner_user:
            raise HTTPException(status_code=404, detail="Scanner user not found")
        
        # Create redemption record
        redemption = ParticipantVoucherRedemption(
            allocation_id=allocation.id,
            participant_id=participant_id,
            quantity=1,
            redeemed_at=datetime.utcnow(),
            redeemed_by=scanner_email,
            notes=notes
        )
        
        db.add(redemption)
        db.commit()
        db.refresh(redemption)
        
        # Return updated voucher info
        new_total_redeemed = total_redeemed + 1
        new_remaining = vouchers_per_participant - new_total_redeemed
        
        return {
            "success": True,
            "message": "Voucher redeemed successfully",
            "participant_name": participant.full_name,
            "allocated_vouchers": vouchers_per_participant,
            "redeemed_vouchers": new_total_redeemed,
            "remaining_vouchers": new_remaining,
            "redemption_id": redemption.id
        }
        
    except Exception as e:
        logger.error(f"Error redeeming voucher: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to redeem voucher: {str(e)}")