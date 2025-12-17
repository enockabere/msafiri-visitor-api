# File: app/services/vetting_notification_service.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.vetting_committee import VettingCommittee, VettingStatus
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.core.email_service import email_service
from app.db.database import SessionLocal

def check_deadline_notifications():
    """Check for committees approaching deadline and send notifications"""
    db = SessionLocal()
    try:
        # Get committees with deadline in 2 days
        deadline_date = datetime.utcnow() + timedelta(days=2)
        
        committees = db.query(VettingCommittee).filter(
            VettingCommittee.selection_end_date <= deadline_date,
            VettingCommittee.status.in_([VettingStatus.PENDING, VettingStatus.IN_PROGRESS])
        ).all()
        
        for committee in committees:
            event = db.query(Event).filter(Event.id == committee.event_id).first()
            if not event:
                continue
                
            # Send notification to committee members
            for member in committee.members:
                subject = f"Deadline Reminder: Selection for {event.title}"
                message = f"""
Dear {member.full_name},

This is a reminder that the selection deadline for {event.title} is approaching.

Deadline: {committee.selection_end_date}
Time Remaining: Less than 2 days

Please complete your participant selections before the deadline.

Access Portal: {get_frontend_url()}/vetting-committee/{committee.id}

Best regards,
MSF Msafiri Team
                """
                
                try:
                    email_service.send_notification_email(
                        to_email=member.email,
                        user_name=member.full_name,
                        title=subject,
                        message=message
                    )
                except Exception as e:
                    print(f"Failed to send deadline reminder to {member.email}: {e}")
    
    finally:
        db.close()

def send_participant_selection_notifications(committee_id: int, db: Session):
    """Send notifications to selected participants after approval"""
    committee = db.query(VettingCommittee).filter(VettingCommittee.id == committee_id).first()
    if not committee or committee.approval_status != "approved":
        return
    
    event = db.query(Event).filter(Event.id == committee.event_id).first()
    if not event:
        return
    
    # Get selected participants
    selected_participants = db.query(EventParticipant).join(
        ParticipantSelection, EventParticipant.id == ParticipantSelection.participant_id
    ).filter(
        ParticipantSelection.committee_id == committee_id,
        ParticipantSelection.selected == True
    ).all()
    
    # Send selection notifications
    for participant in selected_participants:
        subject = f"Selected: {event.title}"
        message = f"""
Dear {participant.full_name},

Congratulations! You have been selected to attend {event.title}.

Event Details:
- Event: {event.title}
- Date: {event.start_date} to {event.end_date}
- Location: {event.location}

You can now view this event in the MSafiri mobile app.

Best regards,
MSF Msafiri Team
        """
        
        try:
            email_service.send_notification_email(
                to_email=participant.email,
                user_name=participant.full_name,
                title=subject,
                message=message
            )
        except Exception as e:
            print(f"Failed to send selection notification to {participant.email}: {e}")

def get_frontend_url():
    """Get frontend URL from environment"""
    from app.core.config import settings
    return getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')