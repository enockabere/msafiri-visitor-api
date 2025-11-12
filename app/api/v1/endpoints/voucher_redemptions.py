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
from app.models.allocation import EventAllocation
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
    db: Session = Depends(get_db)
):
    """Get voucher redemption data for all participants in an event"""
    try:
        print(f"🔍 PARTICIPANT REDEMPTIONS DEBUG: Starting fetch for event_id={event_id}, tenant_id={tenant_id}")
        
        # Verify event exists and belongs to tenant
        event = db.query(Event).filter(
            Event.id == event_id,
            Event.tenant_id == tenant_id
        ).first()
        if not event:
            print(f"❌ PARTICIPANT REDEMPTIONS DEBUG: Event not found for event_id={event_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Event not found")
        
        print(f"✅ PARTICIPANT REDEMPTIONS DEBUG: Found event: {event.title}")
        
        # Get voucher allocation for this event
        voucher_allocation = db.query(EventAllocation).filter(
            EventAllocation.event_id == event_id
        ).first()
        
        vouchers_per_participant = 0
        if voucher_allocation:
            vouchers_per_participant = voucher_allocation.drink_vouchers_per_participant or 0
            print(f"✅ PARTICIPANT REDEMPTIONS DEBUG: Found voucher allocation ID={voucher_allocation.id}, vouchers_per_participant={vouchers_per_participant}")
        else:
            print(f"❌ PARTICIPANT REDEMPTIONS DEBUG: No voucher allocation found for event_id={event_id}")
        
        # Get all participants for this event
        participants_query = db.query(
            EventParticipant.id,
            EventParticipant.full_name,
            EventParticipant.email
        ).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.status.in_(["registered", "selected", "attended"])
        )
        
        participants = participants_query.all()
        print(f"✅ PARTICIPANT REDEMPTIONS DEBUG: Found {len(participants)} participants")
        
        # Get redemption data for each participant
        redemption_data = []
        
        for participant in participants:
            print(f"🔍 PARTICIPANT REDEMPTIONS DEBUG: Processing participant {participant.id} - {participant.full_name}")
            
            # Count total redemptions for this participant using allocation_id
            redemption_count = 0
            last_redemption_date = None
            
            if voucher_allocation:
                redemption_count = db.query(func.sum(ParticipantVoucherRedemption.quantity)).filter(
                    ParticipantVoucherRedemption.allocation_id == voucher_allocation.id,
                    ParticipantVoucherRedemption.participant_id == participant.id
                ).scalar() or 0
                
                print(f"📊 PARTICIPANT REDEMPTIONS DEBUG: Participant {participant.id} has redeemed {redemption_count} vouchers")
                
                # Get last redemption date
                last_redemption = db.query(ParticipantVoucherRedemption).filter(
                    ParticipantVoucherRedemption.allocation_id == voucher_allocation.id,
                    ParticipantVoucherRedemption.participant_id == participant.id
                ).order_by(desc(ParticipantVoucherRedemption.redeemed_at)).first()
                
                last_redemption_date = last_redemption.redeemed_at if last_redemption else None
                if last_redemption_date:
                    print(f"📅 PARTICIPANT REDEMPTIONS DEBUG: Last redemption for participant {participant.id}: {last_redemption_date}")
            
            participant_data = ParticipantRedemptionResponse(
                user_id=participant.id,
                participant_name=participant.full_name or "Unknown",
                participant_email=participant.email,
                allocated_count=vouchers_per_participant,
                redeemed_count=redemption_count,
                last_redemption_date=last_redemption_date
            )
            
            print(f"➕ PARTICIPANT REDEMPTIONS DEBUG: Added participant data: {participant_data.dict()}")
            redemption_data.append(participant_data)
        
        # Sort by redeemed count (highest first) to show over-redemptions at top
        redemption_data.sort(key=lambda x: x.redeemed_count, reverse=True)
        
        print(f"✅ PARTICIPANT REDEMPTIONS DEBUG: Returning {len(redemption_data)} participant redemption records")
        for data in redemption_data:
            print(f"📄 PARTICIPANT REDEMPTIONS DEBUG: {data.participant_name} - Allocated: {data.allocated_count}, Redeemed: {data.redeemed_count}")
        
        return redemption_data
        
    except Exception as e:
        logger.error(f"Error fetching participant redemptions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch redemption data: {str(e)}")

@router.post("/voucher-redemptions/redeem")
async def redeem_voucher(
    redemption_data: VoucherRedemptionCreate,
    event_id: int = Query(...),
    tenant_id: int = Query(...),
    redeemed_by: int = Query(...),
    db: Session = Depends(get_db)
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
            EventParticipant.id == redemption_data.participant_id,
            EventParticipant.status.in_(["registered", "selected", "attended"])
        ).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found or not confirmed for this event")
        
        # Get voucher allocation
        voucher_allocation = db.query(EventAllocation).filter(
            EventAllocation.event_id == event_id
        ).first()
        
        if not voucher_allocation:
            raise HTTPException(status_code=404, detail="No voucher allocation found for this event")
        
        vouchers_per_participant = voucher_allocation.drink_vouchers_per_participant or 0
        
        # Check current redemption count
        current_redemptions = db.query(func.sum(ParticipantVoucherRedemption.quantity)).filter(
            ParticipantVoucherRedemption.allocation_id == voucher_allocation.id,
            ParticipantVoucherRedemption.participant_id == redemption_data.participant_id
        ).scalar() or 0
        
        # Check if redemption would exceed allocation (allow over-redemption but warn)
        remaining_vouchers = vouchers_per_participant - current_redemptions
        is_over_redemption = remaining_vouchers < redemption_data.quantity
        
        # Create redemption record
        for _ in range(redemption_data.quantity):
            voucher_redemption = ParticipantVoucherRedemption(
                allocation_id=voucher_allocation.id,
                participant_id=redemption_data.participant_id,
                quantity=1,
                redeemed_by=str(redeemed_by),
                redeemed_at=datetime.utcnow(),
                notes=f"Location: {redemption_data.location}. Notes: {redemption_data.notes or 'None'}"
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
    db: Session = Depends(get_db)
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
            EventAllocation.event_id == event_id
        ).first()
        
        vouchers_per_participant = 0
        if voucher_allocation:
            vouchers_per_participant = voucher_allocation.drink_vouchers_per_participant or 0
        
        # Count redemptions
        redemption_count = 0
        if voucher_allocation:
            redemption_count = db.query(func.sum(ParticipantVoucherRedemption.quantity)).filter(
                ParticipantVoucherRedemption.allocation_id == voucher_allocation.id,
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