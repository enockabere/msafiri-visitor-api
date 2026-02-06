from sqlalchemy.orm import Session
from app.models.visitor_enhancements import NotificationQueue, NotificationType
from app.db.database import SessionLocal
import json

def queue_notification(
    recipient_email: str,
    notification_type: NotificationType,
    title: str,
    message: str,
    data: dict = None
):
    """Queue a notification for sending"""
    db = SessionLocal()
    try:
        notification = NotificationQueue(
            recipient_email=recipient_email,
            notification_type=notification_type,
            title=title,
            message=message,
            data=json.dumps(data) if data else None
        )
        db.add(notification)
        db.commit()
        
        # Send email notification immediately
        from app.core.email_service import email_service
        email_service.send_notification_email(
            to_email=recipient_email,
            title=title,
            message=message,
            data=data
        )
        
    finally:
        db.close()

# Notification triggers for various events
def notify_pickup_confirmed(participant_email: str, pickup_details: dict):
    """Notify when pickup is confirmed"""
    queue_notification(
        recipient_email=participant_email,
        notification_type=NotificationType.PICKUP_CONFIRMED,
        title="Airport Pickup Confirmed",
        message=f"Your pickup has been confirmed for {pickup_details.get('pickup_time')}",
        data=pickup_details
    )

def notify_room_assigned(participant_email: str, room_details: dict):
    """Notify when room is assigned"""
    queue_notification(
        recipient_email=participant_email,
        notification_type=NotificationType.ROOM_ASSIGNED,
        title="Room Assignment",
        message=f"You've been assigned to {room_details.get('hotel_name')} - Room {room_details.get('room_number')}",
        data=room_details
    )

def notify_ride_assigned(participant_email: str, ride_details: dict):
    """Notify when ride is assigned"""
    queue_notification(
        recipient_email=participant_email,
        notification_type=NotificationType.RIDE_ASSIGNED,
        title="Event Transportation",
        message=f"Your ride to {ride_details.get('destination')} is confirmed",
        data=ride_details
    )

def notify_perdiem_approved(participant_email: str, perdiem_details: dict):
    """Notify when perdiem is approved"""
    queue_notification(
        recipient_email=participant_email,
        notification_type=NotificationType.PERDIEM_APPROVED,
        title="Perdiem Approved",
        message=f"Your perdiem request for ${perdiem_details.get('amount')} has been approved",
        data=perdiem_details
    )

def notify_equipment_fulfilled(participant_email: str, equipment_details: dict):
    """Notify when equipment request is fulfilled"""
    queue_notification(
        recipient_email=participant_email,
        notification_type=NotificationType.EQUIPMENT_FULFILLED,
        title="Equipment Ready",
        message=f"Your requested {equipment_details.get('equipment_name')} is ready for collection",
        data=equipment_details
    )

def notify_security_brief_added(participant_email: str, brief_details: dict):
    """Notify when new security brief is added"""
    queue_notification(
        recipient_email=participant_email,
        notification_type=NotificationType.SECURITY_BRIEF_ADDED,
        title="New Security Brief",
        message=f"New security information: {brief_details.get('title')}",
        data=brief_details
    )

def notify_event_reminder(participant_email: str, event_details: dict):
    """Notify event reminder"""
    queue_notification(
        recipient_email=participant_email,
        notification_type=NotificationType.EVENT_REMINDER,
        title="Event Reminder",
        message=f"Reminder: {event_details.get('event_title')} starts in {event_details.get('hours_until')} hours",
        data=event_details
    )
