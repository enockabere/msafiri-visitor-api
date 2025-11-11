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
            logger.error(f"User not found: {user_email}")
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"Found user: {user.id} - {user.email}")
        
        # Check if user has voucher scanner role
        scanner_role = db.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.role == RoleType.VOUCHER_SCANNER,
            UserRole.is_active == True
        ).first()
        
        logger.info(f"Scanner role check: {scanner_role is not None}")
        
        if not scanner_role:
            logger.warning(f"User {user_email} does not have voucher scanner role")
            return []
        
        # Get all events with voucher allocations
        events_with_allocations = db.query(Event).join(
            EventAllocation, Event.id == EventAllocation.event_id
        ).filter(
            EventAllocation.drink_vouchers_per_participant > 0
        ).distinct().all()
        
        logger.info(f"Found {len(events_with_allocations)} events with voucher allocations")
        
        scanner_events = []
        
        for event in events_with_allocations:
            # Get voucher allocation for this event
            voucher_allocation = db.query(EventAllocation).filter(
                EventAllocation.event_id == event.id
            ).first()
            
            if not voucher_allocation:
                continue
                
            vouchers_per_participant = voucher_allocation.drink_vouchers_per_participant or 0
            
            # Get all participants for this event (check all statuses first)
            all_participants = db.query(EventParticipant).filter(
                EventParticipant.event_id == event.id
            ).all()
            
            # Log all participant statuses for debugging
            if all_participants:
                statuses = [p.status for p in all_participants]
                logger.info(f"Event {event.id}: All participant statuses: {set(statuses)}")
            
            # Get participants with common statuses including confirmed
            participants = db.query(EventParticipant).filter(
                EventParticipant.event_id == event.id,
                EventParticipant.status.in_(["registered", "selected", "attended", "confirmed"])
            ).all()
            
            logger.info(f"Event {event.id} ({event.title}): Found {len(participants)} participants (out of {len(all_participants)} total)")
            
            participants_info = []
            
            for participant in participants:
                # Get total redeemed vouchers for this participant via allocation_id
                total_redeemed = db.query(func.count(ParticipantVoucherRedemption.id)).filter(
                    ParticipantVoucherRedemption.allocation_id == voucher_allocation.id,
                    ParticipantVoucherRedemption.participant_id == participant.id
                ).scalar() or 0
                
                remaining = max(0, vouchers_per_participant - total_redeemed)
                
                participant_info = ParticipantVoucherInfo(
                    participant_id=participant.id,
                    participant_name=participant.full_name,
                    participant_email=participant.email,
                    allocated_vouchers=vouchers_per_participant,
                    redeemed_vouchers=total_redeemed,
                    remaining_vouchers=remaining
                )
                participants_info.append(participant_info)
            
            if participants_info:  # Only include events with participants
                event_info = ScannerEventInfo(
                    event_id=event.id,
                    event_name=event.title,
                    event_description=event.description,
                    start_date=event.start_date,
                    end_date=event.end_date,
                    participants=participants_info
                )
                scanner_events.append(event_info)
                logger.info(f"Added event {event.id} with {len(participants_info)} participants")
            else:
                logger.info(f"Skipped event {event.id} - no participants found")
        
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