from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List
from datetime import datetime, date
import base64
import io
from app.db.database import get_db
from app.models.event_attendance import EventCheckin, EquipmentRequest, EventReview, AppReview
from app.models.event_participant import EventParticipant
from app.models.participant_qr import ParticipantQR
from app.models.event import Event
from app.schemas.event_attendance import (
    EventCheckinCreate, EventCheckin as CheckinSchema,
    EquipmentRequestCreate, EquipmentRequest as RequestSchema,
    EventReviewCreate, EventReview as ReviewSchema,
    AppReviewCreate, AppReview as AppReviewSchema,
    AttendanceStats, BadgePrintData, EquipmentRequestAction
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

# Event Check-in System
@router.post("/checkin/", response_model=CheckinSchema)
def checkin_participant(
    checkin: EventCheckinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin scans QR code to check in participant"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get participant from QR token
    qr_record = db.query(ParticipantQR).filter(
        ParticipantQR.qr_token == checkin.qr_token
    ).first()
    
    if not qr_record:
        raise HTTPException(status_code=404, detail="Invalid QR code")
    
    # Get participant and event details
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == qr_record.participant_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Check if already checked in today
    today = date.today()
    existing_checkin = db.query(EventCheckin).filter(
        and_(
            EventCheckin.participant_id == participant.id,
            EventCheckin.event_id == participant.event_id,
            EventCheckin.checkin_date == today
        )
    ).first()
    
    if existing_checkin:
        raise HTTPException(status_code=400, detail="Already checked in today")
    
    # Create check-in record
    db_checkin = EventCheckin(
        participant_id=participant.id,
        event_id=participant.event_id,
        checkin_date=today,
        checkin_time=datetime.now(),
        checked_in_by=current_user.email,
        qr_token_used=checkin.qr_token,
        notes=checkin.notes
    )
    
    db.add(db_checkin)
    db.commit()
    db.refresh(db_checkin)
    
    return db_checkin

@router.post("/checkin/{checkin_id}/print-badge")
def print_badge(
    checkin_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin prints badge for checked-in participant"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    checkin = db.query(EventCheckin, EventParticipant, Event).join(
        EventParticipant, EventCheckin.participant_id == EventParticipant.id
    ).join(
        Event, EventCheckin.event_id == Event.id
    ).filter(EventCheckin.id == checkin_id).first()
    
    if not checkin:
        raise HTTPException(status_code=404, detail="Check-in not found")
    
    checkin_record, participant, event = checkin
    
    # Mark badge as printed
    checkin_record.badge_printed = True
    checkin_record.badge_printed_at = datetime.now()
    db.commit()
    
    # Generate badge data
    badge_data = BadgePrintData(
        participant_name=participant.full_name or participant.email,
        participant_email=participant.email,
        event_title=event.title,
        checkin_date=str(checkin_record.checkin_date),
        qr_code=checkin_record.qr_token_used
    )
    
    return {
        "message": "Badge ready for printing",
        "badge_data": badge_data,
        "print_instructions": "Send badge_data to printer service"
    }

@router.get("/attendance/{event_id}", response_model=AttendanceStats)
def get_attendance_stats(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin gets attendance statistics for event"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get total participants
    total_participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id
    ).count()
    
    # Get total unique check-ins
    total_checkins = db.query(EventCheckin.participant_id).filter(
        EventCheckin.event_id == event_id
    ).distinct().count()
    
    # Get daily check-ins
    daily_checkins = db.query(
        EventCheckin.checkin_date,
        func.count(EventCheckin.id).label('count')
    ).filter(
        EventCheckin.event_id == event_id
    ).group_by(EventCheckin.checkin_date).all()
    
    daily_data = [
        {"date": str(date), "checkins": count}
        for date, count in daily_checkins
    ]
    
    # Get badges printed
    badges_printed = db.query(EventCheckin).filter(
        and_(
            EventCheckin.event_id == event_id,
            EventCheckin.badge_printed == True
        )
    ).count()
    
    attendance_rate = (total_checkins / total_participants * 100) if total_participants > 0 else 0
    
    return AttendanceStats(
        event_id=event_id,
        event_title=event.title,
        total_participants=total_participants,
        total_checkins=total_checkins,
        attendance_rate=round(attendance_rate, 2),
        daily_checkins=daily_data,
        badges_printed=badges_printed
    )

# Equipment Requests
@router.post("/equipment-requests/", response_model=RequestSchema)
def create_equipment_request(
    request: EquipmentRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor requests equipment for event"""
    
    # Get participant record
    participant = db.query(EventParticipant).filter(
        and_(
            EventParticipant.email == current_user.email,
            EventParticipant.event_id == request.event_id
        )
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Not registered for this event")
    
    db_request = EquipmentRequest(
        participant_id=participant.id,
        **request.dict()
    )
    
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    
    return db_request

@router.get("/equipment-requests/my-requests", response_model=List[RequestSchema])
def get_my_equipment_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor gets their equipment requests"""
    
    requests = db.query(EquipmentRequest).join(
        EventParticipant, EquipmentRequest.participant_id == EventParticipant.id
    ).filter(EventParticipant.email == current_user.email).all()
    
    return requests

@router.get("/equipment-requests/pending", response_model=List[dict])
def get_pending_equipment_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin gets pending equipment requests"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    requests = db.query(EquipmentRequest, EventParticipant, Event).join(
        EventParticipant, EquipmentRequest.participant_id == EventParticipant.id
    ).join(
        Event, EquipmentRequest.event_id == Event.id
    ).filter(EquipmentRequest.status == "pending").all()
    
    result = []
    for request, participant, event in requests:
        result.append({
            "request_id": request.id,
            "participant_name": participant.full_name or participant.email,
            "participant_email": participant.email,
            "event_title": event.title,
            "equipment_name": request.equipment_name,
            "quantity": request.quantity,
            "description": request.description,
            "urgency": request.urgency,
            "created_at": request.created_at
        })
    
    return result

@router.post("/equipment-requests/{request_id}/action")
def handle_equipment_request(
    request_id: int,
    action: EquipmentRequestAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin handles equipment request"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    request = db.query(EquipmentRequest).filter(EquipmentRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request.status = action.status
    request.admin_notes = action.admin_notes
    
    if action.status == "approved":
        request.approved_by = current_user.email
    elif action.status == "fulfilled":
        request.fulfilled_by = current_user.email
        request.fulfilled_at = datetime.now()
    
    db.commit()
    return {"message": f"Request {action.status}"}

# Event Reviews
@router.post("/reviews/event/", response_model=ReviewSchema)
def create_event_review(
    review: EventReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor submits event review"""
    
    # Get participant record
    participant = db.query(EventParticipant).filter(
        and_(
            EventParticipant.email == current_user.email,
            EventParticipant.event_id == review.event_id
        )
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Not registered for this event")
    
    # Check if already reviewed
    existing = db.query(EventReview).filter(
        and_(
            EventReview.participant_id == participant.id,
            EventReview.event_id == review.event_id
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already reviewed this event")
    
    db_review = EventReview(
        participant_id=participant.id,
        **review.dict()
    )
    
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    return db_review

@router.get("/reviews/event/{event_id}", response_model=List[dict])
def get_event_reviews(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get event reviews (admin only)"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    reviews = db.query(EventReview, EventParticipant).join(
        EventParticipant, EventReview.participant_id == EventParticipant.id
    ).filter(EventReview.event_id == event_id).all()
    
    result = []
    for review, participant in reviews:
        result.append({
            "reviewer_name": participant.full_name or "Anonymous",
            "overall_rating": review.overall_rating,
            "content_rating": review.content_rating,
            "organization_rating": review.organization_rating,
            "venue_rating": review.venue_rating,
            "catering_rating": review.catering_rating,
            "review_text": review.review_text,
            "suggestions": review.suggestions,
            "would_recommend": review.would_recommend,
            "created_at": review.created_at
        })
    
    return result

# App Reviews
@router.post("/reviews/app/", response_model=AppReviewSchema)
def create_app_review(
    review: AppReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """User submits app review"""
    
    # Check if already reviewed
    existing = db.query(AppReview).filter(
        AppReview.user_email == current_user.email
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already reviewed the app")
    
    db_review = AppReview(
        user_email=current_user.email,
        user_name=current_user.full_name or current_user.email,
        **review.dict()
    )
    
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    return db_review

@router.get("/reviews/app/", response_model=List[AppReviewSchema])
def get_app_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get app reviews (admin only)"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return db.query(AppReview).order_by(desc(AppReview.created_at)).all()