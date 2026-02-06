from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import json
from app.db.database import get_db
from app.models.visitor_enhancements import EventContact, ParticipantProfile, ContactType
from app.models.accommodation import RoomAssignment
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

# Event Contacts
@router.post("/contacts/")
def create_event_contact(
    contact_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin creates event contact"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    contact = EventContact(
        **contact_data,
        created_by=current_user.email
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

@router.get("/contacts/{event_id}")
def get_event_contacts(event_id: int, db: Session = Depends(get_db)):
    """Get useful contacts for event"""
    contacts = db.query(EventContact).filter(
        EventContact.event_id == event_id
    ).order_by(EventContact.is_primary.desc(), EventContact.contact_type).all()
    
    # Group by contact type
    grouped_contacts = {}
    for contact in contacts:
        contact_type = contact.contact_type.value
        if contact_type not in grouped_contacts:
            grouped_contacts[contact_type] = []
        
        grouped_contacts[contact_type].append({
            "name": contact.name,
            "title": contact.title,
            "phone": contact.phone,
            "email": contact.email,
            "department": contact.department,
            "availability": contact.availability,
            "is_primary": contact.is_primary
        })
    
    return grouped_contacts

# Participant Profile & Accommodations
@router.post("/profile/")
def update_participant_profile(
    profile_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor updates their profile with allergies and special requests"""
    
    # Get participant record
    participant = db.query(EventParticipant).filter(
        EventParticipant.email == current_user.email
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant record not found")
    
    # Check if profile exists
    profile = db.query(ParticipantProfile).filter(
        ParticipantProfile.participant_id == participant.id
    ).first()
    
    if profile:
        # Update existing profile
        for key, value in profile_data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
    else:
        # Create new profile
        profile = ParticipantProfile(
            participant_id=participant.id,
            **profile_data
        )
        db.add(profile)
    
    db.commit()
    db.refresh(profile)
    return profile

@router.get("/profile/")
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor gets their profile"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.email == current_user.email
    ).first()
    
    if not participant:
        return {"message": "No participant record found"}
    
    profile = db.query(ParticipantProfile).filter(
        ParticipantProfile.participant_id == participant.id
    ).first()
    
    if not profile:
        return {"message": "No profile found"}
    
    return {
        "dietary_restrictions": json.loads(profile.dietary_restrictions) if profile.dietary_restrictions else [],
        "food_allergies": json.loads(profile.food_allergies) if profile.food_allergies else [],
        "medical_conditions": json.loads(profile.medical_conditions) if profile.medical_conditions else [],
        "mobility_requirements": profile.mobility_requirements,
        "special_requests": profile.special_requests,
        "emergency_contact": {
            "name": profile.emergency_contact_name,
            "phone": profile.emergency_contact_phone,
            "relationship": profile.emergency_contact_relationship
        }
    }

@router.get("/accommodations/")
def get_my_accommodations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor gets all their accommodations"""
    
    # Get all participant records for this user
    participants = db.query(EventParticipant).filter(
        EventParticipant.email == current_user.email
    ).all()
    
    if not participants:
        return {"accommodations": []}
    
    participant_ids = [p.id for p in participants]
    
    # Get all room assignments
    accommodations = db.query(RoomAssignment, Event).join(
        EventParticipant, RoomAssignment.participant_id == EventParticipant.id
    ).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(RoomAssignment.participant_id.in_(participant_ids)).all()
    
    result = []
    for accommodation, event in accommodations:
        # Calculate duration
        duration_days = (accommodation.check_out_date.date() - accommodation.check_in_date.date()).days
        
        result.append({
            "event_title": event.title,
            "hotel_name": accommodation.hotel_name,
            "room_number": accommodation.room_number,
            "room_type": accommodation.room_type.value,
            "address": accommodation.address,
            "check_in_date": accommodation.check_in_date,
            "check_out_date": accommodation.check_out_date,
            "duration_days": duration_days,
            "checked_in": accommodation.checked_in,
            "amenities": json.loads(accommodation.amenities) if accommodation.amenities else [],
            "wifi_password": accommodation.wifi_password,
            "special_instructions": accommodation.special_instructions
        })
    
    return {"accommodations": result}

# Enhanced Security Briefs
@router.get("/security-briefs/")
def get_applicable_security_briefs(
    event_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get security briefs (general + event-specific)"""
    from app.models.security_brief import SecurityBrief, BriefType
    
    query = db.query(SecurityBrief).filter(
        and_(
            SecurityBrief.tenant_id == current_user.tenant_id,
            SecurityBrief.is_active == True
        )
    )
    
    if event_id:
        # Get general briefs + event-specific briefs
        query = query.filter(
            or_(
                SecurityBrief.brief_type == BriefType.GENERAL,
                and_(
                    SecurityBrief.brief_type == BriefType.EVENT_SPECIFIC,
                    SecurityBrief.event_id == event_id
                )
            )
        )
    else:
        # Only general briefs
        query = query.filter(SecurityBrief.brief_type == BriefType.GENERAL)
    
    briefs = query.all()
    
    # Group by type
    result = {
        "general_briefs": [],
        "event_specific_briefs": []
    }
    
    for brief in briefs:
        brief_data = {
            "id": brief.id,
            "title": brief.title,
            "content_type": brief.content_type.value,
            "content": brief.content,
            "created_at": brief.created_at
        }
        
        if brief.brief_type == BriefType.GENERAL:
            result["general_briefs"].append(brief_data)
        else:
            result["event_specific_briefs"].append(brief_data)
    
    return result

# Notification helpers
def send_notification(recipient_email: str, notification_type: str, title: str, message: str, data: dict = None):
    """Helper function to queue notifications"""
    from app.models.visitor_enhancements import NotificationQueue, NotificationType
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        notification = NotificationQueue(
            recipient_email=recipient_email,
            notification_type=NotificationType(notification_type),
            title=title,
            message=message,
            data=json.dumps(data) if data else None
        )
        db.add(notification)
        db.commit()
    finally:
        db.close()

@router.get("/notifications/")
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's notifications"""
    from app.models.visitor_enhancements import NotificationQueue
    
    notifications = db.query(NotificationQueue).filter(
        NotificationQueue.recipient_email == current_user.email
    ).order_by(NotificationQueue.created_at.desc()).limit(50).all()
    
    result = []
    for notification in notifications:
        result.append({
            "id": notification.id,
            "type": notification.notification_type.value,
            "title": notification.title,
            "message": notification.message,
            "data": json.loads(notification.data) if notification.data else None,
            "sent": notification.sent,
            "created_at": notification.created_at
        })
    
    return result
