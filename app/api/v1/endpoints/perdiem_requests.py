from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List
from datetime import date
from decimal import Decimal
import logging
from app.db.database import get_db
from app.models.perdiem_request import PerdiemRequest, PerdiemStatus
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.models.travel_ticket import ParticipantTicket
from app.models.perdiem_setup import PerdiemSetup
from app.schemas.perdiem_request import (
    PerdiemRequestCreate, PerdiemRequestUpdate, PerdiemRequest as PerdiemSchema,
    PerdiemApprovalAction, PerdiemPaymentAction, ParticipantPerdiemSummary
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/my-perdiem-eligibility", response_model=ParticipantPerdiemSummary)
def get_my_perdiem_eligibility(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check perdiem eligibility for current user"""
    
    # Get user's events
    participants = db.query(EventParticipant, Event).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(EventParticipant.email == current_user.email).all()
    
    if not participants:
        raise HTTPException(status_code=404, detail="No events found")
    
    # Get earliest arrival and latest departure from events
    earliest_start = min(event.start_date for _, event in participants)
    latest_end = max(event.end_date for _, event in participants)
    
    # Check if user has ticket info for more accurate dates
    ticket = db.query(ParticipantTicket).join(
        EventParticipant, ParticipantTicket.participant_id == EventParticipant.id
    ).filter(EventParticipant.email == current_user.email).first()
    
    if ticket:
        arrival_date = ticket.arrival_date
        departure_date = ticket.departure_date
    else:
        arrival_date = earliest_start
        departure_date = latest_end
    
    calculated_days = (departure_date - arrival_date).days + 1
    
    # Get daily rate (use first event's rate or default)
    daily_rate = participants[0][1].perdiem_rate or Decimal('50.00')
    
    # Check existing perdiem request
    existing_request = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).filter(EventParticipant.email == current_user.email).first()
    
    events_data = [
        {
            "title": event.title,
            "start_date": str(event.start_date),
            "end_date": str(event.end_date),
            "location": event.location
        }
        for _, event in participants
    ]
    
    return ParticipantPerdiemSummary(
        participant_email=current_user.email,
        participant_name=current_user.full_name or current_user.email,
        events=events_data,
        arrival_date=arrival_date,
        departure_date=departure_date,
        calculated_days=calculated_days,
        requested_days=existing_request.requested_days if existing_request else calculated_days,
        daily_rate=daily_rate,
        total_amount=daily_rate * (existing_request.requested_days if existing_request else calculated_days),
        can_request_perdiem=existing_request is None,
        perdiem_status=existing_request.status.value if existing_request else None
    )

@router.post("/request", response_model=PerdiemSchema)
def create_perdiem_request(
    request_data: PerdiemRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor creates perdiem request"""
    
    # Get participant record
    participant = db.query(EventParticipant).filter(
        EventParticipant.email == current_user.email
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="No event participation found")
    
    # Check if request already exists
    existing = db.query(PerdiemRequest).filter(
        PerdiemRequest.participant_id == participant.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Perdiem request already exists")
    
    # Calculate days and amount
    calculated_days = (request_data.departure_date - request_data.arrival_date).days + 1
    requested_days = request_data.requested_days or calculated_days
    
    # Get daily rate from tenant's per diem setup
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    
    # Fetch per diem setup for the event's tenant
    perdiem_setup = db.query(PerdiemSetup).filter(
        PerdiemSetup.tenant_id == event.tenant_id
    ).first()
    
    if not perdiem_setup:
        raise HTTPException(status_code=400, detail="Per diem setup not configured for this tenant")
    
    daily_rate = perdiem_setup.daily_rate
    currency = perdiem_setup.currency
    
    # Calculate base amount
    base_amount = daily_rate * requested_days
    
    # Get accommodations for deduction calculation
    from app.models.guesthouse import AccommodationAllocation, VendorAccommodation, GuestHouse, Room
    
    accommodations = db.query(AccommodationAllocation).filter(
        AccommodationAllocation.participant_id == participant.id,
        AccommodationAllocation.tenant_id == event.tenant_id,
        AccommodationAllocation.status.in_(["booked", "checked_in"]),
        AccommodationAllocation.check_in_date <= request_data.departure_date,
        AccommodationAllocation.check_out_date >= request_data.arrival_date
    ).all()
    
    # Calculate accommodation deductions
    accommodation_deduction = Decimal('0.00')
    accommodation_details = []
    
    for allocation in accommodations:
        rate_per_day = allocation.rate_per_day
        
        # Get rate from guesthouse or vendor if not in allocation
        if not rate_per_day:
            if allocation.vendor_accommodation_id:
                vendor = db.query(VendorAccommodation).filter(
                    VendorAccommodation.id == allocation.vendor_accommodation_id
                ).first()
                if vendor and allocation.board_type:
                    if allocation.board_type == 'FullBoard':
                        rate_per_day = vendor.rate_full_board
                    elif allocation.board_type == 'HalfBoard':
                        rate_per_day = vendor.rate_half_board
                    elif allocation.board_type == 'BedAndBreakfast':
                        rate_per_day = vendor.rate_bed_breakfast
                    elif allocation.board_type == 'BedOnly':
                        rate_per_day = vendor.rate_bed_only
            elif allocation.room_id:
                room = db.query(Room).filter(Room.id == allocation.room_id).first()
                if room:
                    guesthouse = db.query(GuestHouse).filter(GuestHouse.id == room.guesthouse_id).first()
                    if guesthouse and allocation.board_type:
                        if allocation.board_type == 'FullBoard':
                            rate_per_day = guesthouse.fullboard_rate
                        elif allocation.board_type == 'HalfBoard':
                            rate_per_day = guesthouse.halfboard_rate
                        elif allocation.board_type == 'BedAndBreakfast':
                            rate_per_day = guesthouse.bed_and_breakfast_rate
                        elif allocation.board_type == 'BedOnly':
                            rate_per_day = guesthouse.bed_only_rate
        
        if rate_per_day:
            # Calculate overlapping days
            overlap_start = max(allocation.check_in_date, request_data.arrival_date)
            overlap_end = min(allocation.check_out_date, request_data.departure_date)
            overlap_days = (overlap_end - overlap_start).days
            
            if overlap_days > 0:
                deduction = Decimal(str(rate_per_day)) * overlap_days
                accommodation_deduction += deduction
                
                accommodation_details.append({
                    "name": allocation.guest_name or "Accommodation",
                    "board_type": allocation.board_type,
                    "rate_per_day": float(rate_per_day),
                    "days": overlap_days,
                    "total": float(deduction)
                })
    
    # Calculate final amount after deductions
    total_amount = base_amount - accommodation_deduction
    
    # Store accommodation breakdown summary
    accommodation_days_total = sum(detail['days'] for detail in accommodation_details)
    accommodation_rate_avg = accommodation_deduction / accommodation_days_total if accommodation_days_total > 0 else Decimal('0.00')
    
    # Create request
    perdiem_request = PerdiemRequest(
        participant_id=participant.id,
        arrival_date=request_data.arrival_date,
        departure_date=request_data.departure_date,
        calculated_days=calculated_days,
        requested_days=requested_days,
        daily_rate=daily_rate,
        currency=currency,
        total_amount=total_amount,
        justification=request_data.justification,
        accommodation_deduction=accommodation_deduction,
        per_diem_base_amount=base_amount,
        accommodation_days=accommodation_days_total if accommodation_days_total > 0 else None,
        accommodation_rate=accommodation_rate_avg if accommodation_days_total > 0 else None
    )
    
    db.add(perdiem_request)
    db.commit()
    db.refresh(perdiem_request)
    
    # Add accommodation details to response
    perdiem_request.accommodation_breakdown = accommodation_details
    perdiem_request.base_amount = float(base_amount)
    
    return perdiem_request

@router.put("/my-request", response_model=PerdiemSchema)
def update_my_perdiem_request(
    update_data: PerdiemRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor updates their perdiem request (only if open or pending)"""
    
    # Get user's perdiem request (allow updates for open and pending status)
    request = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).filter(
        and_(
            EventParticipant.email == current_user.email,
            PerdiemRequest.status.in_([PerdiemStatus.OPEN, PerdiemStatus.PENDING])
        )
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="No editable perdiem request found")
    
    # Recalculate rates from tenant setup
    participant = db.query(EventParticipant).filter(EventParticipant.id == request.participant_id).first()
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    
    # Fetch per diem setup for the event's tenant
    perdiem_setup = db.query(PerdiemSetup).filter(
        PerdiemSetup.tenant_id == event.tenant_id
    ).first()
    
    if not perdiem_setup:
        raise HTTPException(status_code=400, detail="Per diem setup not configured for this tenant")
    
    request.daily_rate = perdiem_setup.daily_rate
    request.currency = perdiem_setup.currency
    
    # Update request
    request.requested_days = update_data.requested_days
    request.justification = update_data.justification
    request.total_amount = request.daily_rate * update_data.requested_days
    
    db.commit()
    db.refresh(request)
    
    return request

@router.get("/my-request", response_model=PerdiemSchema)
def get_my_perdiem_request(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's perdiem request"""
    
    request = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).filter(EventParticipant.email == current_user.email).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="No perdiem request found")
    
    return request

@router.get("/pending", response_model=List[dict])
def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin gets pending perdiem requests"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    requests = db.query(PerdiemRequest, EventParticipant, Event).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(PerdiemRequest.status == PerdiemStatus.PENDING).all()
    
    result = []
    for request, participant, event in requests:
        days_difference = request.requested_days - request.calculated_days
        result.append({
            "request_id": request.id,
            "participant_name": participant.full_name or participant.email,
            "participant_email": participant.email,
            "event_title": event.title,
            "arrival_date": str(request.arrival_date),
            "departure_date": str(request.departure_date),
            "calculated_days": request.calculated_days,
            "requested_days": request.requested_days,
            "days_adjustment": days_difference,
            "daily_rate": float(request.daily_rate),
            "total_amount": float(request.total_amount),
            "justification": request.justification,
            "needs_review": days_difference != 0,
            "created_at": request.created_at
        })
    
    return result

@router.post("/{request_id}/approve")
def approve_perdiem_request(
    request_id: int,
    approval: PerdiemApprovalAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin approves or rejects perdiem request"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.status != PerdiemStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request is not pending")
    
    request.status = PerdiemStatus.APPROVED if approval.status == "approved" else PerdiemStatus.REJECTED
    request.approved_by = current_user.email
    request.admin_notes = approval.admin_notes
    
    db.commit()
    
    return {"message": f"Perdiem request {approval.status}"}

@router.post("/{request_id}/payment")
def record_perdiem_payment(
    request_id: int,
    payment: PerdiemPaymentAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin records perdiem payment"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.status != PerdiemStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Request must be approved first")
    
    request.status = PerdiemStatus.PAID
    request.payment_reference = payment.payment_reference
    if payment.admin_notes:
        request.admin_notes = payment.admin_notes
    
    db.commit()
    
    return {"message": "Payment recorded successfully"}

@router.put("/{request_id}")
def update_perdiem_request_by_id(
    request_id: int,
    update_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update perdiem request by ID (mobile app endpoint)"""
    
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 PER DIEM UPDATE BY ID: {request_id} by {current_user.email}")
    logger.info(f"Update Data: {update_data}")
    
    request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not request:
        logger.error(f"❌ Request {request_id} not found")
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Verify user owns this request
    participant = db.query(EventParticipant).filter(EventParticipant.id == request.participant_id).first()
    if participant.email != current_user.email:
        logger.error(f"❌ Unauthorized - Request belongs to {participant.email}, not {current_user.email}")
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if request.status not in [PerdiemStatus.OPEN, PerdiemStatus.PENDING]:
        logger.error(f"❌ Cannot update - Status is {request.status}")
        raise HTTPException(status_code=400, detail="Can only update open or pending requests")
    
    logger.info(f"✅ Found request - Current: {request.currency} {request.total_amount}")
    
    # Recalculate rates from tenant setup
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    perdiem_setup = db.query(PerdiemSetup).filter(PerdiemSetup.tenant_id == event.tenant_id).first()
    
    if not perdiem_setup:
        logger.error(f"❌ No per diem setup for tenant {event.tenant_id}")
        raise HTTPException(status_code=400, detail="Per diem setup not configured for this tenant")
    
    request.daily_rate = perdiem_setup.daily_rate
    request.currency = perdiem_setup.currency
    logger.info(f"💰 Using tenant setup: {request.currency} {request.daily_rate}")
    
    # Update fields
    if 'requested_days' in update_data:
        request.requested_days = update_data['requested_days']
    if 'purpose' in update_data:
        request.justification = update_data['purpose']
    if 'payment_method' in update_data:
        request.payment_method = update_data['payment_method']
    if 'cash_pickup_date' in update_data:
        request.cash_pickup_date = update_data['cash_pickup_date']
    if 'mpesa_number' in update_data:
        request.mpesa_number = update_data['mpesa_number']
    
    request.total_amount = request.daily_rate * request.requested_days
    
    logger.info(f"💵 NEW: {request.currency} {request.daily_rate} x {request.requested_days} = {request.total_amount}")
    
    db.commit()
    db.refresh(request)
    
    logger.info(f"✅ UPDATE COMPLETED")
    
    return request

@router.post("/{request_id}/cancel")
def cancel_perdiem_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel perdiem request"""
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚫 CANCEL PER DIEM REQUEST {request_id} by {current_user.email}")
    
    request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not request:
        logger.error(f"❌ Request {request_id} not found")
        raise HTTPException(status_code=404, detail="Request not found")
    
    logger.info(f"Current Status: {request.status}, Amount: {request.currency} {request.total_amount}")
    
    # Verify user owns this request
    participant = db.query(EventParticipant).filter(EventParticipant.id == request.participant_id).first()
    if participant.email != current_user.email:
        logger.error(f"❌ Unauthorized - Request belongs to {participant.email}")
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if request.status not in [PerdiemStatus.OPEN, PerdiemStatus.PENDING]:
        logger.error(f"❌ Cannot cancel - Status is {request.status}")
        raise HTTPException(status_code=400, detail="Can only cancel open or pending requests")
    
    old_status = request.status
    request.status = PerdiemStatus.OPEN
    db.commit()
    
    logger.info(f"✅ CANCEL SUCCESSFUL - Status: {old_status} → OPEN")
    
    return {"message": "Request cancelled successfully", "status": "open"}

@router.post("/{request_id}/submit")
def submit_perdiem_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit perdiem request for approval"""
    
    logger = logging.getLogger(__name__)
    logger.info(f"📤 SUBMIT PER DIEM REQUEST {request_id} by {current_user.email}")
    
    request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not request:
        logger.error(f"❌ Request {request_id} not found")
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Verify user owns this request
    participant = db.query(EventParticipant).filter(EventParticipant.id == request.participant_id).first()
    if participant.email != current_user.email:
        logger.error(f"❌ Unauthorized")
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if request.status != PerdiemStatus.OPEN:
        logger.error(f"❌ Cannot submit - Status is {request.status}")
        raise HTTPException(status_code=400, detail="Can only submit open requests")
    
    request.status = PerdiemStatus.PENDING
    db.commit()
    
    logger.info(f"✅ SUBMIT SUCCESSFUL - Status: OPEN → PENDING")
    
    return {"message": "Request submitted successfully"}

@router.post("/{request_id}/received")
def mark_perdiem_received(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark perdiem as received"""
    
    logger = logging.getLogger(__name__)
    logger.info(f"✅ MARK RECEIVED {request_id} by {current_user.email}")
    
    request = db.query(PerdiemRequest).filter(PerdiemRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Verify user owns this request
    participant = db.query(EventParticipant).filter(EventParticipant.id == request.participant_id).first()
    if participant.email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if request.status != PerdiemStatus.ISSUED:
        raise HTTPException(status_code=400, detail="Can only mark issued requests as received")
    
    request.status = PerdiemStatus.COMPLETED
    db.commit()
    
    logger.info(f"✅ Request {request_id} marked as received")
    
    return {"message": "Marked as received successfully"}
