from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.event_participant import EventParticipant
from sqlalchemy import text

router = APIRouter()

@router.get("/{event_id}/agenda")
def get_event_agenda(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get event agenda items."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if user is admin (can view any event agenda)
    from app.models.user import UserRole
    admin_roles = [UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN, UserRole.SUPER_ADMIN]
    
    if current_user.role not in admin_roles:
        # Check if user has access to this event as participant
        participation = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.email == current_user.email,
            EventParticipant.status.in_(['selected', 'approved', 'confirmed', 'checked_in'])
        ).first()
        
        if not participation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - not a participant of this event"
            )
    
    # Get real agenda data from database
    from app.models.event_agenda import EventAgenda
    
    agenda_items = db.query(EventAgenda).filter(
        EventAgenda.event_id == event_id
    ).order_by(EventAgenda.event_date, EventAgenda.time).all()
    
    # Convert to dict format expected by portal
    agenda_list = []
    for item in agenda_items:
        # Create datetime strings for portal compatibility
        event_date_str = item.event_date.isoformat() if item.event_date else "2024-01-01"
        time_str = item.time or "09:00"
        end_time_str = item.end_time if hasattr(item, 'end_time') and item.end_time else time_str
        start_datetime = f"{event_date_str}T{time_str}:00"
        end_datetime = f"{event_date_str}T{end_time_str}:00"

        agenda_list.append({
            "id": item.id,
            "title": item.title or "",
            "description": item.description or "",
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "location": "",  # Not stored in current model
            "presenter": item.created_by or "",  # Use created_by as presenter for speaker display
            "session_number": f"Session {item.id}",  # Generate session number
            "created_by": item.created_by or "",
            "created_at": start_datetime  # Use start_datetime as created_at
        })
    

    return agenda_list

@router.get("/{event_id}/my-role")
def get_my_event_role(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get current user's role in the event."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"👤 Get user role - Event: {event_id}, User: {current_user.email}")
    
    # Check participation and role
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not a participant of this event"
        )
    
    # Check both role and participant_role fields
    role = participation.role
    if hasattr(participation, 'participant_role') and participation.participant_role:
        role = participation.participant_role
    
    logger.info(f"📊 User role: {role}")
    return {"role": role}

@router.post("/{event_id}/agenda")
def create_agenda_item(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Create new agenda item (facilitators and admins)."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"➕ Create agenda item - Event: {event_id}, User: {current_user.email}")
    logger.info(f"👤 User role: {current_user.role}")
    logger.info(f"📝 Received agenda data: {agenda_data}")
    
    # Check if event has ended
    from app.models.event import Event
    from datetime import date
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if event.end_date and event.end_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot add agenda items to ended events"
        )
    
    # Check if user is admin (can manage any event)
    from app.models.user import UserRole
    admin_roles = [UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN, UserRole.SUPER_ADMIN]
    
    if current_user.role in admin_roles:
        logger.info(f"✅ Admin user can create agenda items")
    else:
        # Check if user is a facilitator for this specific event
        participation = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.email == current_user.email
        ).first()
        
        if not participation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - not a participant of this event"
            )
        
        # Check if user is facilitator
        role = participation.role
        if hasattr(participation, 'participant_role') and participation.participant_role:
            role = participation.participant_role
        
        logger.info(f"👤 Participant role: {role}")
        
        if role != 'facilitator':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - only facilitators and admins can manage agenda"
            )
    
    # Create real agenda item in database
    from app.models.event_agenda import EventAgenda
    from datetime import datetime
    
    # Parse the agenda data - handle both portal and mobile formats
    title = agenda_data.get('title', '')
    description = agenda_data.get('description', '')
    day_number = agenda_data.get('day_number', 1)
    
    # Handle time from different sources
    time = agenda_data.get('time', '')
    start_time = agenda_data.get('start_time', '')
    if start_time:
        time = start_time
    elif not time and 'start_datetime' in agenda_data:
        # Extract time from start_datetime (portal format)
        try:
            start_dt = datetime.fromisoformat(agenda_data['start_datetime'].replace('Z', '+00:00'))
            time = start_dt.strftime('%H:%M')
        except:
            time = '09:00'

    # Handle end_time from different sources
    end_time = agenda_data.get('end_time', '')
    if not end_time and 'end_datetime' in agenda_data:
        # Extract end time from end_datetime (portal format)
        try:
            end_dt = datetime.fromisoformat(agenda_data['end_datetime'].replace('Z', '+00:00'))
            end_time = end_dt.strftime('%H:%M')
        except:
            end_time = None
    
    # Handle event_date from different sources
    event_date = agenda_data.get('event_date')
    if not event_date and 'start_datetime' in agenda_data:
        # Extract date from start_datetime (portal format)
        try:
            start_dt = datetime.fromisoformat(agenda_data['start_datetime'].replace('Z', '+00:00'))
            event_date = start_dt.date()
        except:
            event_date = None
    
    # If no event_date, calculate from day_number and event start date
    if not event_date and day_number:
        from app.models.event import Event
        event = db.query(Event).filter(Event.id == event_id).first()
        if event and event.start_date:
            from datetime import timedelta
            event_date = event.start_date + timedelta(days=day_number - 1)
            logger.info(f"📅 Calculated event_date: {event_date} from day_number: {day_number}")
    
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title is required"
        )
    
    # Parse event_date if provided as string
    if isinstance(event_date, str):
        try:
            event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    # Default time if not provided
    if not time:
        time = '09:00'
    
    # Handle speaker/presenter field from both portal and mobile
    speaker = agenda_data.get('speaker', '')
    presenter = agenda_data.get('presenter', '')
    if speaker:
        # Store speaker name in created_by field since we don't have a separate presenter field
        created_by = speaker
    elif presenter:
        # Store presenter name from mobile app
        created_by = presenter
    else:
        created_by = current_user.email
    
    # Create agenda item
    agenda_item = EventAgenda(
        event_id=event_id,
        title=title,
        description=description,
        time=time,
        end_time=end_time,
        event_date=event_date,
        day_number=day_number,
        created_by=created_by
    )
    
    db.add(agenda_item)
    db.commit()
    db.refresh(agenda_item)
    
    logger.info(f"✅ Agenda item created successfully with ID: {agenda_item.id}")
    return {"message": "Agenda item created successfully", "id": agenda_item.id}

@router.put("/{event_id}/agenda/{agenda_id}")
def update_agenda_item(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_id: int,
    agenda_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update agenda item (facilitators and admins)."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"✏️ Update agenda item - Event: {event_id}, Agenda: {agenda_id}, User: {current_user.email}")
    
    # Check if event has ended
    from app.models.event import Event
    from datetime import date
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if event.end_date and event.end_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify agenda items for ended events"
        )
    
    # Check if user is admin (can manage any event)
    from app.models.user import UserRole
    admin_roles = [UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN, UserRole.SUPER_ADMIN]
    
    if current_user.role in admin_roles:
        logger.info(f"✅ Admin user can update agenda items")
    else:
        # Check if user is a facilitator for this specific event
        participation = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.email == current_user.email
        ).first()
        
        if not participation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - not a participant of this event"
            )
        
        role = participation.role
        if hasattr(participation, 'participant_role') and participation.participant_role:
            role = participation.participant_role
        
        if role != 'facilitator':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - only facilitators and admins can manage agenda"
            )
    
    # Update real agenda item in database
    from app.models.event_agenda import EventAgenda
    from datetime import datetime
    
    # Find the agenda item
    agenda_item = db.query(EventAgenda).filter(
        EventAgenda.id == agenda_id,
        EventAgenda.event_id == event_id
    ).first()
    
    if not agenda_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda item not found"
        )
    
    # Update fields if provided - handle both portal and mobile formats
    if 'title' in agenda_data:
        agenda_item.title = agenda_data['title']
    if 'description' in agenda_data:
        agenda_item.description = agenda_data['description']
    
    # Handle time from different sources
    if 'time' in agenda_data:
        agenda_item.time = agenda_data['time']
    elif 'start_datetime' in agenda_data:
        try:
            start_dt = datetime.fromisoformat(agenda_data['start_datetime'].replace('Z', '+00:00'))
            agenda_item.time = start_dt.strftime('%H:%M')
        except:
            pass

    # Handle end_time from different sources
    if 'end_time' in agenda_data:
        agenda_item.end_time = agenda_data['end_time']
    elif 'end_datetime' in agenda_data:
        try:
            end_dt = datetime.fromisoformat(agenda_data['end_datetime'].replace('Z', '+00:00'))
            agenda_item.end_time = end_dt.strftime('%H:%M')
        except:
            pass
    
    # Handle event_date from different sources
    if 'event_date' in agenda_data:
        event_date = agenda_data['event_date']
        if isinstance(event_date, str):
            try:
                agenda_item.event_date = datetime.strptime(event_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        else:
            agenda_item.event_date = event_date
    elif 'start_datetime' in agenda_data:
        try:
            start_dt = datetime.fromisoformat(agenda_data['start_datetime'].replace('Z', '+00:00'))
            agenda_item.event_date = start_dt.date()
        except:
            pass
    
    if 'day_number' in agenda_data:
        agenda_item.day_number = agenda_data['day_number']
    
    # Handle speaker field from portal
    if 'speaker' in agenda_data:
        # Store speaker in created_by field since we don't have a separate presenter field in the model
        if agenda_data['speaker']:
            agenda_item.created_by = agenda_data['speaker']
    
    db.commit()
    
    logger.info(f"✅ Agenda item updated successfully")
    return {"message": "Agenda item updated successfully"}

@router.delete("/{event_id}/agenda/{agenda_id}")
def delete_agenda_item(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Delete agenda item (facilitators and admins)."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🗑️ Delete agenda item - Event: {event_id}, Agenda: {agenda_id}, User: {current_user.email}")
    
    # Check if event has ended
    from app.models.event import Event
    from datetime import date
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    if event.end_date and event.end_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete agenda items from ended events"
        )
    
    # Check if user is admin (can manage any event)
    from app.models.user import UserRole
    admin_roles = [UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN, UserRole.SUPER_ADMIN]
    
    if current_user.role in admin_roles:
        logger.info(f"✅ Admin user can delete agenda items")
    else:
        # Check if user is a facilitator for this specific event
        participation = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.email == current_user.email
        ).first()
        
        if not participation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - not a participant of this event"
            )
        
        role = participation.role
        if hasattr(participation, 'participant_role') and participation.participant_role:
            role = participation.participant_role
        
        if role != 'facilitator':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - only facilitators and admins can manage agenda"
            )
    
    # Delete real agenda item from database
    from app.models.event_agenda import EventAgenda
    
    # Find the agenda item
    agenda_item = db.query(EventAgenda).filter(
        EventAgenda.id == agenda_id,
        EventAgenda.event_id == event_id
    ).first()
    
    if not agenda_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agenda item not found"
        )
    
    db.delete(agenda_item)
    db.commit()
    
    logger.info(f"✅ Agenda item deleted successfully")
    return {"message": "Agenda item deleted successfully"}

@router.post("/{event_id}/agenda/{agenda_id}/feedback")
def submit_agenda_feedback(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_id: int,
    feedback_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Submit feedback for an agenda item."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"💬 Submit agenda feedback - Event: {event_id}, Agenda: {agenda_id}, User: {current_user.email}")
    
    # Check if user has access to this event
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email,
        EventParticipant.status.in_(['selected', 'approved', 'confirmed', 'checked_in'])
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - not a participant of this event"
        )
    
    # Check if agenda item exists in database
    from app.models.event_agenda import EventAgenda
    
    agenda_item = db.query(EventAgenda).filter(
        EventAgenda.id == agenda_id,
        EventAgenda.event_id == event_id
    ).first()
    
    if not agenda_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agenda item {agenda_id} not found"
        )
    
    # Check if user is not a facilitator (facilitators shouldn't give feedback)
    role = participation.role
    if hasattr(participation, 'participant_role') and participation.participant_role:
        role = participation.participant_role
    
    if role == 'facilitator':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Facilitators cannot submit feedback"
        )
    
    # Save feedback to database
    from app.models.agenda_feedback import AgendaFeedback
    
    # Check if user already submitted feedback for this agenda
    existing_feedback = db.query(AgendaFeedback).filter(
        AgendaFeedback.agenda_id == agenda_id,
        AgendaFeedback.user_email == current_user.email
    ).first()
    
    if existing_feedback:
        # Update existing feedback
        existing_feedback.rating = feedback_data.get('rating', 5.0)
        existing_feedback.comment = feedback_data.get('comment', '')
        db.commit()
        feedback_id = existing_feedback.id
    else:
        # Create new feedback
        feedback = AgendaFeedback(
            agenda_id=agenda_id,
            user_email=current_user.email,
            rating=feedback_data.get('rating', 5.0),
            comment=feedback_data.get('comment', '')
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        feedback_id = feedback.id
    
    # Send notification to facilitators
    try:
        from app.crud.notification import create_notification
        
        # Get facilitators for this event
        facilitators = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.participant_role == 'facilitator'
        ).all()
        
        # Create notification for each facilitator
        for facilitator in facilitators:
            create_notification(
                db=db,
                recipient_email=facilitator.email,
                title="New Agenda Feedback",
                message=f"New feedback received for '{agenda_item.title}' from {current_user.email}",
                notification_type="agenda_feedback",
                related_id=feedback_id
            )
        
        logger.info(f"📧 Sent feedback notifications to {len(facilitators)} facilitators")
    except Exception as e:
        logger.error(f"❌ Error sending feedback notifications: {e}")
    
    logger.info(f"✅ Agenda feedback submitted successfully with ID: {feedback_id}")
    return {"message": "Feedback submitted successfully", "feedback_id": feedback_id}

@router.get("/{event_id}/agenda/{agenda_id}/feedback")
def get_agenda_feedback(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get feedback for an agenda item."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"📖 Get agenda feedback - Event: {event_id}, Agenda: {agenda_id}, User: {current_user.email}")
    
    # Check if user has access to this event
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email,
        EventParticipant.status.in_(['selected', 'approved', 'confirmed', 'checked_in'])
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - not a participant of this event"
        )
    
    # Check if agenda item exists
    from app.models.event_agenda import EventAgenda
    
    agenda_item = db.query(EventAgenda).filter(
        EventAgenda.id == agenda_id,
        EventAgenda.event_id == event_id
    ).first()
    
    if not agenda_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agenda item {agenda_id} not found"
        )
    
    # Get user's feedback for this agenda item
    from app.models.agenda_feedback import AgendaFeedback, FeedbackResponse
    
    feedback = db.query(AgendaFeedback).filter(
        AgendaFeedback.agenda_id == agenda_id,
        AgendaFeedback.user_email == current_user.email
    ).first()
    
    if not feedback:
        return []
    
    # Get responses for this feedback
    responses = db.query(FeedbackResponse).filter(
        FeedbackResponse.feedback_id == feedback.id
    ).all()
    
    # Format response
    feedback_data = {
        "id": feedback.id,
        "rating": feedback.rating,
        "comment": feedback.comment,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
        "responses": [
            {
                "id": resp.id,
                "responder_email": resp.responder_email,
                "response_text": resp.response_text,
                "is_like": resp.is_like,
                "created_at": resp.created_at.isoformat() if resp.created_at else None
            }
            for resp in responses
        ]
    }
    
    logger.info(f"📊 Found feedback with {len(responses)} responses")
    return [feedback_data]

@router.post("/{event_id}/agenda/{agenda_id}/feedback/{feedback_id}/respond")
def respond_to_feedback(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    agenda_id: int,
    feedback_id: int,
    response_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Respond to agenda feedback (facilitators only)."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"💬 Respond to feedback - Event: {event_id}, Agenda: {agenda_id}, Feedback: {feedback_id}, User: {current_user.email}")
    
    # Check if user is facilitator for this event
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - not a participant of this event"
        )
    
    role = participation.role
    if hasattr(participation, 'participant_role') and participation.participant_role:
        role = participation.participant_role
    
    if role != 'facilitator':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied - only facilitators can respond to feedback"
        )
    
    # Check if feedback exists
    from app.models.agenda_feedback import AgendaFeedback, FeedbackResponse
    
    feedback = db.query(AgendaFeedback).filter(
        AgendaFeedback.id == feedback_id,
        AgendaFeedback.agenda_id == agenda_id
    ).first()
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    # Create response
    response = FeedbackResponse(
        feedback_id=feedback_id,
        responder_email=current_user.email,
        response_text=response_data.get('response_text', ''),
        is_like=response_data.get('is_like', False)
    )
    
    db.add(response)
    db.commit()
    db.refresh(response)
    
    # Send notification to feedback author
    try:
        from app.crud.notification import create_notification
        
        response_type = "liked" if response.is_like else "replied to"
        create_notification(
            db=db,
            recipient_email=feedback.user_email,
            title="Facilitator Response",
            message=f"Facilitator {current_user.email} {response_type} your feedback",
            notification_type="feedback_response",
            related_id=response.id
        )
        
        logger.info(f"📧 Sent response notification to {feedback.user_email}")
    except Exception as e:
        logger.error(f"❌ Error sending response notification: {e}")
    
    logger.info(f"✅ Feedback response created successfully with ID: {response.id}")
    return {"message": "Response submitted successfully", "response_id": response.id}