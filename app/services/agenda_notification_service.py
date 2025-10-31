from typing import List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.event_agenda import EventAgenda
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.services.notification_service import create_notification
import logging

logger = logging.getLogger(__name__)

def send_agenda_start_notifications(db: Session):
    """Check for agenda items starting now and send notifications to participants"""
    try:
        current_time = datetime.now()
        # Check for agenda items starting in the next 5 minutes
        start_window = current_time + timedelta(minutes=5)
        
        # Get agenda items starting soon
        upcoming_agenda_items = db.query(EventAgenda).filter(
            EventAgenda.event_date == current_time.date(),
            EventAgenda.time >= current_time.strftime('%H:%M'),
            EventAgenda.time <= start_window.strftime('%H:%M')
        ).all()
        
        for agenda_item in upcoming_agenda_items:
            # Get event details
            event = db.query(Event).filter(Event.id == agenda_item.event_id).first()
            if not event:
                continue
                
            # Get all confirmed participants for this event
            participants = db.query(EventParticipant).filter(
                EventParticipant.event_id == agenda_item.event_id,
                EventParticipant.status.in_(['confirmed', 'checked_in'])
            ).all()
            
            # Send notification to each participant
            for participant in participants:
                title = f"Session Starting: {agenda_item.title}"
                message = f"'{agenda_item.title}' is starting at {agenda_item.time}. Don't miss it!"
                
                create_notification(
                    db=db,
                    user_email=participant.email,
                    tenant_id=str(event.tenant_id),
                    title=title,
                    message=message,
                    triggered_by="system"
                )
                
                logger.info(f"Sent agenda notification to {participant.email} for agenda {agenda_item.id}")
        
        db.commit()
        logger.info(f"Processed {len(upcoming_agenda_items)} upcoming agenda items")
        
    except Exception as e:
        logger.error(f"Error sending agenda notifications: {str(e)}")
        db.rollback()