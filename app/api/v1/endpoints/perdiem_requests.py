from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List
from datetime import date
from decimal import Decimal
from app.db.database import get_db
from app.models.perdiem_request import PerdiemRequest, PerdiemStatus
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.models.travel_ticket import ParticipantTicket
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
    
    # Get daily rate from events
    event = db.query(Event).filter(Event.id == participant.event_id).first()
    daily_rate = event.perdiem_rate or Decimal('50.00')
    
    total_amount = daily_rate * requested_days
    
    # Create request
    perdiem_request = PerdiemRequest(
        participant_id=participant.id,
        arrival_date=request_data.arrival_date,
        departure_date=request_data.departure_date,
        calculated_days=calculated_days,
        requested_days=requested_days,
        daily_rate=daily_rate,
        total_amount=total_amount,
        justification=request_data.justification
    )
    
    db.add(perdiem_request)
    db.commit()
    db.refresh(perdiem_request)
    
    return perdiem_request

@router.put("/my-request", response_model=PerdiemSchema)
def update_my_perdiem_request(
    update_data: PerdiemRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor updates their perdiem request (only if pending)"""
    
    # Get user's perdiem request
    request = db.query(PerdiemRequest).join(
        EventParticipant, PerdiemRequest.participant_id == EventParticipant.id
    ).filter(
        and_(
            EventParticipant.email == current_user.email,
            PerdiemRequest.status == PerdiemStatus.PENDING
        )
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="No pending perdiem request found")
    
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
