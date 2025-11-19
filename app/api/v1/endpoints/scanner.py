from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List
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
    event_description: str = None
    start_date: datetime
    end_date: datetime
    participants: List[ParticipantVoucherInfo]

class VoucherRedeemRequest(BaseModel):
    participant_id: int
    scanner_email: str
    notes: str = None

@router.get("/scanner/events", response_model=List[ScannerEventInfo])
async def get_scanner_events(
    user_email: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get events where user is assigned as voucher scanner"""
    try:
        logger.info(f"🔍 GET SCANNER EVENTS for user: {user_email}")
        
        # Get user
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user has voucher scanner role
        has_scanner_role = db.query(UserRole).filter(
            UserRole.user_id == user.id,
            UserRole.role == RoleType.VOUCHER_SCANNER
        ).first()
        
        if not has_scanner_role:
            logger.info(f"❌ User {user_email} does not have voucher scanner role")
            return []
        
        # Get events where user is assigned as scanner
        try:
            # Try event-specific scanner assignments first
            result = db.execute(text("""
                SELECT DISTINCT e.id, e.title, e.description, e.start_date, e.end_date, e.tenant_id
                FROM events e
                JOIN event_voucher_scanners evs ON e.id = evs.event_id
                WHERE evs.user_id = :user_id AND evs.is_active = true
            """), {"user_id": user.id})
            
            event_rows = result.fetchall()
            logger.info(f"📊 Found {len(event_rows)} events with specific scanner assignments")
            
        except Exception as table_error:
            logger.warning(f"Event-specific scanner table not available: {str(table_error)}")
            # Fallback: get all events from user's tenant
            event_rows = db.query(Event).filter(
                Event.tenant_id == user.tenant_id if hasattr(user, 'tenant_id') else True
            ).all()
            event_rows = [(e.id, e.title, e.description, e.start_date, e.end_date, e.tenant_id) for e in event_rows]
        
        scanner_events = []
        
        for event_row in event_rows:
            event_id = event_row[0]
            event_name = event_row[1]
            event_description = event_row[2]
            start_date = event_row[3]
            end_date = event_row[4]
            
            # Get voucher allocation for this event
            all_allocations = db.query(EventAllocation).filter(
                EventAllocation.event_id == event_id
            ).all()
            logger.info(f"📊 Event {event_id} has {len(all_allocations)} total allocations")
            for alloc in all_allocations:
                logger.info(f"📊 Allocation {alloc.id}: drink_vouchers={alloc.drink_vouchers_per_participant}, status={alloc.status}")
            
            voucher_allocation = db.query(EventAllocation).filter(
                EventAllocation.event_id == event_id
            ).first()
            
            vouchers_per_participant = 0
            if voucher_allocation:
                vouchers_per_participant = voucher_allocation.drink_vouchers_per_participant or 0
                logger.info(f"🍻 Event {event_id} allocation: {vouchers_per_participant} vouchers per participant (allocation_id: {voucher_allocation.id})")
                logger.info(f"🔍 Allocation details: status={voucher_allocation.status}, created_at={voucher_allocation.created_at}, drink_vouchers={voucher_allocation.drink_vouchers_per_participant}")
            else:
                logger.warning(f"⚠️ No voucher allocation found for event {event_id}")
            
            # Get participants with voucher data
            participants_query = db.query(
                EventParticipant.id,
                EventParticipant.full_name,
                EventParticipant.email
            ).filter(
                EventParticipant.event_id == event_id,
                EventParticipant.status.in_(["confirmed", "registered", "selected", "attended"])
            )
            
            participants = participants_query.all()
            participant_voucher_info = []
            
            for participant in participants:
                # Count redemptions for this participant
                redemption_count = 0
                if voucher_allocation:
                    redemption_count = db.query(func.sum(ParticipantVoucherRedemption.quantity)).filter(
                        ParticipantVoucherRedemption.allocation_id == voucher_allocation.id,
                        ParticipantVoucherRedemption.participant_id == participant.id
                    ).scalar() or 0
                
                remaining_vouchers = max(0, vouchers_per_participant - redemption_count)
                
                logger.info(f"📊 Participant {participant.full_name} (ID: {participant.id}, Email: {participant.email}): allocated={vouchers_per_participant}, redeemed={redemption_count}, remaining={remaining_vouchers}")
                
                participant_info = ParticipantVoucherInfo(
                    participant_id=participant.id,
                    participant_name=participant.full_name or "Unknown",
                    participant_email=participant.email,
                    allocated_vouchers=vouchers_per_participant,
                    redeemed_vouchers=redemption_count,
                    remaining_vouchers=remaining_vouchers
                )
                participant_voucher_info.append(participant_info)
            
            # Only include events that have participants
            if participant_voucher_info:
                scanner_event = ScannerEventInfo(
                    event_id=event_id,
                    event_name=event_name,
                    event_description=event_description,
                    start_date=start_date,
                    end_date=end_date,
                    participants=participant_voucher_info
                )
                scanner_events.append(scanner_event)
        
        logger.info(f"✅ Returning {len(scanner_events)} scanner events")
        return scanner_events
        
    except Exception as e:
        logger.error(f"Error fetching scanner events: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch scanner events: {str(e)}")

@router.post("/scanner/redeem-voucher")
async def redeem_voucher_scan(
    request: VoucherRedeemRequest,
    db: Session = Depends(get_db)
):
    """Redeem voucher via scanner (mobile app)"""
    try:
        logger.info(f"🎫 REDEEM VOUCHER: participant_id={request.participant_id}, scanner={request.scanner_email}")
        
        # Get scanner user
        scanner_user = db.query(User).filter(User.email == request.scanner_email).first()
        if not scanner_user:
            raise HTTPException(status_code=404, detail="Scanner user not found")
        
        # Get participant
        participant = db.query(EventParticipant).filter(
            EventParticipant.id == request.participant_id
        ).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        # Get voucher allocation for the event
        voucher_allocation = db.query(EventAllocation).filter(
            EventAllocation.event_id == participant.event_id
        ).first()
        
        if not voucher_allocation:
            raise HTTPException(status_code=404, detail="No voucher allocation found for this event")
        
        vouchers_per_participant = voucher_allocation.drink_vouchers_per_participant or 0
        
        # Check current redemption count
        current_redemptions = db.query(func.sum(ParticipantVoucherRedemption.quantity)).filter(
            ParticipantVoucherRedemption.allocation_id == voucher_allocation.id,
            ParticipantVoucherRedemption.participant_id == request.participant_id
        ).scalar() or 0
        
        # Check if participant has remaining vouchers
        remaining_vouchers = vouchers_per_participant - current_redemptions
        if remaining_vouchers <= 0:
            raise HTTPException(status_code=400, detail="No remaining vouchers for this participant")
        
        # Create redemption record
        voucher_redemption = ParticipantVoucherRedemption(
            allocation_id=voucher_allocation.id,
            participant_id=request.participant_id,
            quantity=1,
            redeemed_by=str(scanner_user.id),
            redeemed_at=datetime.utcnow(),
            notes=request.notes or f"Scanned by {request.scanner_email}"
        )
        db.add(voucher_redemption)
        db.commit()
        
        logger.info(f"✅ Voucher redeemed successfully for participant {request.participant_id}")
        
        return {
            "success": True,
            "message": "Voucher redeemed successfully",
            "participant_id": request.participant_id,
            "participant_name": participant.full_name,
            "total_redeemed": current_redemptions + 1,
            "remaining_vouchers": remaining_vouchers - 1
        }
        
    except Exception as e:
        logger.error(f"Error redeeming voucher: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to redeem voucher: {str(e)}")