from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List
from datetime import date
from decimal import Decimal
from app.db.database import get_db
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.participant_perdiem import ParticipantPerdiem, EventConflictCheck
from app.schemas.multi_event import (
    ParticipantEventSummary, EventConflict, ParticipantPerdiem as PerdiemSchema,
    PerdiemApproval, PerdiemPayment
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/participants/{participant_email}/events", response_model=ParticipantEventSummary)
def get_participant_events(
    participant_email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all events for a participant with perdiem calculation"""
    
    # Get all participant records for this email
    participants = db.query(EventParticipant, Event).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(EventParticipant.email == participant_email).all()
    
    if not participants:
        raise HTTPException(status_code=404, detail="No events found for participant")
    
    events_data = []
    total_perdiem = Decimal('0.00')
    
    for participant, event in participants:
        # Get or calculate perdiem
        perdiem = db.query(ParticipantPerdiem).filter(
            and_(
                ParticipantPerdiem.participant_id == participant.id,
                ParticipantPerdiem.event_id == event.id
            )
        ).first()
        
        if not perdiem and event.perdiem_rate and event.duration_days:
            # Create perdiem record
            perdiem = ParticipantPerdiem(
                participant_id=participant.id,
                event_id=event.id,
                daily_rate=event.perdiem_rate,
                duration_days=event.duration_days,
                total_amount=event.perdiem_rate * event.duration_days
            )
            db.add(perdiem)
            db.commit()
            db.refresh(perdiem)
        
        event_perdiem = perdiem.total_amount if perdiem else Decimal('0.00')
        total_perdiem += event_perdiem
        
        events_data.append({
            "event_id": event.id,
            "title": event.title,
            "start_date": str(event.start_date),
            "end_date": str(event.end_date),
            "duration_days": event.duration_days,
            "location": event.location,
            "perdiem_amount": float(event_perdiem),
            "perdiem_approved": perdiem.approved if perdiem else False,
            "perdiem_paid": perdiem.paid if perdiem else False
        })
    
    # Check for conflicts
    conflicts = check_event_conflicts(participant_email, db)
    
    return ParticipantEventSummary(
        participant_id=participants[0][0].id,
        participant_name=participants[0][0].full_name or "Unknown",
        participant_email=participant_email,
        events=events_data,
        total_perdiem=total_perdiem,
        conflicts=conflicts
    )

def check_event_conflicts(participant_email: str, db: Session) -> List[EventConflict]:
    """Check for date conflicts between participant's events"""
    
    # Get all events for participant
    participant_events = db.query(EventParticipant, Event).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(EventParticipant.email == participant_email).all()
    
    conflicts = []
    
    for i, (participant1, event1) in enumerate(participant_events):
        for j, (participant2, event2) in enumerate(participant_events[i+1:], i+1):
            # Check for date overlap
            if (event1.start_date <= event2.end_date and event1.end_date >= event2.start_date):
                conflict_type = "overlap"
                if event1.start_date == event2.start_date or event1.end_date == event2.end_date:
                    conflict_type = "same_day"
                
                conflicts.append(EventConflict(
                    participant_email=participant_email,
                    event_id=event1.id,
                    event_title=event1.title,
                    conflicting_event_id=event2.id,
                    conflicting_event_title=event2.title,
                    conflict_type=conflict_type,
                    event_dates=f"{event1.start_date} to {event1.end_date}",
                    conflicting_dates=f"{event2.start_date} to {event2.end_date}"
                ))
    
    return conflicts

@router.get("/conflicts/", response_model=List[EventConflict])
def get_all_conflicts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all event conflicts for admin review"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get all participants with multiple events
    participants_with_multiple = db.query(EventParticipant.email).group_by(
        EventParticipant.email
    ).having(func.count(EventParticipant.id) > 1).all()
    
    all_conflicts = []
    for (email,) in participants_with_multiple:
        conflicts = check_event_conflicts(email, db)
        all_conflicts.extend(conflicts)
    
    return all_conflicts

@router.get("/perdiem/pending", response_model=List[PerdiemSchema])
def get_pending_perdiem(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending perdiem approvals"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return db.query(ParticipantPerdiem).filter(
        ParticipantPerdiem.approved == False
    ).all()

@router.post("/perdiem/approve")
def approve_perdiem(
    approval: PerdiemApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve participant perdiem"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    perdiem = db.query(ParticipantPerdiem).filter(
        and_(
            ParticipantPerdiem.participant_id == approval.participant_id,
            ParticipantPerdiem.event_id == approval.event_id
        )
    ).first()
    
    if not perdiem:
        raise HTTPException(status_code=404, detail="Perdiem record not found")
    
    perdiem.approved = approval.approved
    perdiem.approved_by = current_user.email
    if approval.notes:
        perdiem.notes = approval.notes
    
    db.commit()
    return {"message": "Perdiem approval updated"}

@router.post("/perdiem/payment")
def record_perdiem_payment(
    payment: PerdiemPayment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record perdiem payment"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    perdiem = db.query(ParticipantPerdiem).filter(
        and_(
            ParticipantPerdiem.participant_id == payment.participant_id,
            ParticipantPerdiem.event_id == payment.event_id
        )
    ).first()
    
    if not perdiem:
        raise HTTPException(status_code=404, detail="Perdiem record not found")
    
    if not perdiem.approved:
        raise HTTPException(status_code=400, detail="Perdiem must be approved before payment")
    
    perdiem.paid = True
    perdiem.payment_reference = payment.payment_reference
    if payment.notes:
        perdiem.notes = payment.notes
    
    db.commit()
    return {"message": "Perdiem payment recorded"}

@router.get("/perdiem/summary/{participant_email}")
def get_perdiem_summary(
    participant_email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get perdiem summary for participant"""
    
    perdiem_records = db.query(ParticipantPerdiem, Event, EventParticipant).join(
        Event, ParticipantPerdiem.event_id == Event.id
    ).join(
        EventParticipant, ParticipantPerdiem.participant_id == EventParticipant.id
    ).filter(EventParticipant.email == participant_email).all()
    
    total_approved = sum(p.total_amount for p, e, ep in perdiem_records if p.approved)
    total_paid = sum(p.total_amount for p, e, ep in perdiem_records if p.paid)
    total_pending = sum(p.total_amount for p, e, ep in perdiem_records if not p.approved)
    
    return {
        "participant_email": participant_email,
        "total_approved": float(total_approved),
        "total_paid": float(total_paid),
        "total_pending": float(total_pending),
        "records": [
            {
                "event_title": e.title,
                "amount": float(p.total_amount),
                "approved": p.approved,
                "paid": p.paid,
                "duration_days": p.duration_days,
                "daily_rate": float(p.daily_rate)
            }
            for p, e, ep in perdiem_records
        ]
    }
