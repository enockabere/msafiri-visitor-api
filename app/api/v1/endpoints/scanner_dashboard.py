from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.models.user import User
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.event_allocation import EventAllocation
from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
from app.models.user_roles import UserRole, RoleType
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

@router.get("/scanner/events", response_model=List[ScannerEventInfo])
async def get_scanner_events(
    user_email: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get events where user is assigned as voucher scanner"""
    try:
        # Get user
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user has voucher scanner role
        scanner_role = db.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.role == RoleType.VOUCHER_SCANNER,
            UserRole.is_active == True
        ).first()
        
        if not scanner_role:
            return []
        
        # Get all events with allocations (voucher events)
        events_with_allocations = db.query(Event).join(
            EventAllocation, Event.id == EventAllocation.event_id
        ).filter(
            EventAllocation.allocation_type == "voucher"
        ).distinct().all()
        
        scanner_events = []
        
        for event in events_with_allocations:
            # Get all participants for this event with voucher allocations
            participants_query = db.query(
                EventParticipant,
                EventAllocation
            ).join(
                EventAllocation, 
                EventParticipant.id == EventAllocation.participant_id
            ).filter(
                EventAllocation.event_id == event.id,
                EventAllocation.allocation_type == "voucher"
            ).all()
            
            participants_info = []
            
            for participant, allocation in participants_query:
                # Get total redeemed vouchers for this participant
                total_redeemed = db.query(ParticipantVoucherRedemption).filter(
                    ParticipantVoucherRedemption.allocation_id == allocation.id
                ).count()
                
                remaining = max(0, allocation.quantity - total_redeemed)
                
                participant_info = ParticipantVoucherInfo(
                    participant_id=participant.id,
                    participant_name=participant.full_name,
                    participant_email=participant.email,
                    allocated_vouchers=allocation.quantity,
                    redeemed_vouchers=total_redeemed,
                    remaining_vouchers=remaining
                )
                participants_info.append(participant_info)
            
            if participants_info:  # Only include events with participants
                event_info = ScannerEventInfo(
                    event_id=event.id,
                    event_name=event.name,
                    event_description=event.description,
                    start_date=event.start_date,
                    end_date=event.end_date,
                    participants=participants_info
                )
                scanner_events.append(event_info)
        
        return scanner_events
        
    except Exception as e:
        logger.error(f"Error fetching scanner events: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch scanner events: {str(e)}")

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
            UserRole.role == RoleType.VOUCHER_SCANNER,
            UserRole.is_active == True
        ).first()
        
        if not scanner_role:
            raise HTTPException(status_code=403, detail="User is not authorized as voucher scanner")
        
        # Get participant
        participant = db.query(EventParticipant).filter(
            EventParticipant.id == participant_id
        ).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        # Get participant's voucher allocation
        allocation = db.query(EventAllocation).filter(
            EventAllocation.participant_id == participant_id,
            EventAllocation.allocation_type == "voucher"
        ).first()
        
        if not allocation:
            raise HTTPException(status_code=404, detail="No voucher allocation found for participant")
        
        # Check remaining vouchers
        total_redeemed = db.query(ParticipantVoucherRedemption).filter(
            ParticipantVoucherRedemption.allocation_id == allocation.id
        ).count()
        
        remaining = allocation.quantity - total_redeemed
        
        if remaining <= 0:
            raise HTTPException(status_code=400, detail="No vouchers remaining for this participant")
        
        # Create redemption record
        redemption = ParticipantVoucherRedemption(
            allocation_id=allocation.id,
            participant_id=participant_id,
            quantity=1,  # Redeem one voucher at a time
            redeemed_at=datetime.utcnow(),
            redeemed_by=scanner_email,
            notes=notes
        )
        
        db.add(redemption)
        db.commit()
        db.refresh(redemption)
        
        # Return updated voucher info
        new_total_redeemed = total_redeemed + 1
        new_remaining = allocation.quantity - new_total_redeemed
        
        return {
            "success": True,
            "message": "Voucher redeemed successfully",
            "participant_name": participant.full_name,
            "allocated_vouchers": allocation.quantity,
            "redeemed_vouchers": new_total_redeemed,
            "remaining_vouchers": new_remaining,
            "redemption_id": redemption.id
        }
        
    except Exception as e:
        logger.error(f"Error redeeming voucher: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to redeem voucher: {str(e)}")