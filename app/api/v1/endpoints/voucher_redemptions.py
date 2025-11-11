from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.tenant import Tenant
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.participant_voucher_redemption import ParticipantVoucherRedemption
from app.models.event_allocation import EventAllocation
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ParticipantRedemptionResponse(BaseModel):
    user_id: int
    participant_name: str
    participant_email: str
    allocated_count: int
    redeemed_count: int
    last_redemption_date: Optional[datetime]

class VoucherRedemptionCreate(BaseModel):
    participant_id: int
    quantity: int = 1
    location: Optional[str] = None
    notes: Optional[str] = None

@router.get("/voucher-redemptions/event/{event_id}/participants", response_model=List[ParticipantRedemptionResponse])
async def get_participant_redemptions(
    event_id: int,
    tenant_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get voucher redemption data for all participants in an event"""
    try:
        # Verify event exists and belongs to tenant
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.tenant_id == tenant_id
        ).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get voucher allocation for this event
        voucher_allocation = db.query(EventAllocation).filter(
            EventAllocation.event_id == event_id,
            EventAllocation.allocation_type == "vouchers"
        ).first()
        
        vouchers_per_participant = 0
        if voucher_allocation and voucher_allocation.details:
            vouchers_per_participant = voucher_allocation.details.get("drink_vouchers_per_participant", 0)
        
        # Get all participants for this event
        participants_query = db.query(
            EventParticipant.user_id,
            User.full_name,
            User.email
        ).join(
            User, EventParticipant.user_id == User.id
        ).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.status == "confirmed"
        )
        
        participants = participants_query.all()
        
        # Get redemption data for each participant
        redemption_data = []
        
        for participant in participants:
            # Count total redemptions for this participant
            redemption_count = db.query(func.count(ParticipantVoucherRedemption.id)).filter(
                ParticipantVoucherRedemption.event_id == event_id,
                ParticipantVoucherRedemption.participant_id == participant.user_id
            ).scalar() or 0
            
            # Get last redemption date
            last_redemption = db.query(ParticipantVoucherRedemption).filter(
                ParticipantVoucherRedemption.event_id == event_id,
                ParticipantVoucherRedemption.participant_id == participant.user_id
            ).order_by(desc(ParticipantVoucherRedemption.redeemed_at)).first()
            
            last_redemption_date = last_redemption.redeemed_at if last_redemption else None
            
            participant_data = ParticipantRedemptionResponse(
                user_id=participant.user_id,
                participant_name=participant.full_name or "Unknown",
                participant_email=participant.email,
                allocated_count=vouchers_per_participant,
                redeemed_count=redemption_count,
                last_redemption_date=last_redemption_date
            )
            
            redemption_data.append(participant_data)
        
        # Sort by redeemed count (highest first) to show over-redemptions at top
        redemption_data.sort(key=lambda x: x.redeemed_count, reverse=True)
        
        return redemption_data
        
    except Exception as e:
        logger.error(f"Error fetching participant redemptions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch redemption data: {str(e)}")

@router.post("/voucher-redemptions/redeem")
async def redeem_voucher(
    redemption_data: VoucherRedemptionCreate,
    event_id: int = Query(...),
    tenant_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Redeem voucher for a participant (used by scanner app)"""
    try:
        # Verify event exists and belongs to tenant
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.tenant_id == tenant_id
        ).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Verify participant exists and is registered for event
        participant = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == redemption_data.participant_id,
            EventParticipant.status == "confirmed"
        ).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found or not confirmed for this event")
        
        # Get voucher allocation
        voucher_allocation = db.query(EventAllocation).filter(
            EventAllocation.event_id == event_id,
            EventAllocation.allocation_type == "vouchers"
        ).first()
        
        if not voucher_allocation:
            raise HTTPException(status_code=404, detail="No voucher allocation found for this event")
        
        vouchers_per_participant = voucher_allocation.details.get("drink_vouchers_per_participant", 0)
        
        # Check current redemption count
        current_redemptions = db.query(func.count(ParticipantVoucherRedemption.id)).filter(
            ParticipantVoucherRedemption.event_id == event_id,
            ParticipantVoucherRedemption.participant_id == redemption_data.participant_id
        ).scalar() or 0
        
        # Check if redemption would exceed allocation (allow over-redemption but warn)
        remaining_vouchers = vouchers_per_participant - current_redemptions
        is_over_redemption = remaining_vouchers < redemption_data.quantity
        
        # Create redemption record
        for _ in range(redemption_data.quantity):
            voucher_redemption = ParticipantVoucherRedemption(
                event_id=event_id,
                participant_id=redemption_data.participant_id,
                redeemed_by=current_user.id,
                redeemed_at=datetime.utcnow(),
                location=redemption_data.location,
                notes=redemption_data.notes
            )
            db.add(voucher_redemption)
        
        db.commit()
        
        response_data = {
            "message": "Voucher redeemed successfully",
            "participant_id": redemption_data.participant_id,
            "quantity_redeemed": redemption_data.quantity,
            "total_redeemed": current_redemptions + redemption_data.quantity,
            "allocated_vouchers": vouchers_per_participant,
            "remaining_vouchers": max(0, vouchers_per_participant - (current_redemptions + redemption_data.quantity)),
            "is_over_redemption": is_over_redemption
        }
        
        if is_over_redemption:
            response_data["warning"] = "This redemption exceeds the participant's allocation"
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error redeeming voucher: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to redeem voucher: {str(e)}")

@router.get("/voucher-redemptions/participant/{participant_id}/balance")
async def get_participant_voucher_balance(
    participant_id: int,
    event_id: int = Query(...),
    tenant_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get voucher balance for a specific participant"""
    try:
        # Verify event exists and belongs to tenant
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.tenant_id == tenant_id
        ).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get voucher allocation
        voucher_allocation = db.query(EventAllocation).filter(
            EventAllocation.event_id == event_id,
            EventAllocation.allocation_type == "vouchers"
        ).first()
        
        vouchers_per_participant = 0
        if voucher_allocation and voucher_allocation.details:
            vouchers_per_participant = voucher_allocation.details.get("drink_vouchers_per_participant", 0)
        
        # Count redemptions
        redemption_count = db.query(func.count(ParticipantVoucherRedemption.id)).filter(
            ParticipantVoucherRedemption.event_id == event_id,
            ParticipantVoucherRedemption.participant_id == participant_id
        ).scalar() or 0
        
        # Get participant info
        participant = db.query(User).filter(User.id == participant_id).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        balance = vouchers_per_participant - redemption_count
        
        return {
            "participant_id": participant_id,
            "participant_name": participant.full_name,
            "participant_email": participant.email,
            "allocated_vouchers": vouchers_per_participant,
            "redeemed_vouchers": redemption_count,
            "remaining_vouchers": max(0, balance),
            "is_over_redeemed": balance < 0,
            "over_redemption_count": abs(balance) if balance < 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error fetching participant balance: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch balance: {str(e)}")