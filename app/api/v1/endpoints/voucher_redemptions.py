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

@router.get("/voucher-redemptions/debug/{event_id}")
async def debug_voucher_data(
    event_id: int,
    tenant_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check voucher data"""
    try:
        # Get event allocation
        allocation = db.query(EventAllocation).filter(
            EventAllocation.event_id == event_id
        ).first()
        
        # Get all participants for this event
        participants = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id
        ).all()
        
        # Get all redemptions for this allocation
        redemptions = []
        if allocation:
            redemptions = db.query(ParticipantVoucherRedemption).filter(
                ParticipantVoucherRedemption.allocation_id == allocation.id
            ).all()
        
        return {
            "event_id": event_id,
            "allocation": {
                "id": allocation.id if allocation else None,
                "vouchers_per_participant": allocation.drink_vouchers_per_participant if allocation else None
            } if allocation else None,
            "participants": [
                {
                    "id": p.id,
                    "name": p.full_name,
                    "email": p.email,
                    "status": p.status
                } for p in participants
            ],
            "redemptions": [
                {
                    "id": r.id,
                    "allocation_id": r.allocation_id,
                    "participant_id": r.participant_id,
                    "quantity": r.quantity,
                    "redeemed_at": r.redeemed_at.isoformat() if r.redeemed_at else None
                } for r in redemptions
            ]
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/voucher-redemptions/test")
async def test_voucher_endpoint():
    """Test endpoint to verify voucher redemptions router is working"""
    logger.info("🚨 VOUCHER TEST ENDPOINT HIT")
    print("🚨 VOUCHER TEST ENDPOINT HIT")
    return {"message": "Voucher redemptions router is working", "status": "ok"}

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
    # Force logging to appear in gunicorn logs
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    logger.info(f"🚨 VOUCHER REDEMPTIONS ENDPOINT HIT: event_id={event_id}, tenant_id={tenant_id}")
    print(f"🚨 VOUCHER REDEMPTIONS ENDPOINT HIT: event_id={event_id}, tenant_id={tenant_id}", flush=True)
    
    # Also write to stderr to ensure it appears
    import sys
    sys.stderr.write(f"🚨 VOUCHER REDEMPTIONS ENDPOINT HIT: event_id={event_id}, tenant_id={tenant_id}\n")
    sys.stderr.flush()
    try:
        print(f"🔍 PARTICIPANT REDEMPTIONS DEBUG: Starting fetch for event_id={event_id}, tenant_id={tenant_id}", flush=True)
        sys.stderr.write(f"🔍 PARTICIPANT REDEMPTIONS DEBUG: Starting fetch for event_id={event_id}, tenant_id={tenant_id}\n")
        sys.stderr.flush()
        
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
        
        # Get all participants for this event - UPDATED STATUS FILTER
        participants_query = db.query(
            EventParticipant.id,
            EventParticipant.full_name,
            EventParticipant.email
        ).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.status.in_(["confirmed", "registered", "selected", "attended"])
        )
        
        participants = participants_query.all()
        print(f"✅ PARTICIPANT REDEMPTIONS DEBUG: Found {len(participants)} participants")
        
        # Get redemption data for each participant
        redemption_data = []
        
        for participant in participants:
            print(f"🔍 PARTICIPANT REDEMPTIONS DEBUG: Processing participant {participant.id} - {participant.full_name}", flush=True)
            
            # Count total redemptions for this participant using allocation_id
            redemption_count = 0
            last_redemption_date = None
            
            if voucher_allocation:
                redemption_count = db.query(func.sum(ParticipantVoucherRedemption.quantity)).filter(
                    ParticipantVoucherRedemption.allocation_id == voucher_allocation.id,
                    ParticipantVoucherRedemption.participant_id == participant.id
                ).scalar() or 0
                
                print(f"📊 PARTICIPANT REDEMPTIONS DEBUG: Participant {participant.id} has redeemed {redemption_count} vouchers", flush=True)
                
                # Get last redemption date
                last_redemption = db.query(ParticipantVoucherRedemption).filter(
                    ParticipantVoucherRedemption.allocation_id == voucher_allocation.id,
                    ParticipantVoucherRedemption.participant_id == participant.id
                ).order_by(desc(ParticipantVoucherRedemption.redeemed_at)).first()
                
                last_redemption_date = last_redemption.redeemed_at if last_redemption else None
                if last_redemption_date:
                    print(f"📅 PARTICIPANT REDEMPTIONS DEBUG: Last redemption for participant {participant.id}: {last_redemption_date}", flush=True)
            
            # ONLY INCLUDE PARTICIPANTS WITH REDEMPTIONS
            if redemption_count > 0:
                participant_data = ParticipantRedemptionResponse(
                    user_id=participant.id,
                    participant_name=participant.full_name or "Unknown",
                    participant_email=participant.email,
                    allocated_count=vouchers_per_participant,
                    redeemed_count=redemption_count,
                    last_redemption_date=last_redemption_date
                )
                
                print(f"➕ PARTICIPANT REDEMPTIONS DEBUG: Added participant data: {participant_data.dict()}", flush=True)
                redemption_data.append(participant_data)
            else:
                print(f"⏭️ PARTICIPANT REDEMPTIONS DEBUG: Skipped participant {participant.id} - no redemptions", flush=True)
        
        # Sort by redeemed count (highest first) to show over-redemptions at top
        redemption_data.sort(key=lambda x: x.redeemed_count, reverse=True)
        
        print(f"✅ PARTICIPANT REDEMPTIONS DEBUG: Returning {len(redemption_data)} participant redemption records", flush=True)
        for data in redemption_data:
            print(f"📄 PARTICIPANT REDEMPTIONS DEBUG: {data.participant_name} - Allocated: {data.allocated_count}, Redeemed: {data.redeemed_count}", flush=True)
        
        return redemption_data
        
    except Exception as e:
        logger.error(f"❌ VOUCHER REDEMPTIONS ERROR: {str(e)}")
        print(f"❌ VOUCHER REDEMPTIONS ERROR: {str(e)}")
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