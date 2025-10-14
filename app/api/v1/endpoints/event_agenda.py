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
    
    logger.info(f"🗓️ Get agenda - Event: {event_id}, User: {current_user.email}")
    logger.info(f"👤 User role: {current_user.role}")
    
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
        logger.info(f"✅ Participant access granted")
    else:
        logger.info(f"✅ Admin access granted")
    
    # Get real agenda data from database
    from app.models.event_agenda import EventAgenda
    
    agenda_items = db.query(EventAgenda).filter(
        EventAgenda.event_id == event_id
    ).order_by(EventAgenda.event_date, EventAgenda.time).all()
    
    # Convert to dict format expected by portal
    agenda_list = []
    for item in agenda_items:
        agenda_list.append({
            "id": item.id,
            "title": item.title or "",
            "description": item.description or "",
            "time": item.time or "",  # Portal expects 'time' field
            "start_time": item.time or "",
            "end_time": "",  # Not stored in current model
            "event_date": item.event_date.isoformat() if item.event_date else None,
            "day_number": item.day_number or 1,
            "event_id": item.event_id,
            "created_by": item.created_by or ""
        })
    
    logger.info(f"📊 Found {len(agenda_list)} agenda items")
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
    
    # Parse the agenda data
    title = agenda_data.get('title', '')
    description = agenda_data.get('description', '')
    time = agenda_data.get('time', '')
    event_date = agenda_data.get('event_date')
    day_number = agenda_data.get('day_number', 1)
    
    if not title or not time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title and time are required"
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
    
    # Create agenda item
    agenda_item = EventAgenda(
        event_id=event_id,
        title=title,
        description=description,
        time=time,
        event_date=event_date,
        day_number=day_number,
        created_by=current_user.email
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
    
    # Update fields if provided
    if 'title' in agenda_data:
        agenda_item.title = agenda_data['title']
    if 'description' in agenda_data:
        agenda_item.description = agenda_data['description']
    if 'time' in agenda_data:
        agenda_item.time = agenda_data['time']
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
    if 'day_number' in agenda_data:
        agenda_item.day_number = agenda_data['day_number']
    
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
    
    # Mock feedback submission - in real implementation, save to database
    logger.info(f"📊 Feedback: Rating={feedback_data.get('rating')}, Comment={feedback_data.get('comment')}")
    logger.info(f"✅ Agenda feedback submitted successfully")
    
    return {"message": "Feedback submitted successfully"}