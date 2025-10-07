# File: app/api/v1/endpoints/events.py
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.models.user_roles import UserRole as UserRoleModel, RoleType

router = APIRouter()

def can_create_events(user_role: UserRole) -> bool:
    """Check if user role can create events (any role with ADMIN except SUPER_ADMIN)"""
    admin_roles = [UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    return user_role in admin_roles

def can_create_events_by_relationship_roles(user_roles: List[UserRoleModel]) -> bool:
    """Check if user has admin roles in the relationship table"""
    admin_role_types = [RoleType.MT_ADMIN, RoleType.HR_ADMIN, RoleType.EVENT_ADMIN]
    return any(role.role in admin_role_types and role.is_active for role in user_roles)

@router.get("/published", response_model=List[schemas.Event])
def get_published_events(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get published events (public endpoint for mobile)."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🎯 === PUBLISHED EVENTS GET REQUEST START ===")
        logger.info(f"📊 Skip: {skip}, Limit: {limit}")
        
        # Get all published events regardless of tenant
        events = crud.event.get_published_events(db, skip=skip, limit=limit)
        logger.info(f"📊 Found {len(events)} published events")
        
        return events
        
    except Exception as e:
        logger.error(f"💥 PUBLISHED EVENTS GET ERROR: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/my-participation")
def check_my_event_participation(
    *,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Check if current user has any event participation."""
    from app.models.event_participant import EventParticipant
    
    # Check if user has any event participation (approved or confirmed)
    participation = db.query(EventParticipant).filter(
        EventParticipant.email == current_user.email,
        EventParticipant.status.in_(['approved', 'confirmed', 'checked_in'])
    ).first()
    
    return {
        "has_participation": participation is not None,
        "participant_id": participation.id if participation else None,
        "event_id": participation.event_id if participation else None,
        "status": participation.status if participation else None
    }

@router.get("/mobile/{event_id}", response_model=schemas.Event)
def get_event_for_mobile(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get specific event details for mobile (public endpoint)."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🎯 === MOBILE EVENT DETAILS REQUEST START ===")
        logger.info(f"📝 Event ID: {event_id}")
        
        event = crud.event.get(db, id=event_id)
        if not event:
            logger.error(f"❌ Event not found: {event_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Only return published events for mobile
        if event.status.lower() != 'published':
            logger.error(f"❌ Event not published: {event_id}, status: {event.status}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not available"
            )
        
        logger.info(f"✅ Returning event details for mobile: {event.title}")
        return event
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 MOBILE EVENT DETAILS ERROR: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/", response_model=schemas.Event)
def create_event(
    *,
    db: Session = Depends(get_db),
    event_in: schemas.EventCreate,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant: Optional[str] = None
) -> Any:
    """Create new event. Only admin roles can create events."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🎯 === EVENT CREATE REQUEST START ===")
        logger.info(f"📝 Event data: {event_in.dict()}")
        logger.info(f"👤 User: {current_user.email}, Role: {current_user.role}")
        logger.info(f"👤 Role type: {type(current_user.role)}, Role value: {current_user.role.value if hasattr(current_user.role, 'value') else 'NO_VALUE'}")
        logger.info(f"🏢 Tenant param: {tenant}")
        
        # Check user roles from relationship table
        user_roles = db.query(UserRoleModel).filter(
            UserRoleModel.user_id == current_user.id,
            UserRoleModel.is_active == True
        ).all()
        logger.info(f"🔐 User roles from relationship: {[role.role.value for role in user_roles]}")
        
        # Check if user has admin roles in the relationship table
        admin_role_types = [RoleType.MT_ADMIN, RoleType.HR_ADMIN, RoleType.EVENT_ADMIN]
        has_admin_role_in_relationship = any(role.role in admin_role_types for role in user_roles)
        logger.info(f"🔐 Has admin role in relationship table: {has_admin_role_in_relationship}")
        
        # Check permissions - check both single role and relationship roles
        has_single_role_permission = can_create_events(current_user.role)
        
        # Allow if either permission method grants access
        if not has_single_role_permission and not has_admin_role_in_relationship:
            logger.error(f"❌ Role check failed")
            logger.error(f"❌ Single role: {current_user.role} (valid: {has_single_role_permission})")
            logger.error(f"❌ Relationship roles: {[role.role.value for role in user_roles]} (valid: {has_admin_role_in_relationship})")
            logger.error(f"❌ Expected single roles: {[UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]}")
            logger.error(f"❌ Expected relationship roles: {[role.value for role in admin_role_types]}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin roles can create events"
            )
        else:
            logger.info(f"✅ Permission granted - Single role: {has_single_role_permission}, Relationship role: {has_admin_role_in_relationship}")
        
        # Use tenant parameter if available, otherwise fall back to user's tenant_id
        target_tenant = tenant or current_user.tenant_id
        
        if not target_tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to a tenant to create events"
            )
        
        # Convert tenant slug to tenant ID
        tenant_obj = crud.tenant.get_by_slug(db, slug=target_tenant)
        if not tenant_obj:
            logger.error(f"❌ Tenant not found: {target_tenant}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {target_tenant} not found"
            )
        
        logger.info(f"✅ Creating event for tenant: {target_tenant} (ID: {tenant_obj.id})")
        
        # Create event
        event = crud.event.create_with_tenant(
            db, 
            obj_in=event_in, 
            tenant_id=tenant_obj.id,
            created_by=current_user.email
        )
        
        # Send notifications to tenant admins
        from app.services.notification_service import send_event_notifications
        send_event_notifications(db, event, "created", current_user.email)
        
        db.commit()
        
        logger.info(f"🎉 Event created successfully with ID: {event.id}")
        return event
        
    except Exception as e:
        logger.error(f"💥 EVENT CREATE ERROR: {str(e)}")
        logger.exception("Full traceback:")
        raise

@router.get("/", response_model=List[schemas.Event])
def get_events(
    *,
    db: Session = Depends(get_db),
    tenant: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get events (no auth required for dashboard stats)."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🎯 === EVENTS GET REQUEST START ===")
        logger.info(f"🏢 Tenant param: {tenant}")
        logger.info(f"📊 Skip: {skip}, Limit: {limit}")
        
        # If no tenant specified, return all events
        if not tenant:
            logger.info(f"✅ Accessing all events (no tenant filter)")
            events = crud.event.get_multi(db, skip=skip, limit=limit)
            logger.info(f"📊 Found {len(events)} events (all tenants)")
            return events
        
        # Convert tenant slug to tenant ID if tenant is specified
        tenant_obj = crud.tenant.get_by_slug(db, slug=tenant)
        if not tenant_obj:
            logger.error(f"❌ Tenant not found: {tenant}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant} not found"
            )
        
        logger.info(f"✅ Fetching events for tenant: {tenant} (ID: {tenant_obj.id})")
        events = crud.event.get_by_tenant(
            db, tenant_id=tenant_obj.id, skip=skip, limit=limit
        )
        logger.info(f"📊 Found {len(events)} events for tenant {tenant}")
        logger.info(f"🎯 === EVENTS GET REQUEST END ===")
        return events
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 EVENTS GET ERROR: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/{event_id}", response_model=schemas.Event)
def get_event(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get specific event."""
    
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check if user can access this event (same tenant or super admin)
    if current_user.role != UserRole.SUPER_ADMIN and event.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access events from other tenants"
        )
    
    return event

@router.put("/{event_id}", response_model=schemas.Event)
def update_event(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    event_update: schemas.EventUpdate
) -> Any:
    """Update event."""
    
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    updated_event = crud.event.update(db, db_obj=event, obj_in=event_update)
    return updated_event

@router.delete("/{event_id}")
def delete_event(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Delete event (only allowed for draft events)."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🗑️ Delete event request - Event ID: {event_id}, User: {current_user.email}")
    
    event = crud.event.get(db, id=event_id)
    if not event:
        logger.error(f"❌ Event not found: {event_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    logger.info(f"📊 Event details - Status: {event.status}, Tenant: {event.tenant_id}")
    logger.info(f"👤 User details - Role: {current_user.role}, Tenant: {current_user.tenant_id}")
    
    # Only allow deletion of draft events
    if event.status.lower() != 'draft':
        logger.error(f"❌ Cannot delete non-draft event: {event.status}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft events can be deleted. Published events cannot be deleted."
        )
    
    # Check permissions using both role systems
    user_roles = db.query(UserRoleModel).filter(
        UserRoleModel.user_id == current_user.id,
        UserRoleModel.is_active == True
    ).all()
    
    logger.info(f"🔐 User roles from relationship: {[role.role.value for role in user_roles]}")
    
    has_single_role_permission = can_create_events(current_user.role)
    has_relationship_role_permission = can_create_events_by_relationship_roles(user_roles)
    
    logger.info(f"🔐 Single role permission: {has_single_role_permission}")
    logger.info(f"🔐 Relationship role permission: {has_relationship_role_permission}")
    
    if not has_single_role_permission and not has_relationship_role_permission:
        logger.error(f"❌ User lacks admin permissions")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin roles can delete events"
        )
    
    # Check if user can delete this event (same tenant)
    # Convert user's tenant slug to tenant ID for comparison
    user_tenant_obj = None
    if current_user.tenant_id:
        user_tenant_obj = crud.tenant.get_by_slug(db, slug=current_user.tenant_id)
    
    user_tenant_id = user_tenant_obj.id if user_tenant_obj else None
    logger.info(f"🏢 Tenant comparison - Event tenant_id: {event.tenant_id}, User tenant_id: {user_tenant_id} (from slug: {current_user.tenant_id})")
    
    if event.tenant_id != user_tenant_id:
        logger.error(f"❌ Tenant mismatch - Event: {event.tenant_id}, User: {user_tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete events from other tenants"
        )
    
    # Hard delete for draft events (since they haven't been published)
    logger.info(f"✅ Deleting draft event: {event_id}")
    db.delete(event)
    db.commit()
    logger.info(f"🎉 Event deleted successfully: {event_id}")
    return {"message": "Draft event deleted successfully"}

@router.put("/{event_id}/status")
def update_event_status(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    status_update: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update event status."""
    
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check permissions
    user_roles = db.query(UserRoleModel).filter(
        UserRoleModel.user_id == current_user.id,
        UserRoleModel.is_active == True
    ).all()
    
    has_single_role_permission = can_create_events(current_user.role)
    has_relationship_role_permission = can_create_events_by_relationship_roles(user_roles)
    
    if not has_single_role_permission and not has_relationship_role_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin roles can update event status"
        )
    
    # Update status
    new_status = status_update.get("status")
    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status is required"
        )
    
    crud.event.update(db, db_obj=event, obj_in={"status": new_status})
    return {"message": f"Event status updated to {new_status}", "status": new_status}

@router.get("/{event_id}/status/suggestions")
def get_status_suggestions(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get status suggestions for an event."""
    
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    suggestions = []
    if event.status == "Draft":
        suggestions.append({"status": "Published", "description": "Make event visible to participants"})
    elif event.status == "Published":
        suggestions.append({"status": "Ongoing", "description": "Mark event as currently happening"})
    elif event.status == "Ongoing":
        suggestions.append({"status": "Completed", "description": "Mark event as finished"})
    
    return {"suggestions": suggestions}

@router.post("/{event_id}/notify-update")
def notify_event_update(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Send notifications about event updates."""
    
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return {"message": "Notifications sent successfully"}

@router.get("/{event_id}/my-attendance-status")
def get_my_attendance_status(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get current user's attendance status for a specific event."""
    import logging
    logger = logging.getLogger(__name__)
    
    from app.models.event_participant import EventParticipant
    
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    logger.info(f"🎯 Get attendance status - Event: {event_id}, User: {current_user.email}")
    logger.info(f"📊 Found participation: {participation is not None}")
    if participation:
        logger.info(f"📊 Participation status: '{participation.status}'")
    
    return {
        "status": participation.status if participation else None,
        "participant_id": participation.id if participation else None,
        "requires_eta": participation.requires_eta if participation else False,
        "has_passport": bool(participation.passport_document) if participation else False,
        "has_ticket": bool(participation.ticket_document) if participation else False,
    }

@router.post("/{event_id}/request-attendance")
def request_event_attendance(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    registration_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Request to attend an event with registration details."""
    from app.models.event_participant import EventParticipant
    
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check if event is published and active
    if event.status.lower() != 'published':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event is not open for registration"
        )
    
    from datetime import datetime
    if event.end_date < datetime.now().date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event has already ended"
        )
    
    # Check if user already requested attendance
    existing = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if existing:
        return {
            "message": f"Attendance request already exists with status: {existing.status}",
            "status": existing.status,
            "participant_id": existing.id
        }
    
    # Update user profile with registration data
    if registration_data.get('country'):
        current_user.country = registration_data['country']
    if registration_data.get('position'):
        current_user.position = registration_data['position']
    if registration_data.get('project'):
        current_user.project = registration_data['project']
    if registration_data.get('gender'):
        current_user.gender = registration_data['gender']
    
    # Create attendance request with additional data
    participant = EventParticipant(
        event_id=event_id,
        full_name=current_user.full_name,
        email=current_user.email,
        role='attendee',
        status='requested',
        invited_by=current_user.email,
        country=registration_data.get('country'),
        position=registration_data.get('position'),
        project=registration_data.get('project'),
        gender=registration_data.get('gender'),
        eta=registration_data.get('eta') if registration_data.get('requires_eta') else None,
        requires_eta=registration_data.get('requires_eta', False)
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    
    return {
        "message": "Registration submitted successfully",
        "status": "requested",
        "participant_id": participant.id
    }

@router.post("/{event_id}/confirm-attendance")
def confirm_event_attendance(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Confirm attendance for an approved event."""
    import logging
    logger = logging.getLogger(__name__)
    
    from app.models.event_participant import EventParticipant
    from app.models.notification import Notification, NotificationPriority, NotificationType
    
    # Find the user's participation record
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    logger.info(f"🎯 Confirm attendance - Event: {event_id}, User: {current_user.email}")
    
    if not participation:
        logger.error(f"❌ No participation record found for user {current_user.email} in event {event_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No participation record found"
        )
    
    logger.info(f"📊 Current participation status: '{participation.status}'")
    logger.info(f"📊 Checking if status '{participation.status}' is in ['approved', 'selected']")
    
    if participation.status not in ['approved', 'selected']:
        logger.error(f"❌ Invalid status for confirmation: '{participation.status}' (expected 'approved' or 'selected')")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only confirm attendance for approved or selected participants. Current status: {participation.status}"
        )
    
    # Update status to confirmed
    logger.info(f"✅ Updating status from '{participation.status}' to 'confirmed'")
    participation.status = 'confirmed'
    
    db.commit()
    
    return {
        "message": "Attendance confirmed successfully",
        "status": "confirmed"
    }

@router.post("/{event_id}/upload-document")
def upload_event_document(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    document_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Upload document for event participation."""
    import base64
    import os
    from pathlib import Path
    
    # Validate participation
    from app.models.event_participant import EventParticipant
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No participation record found"
        )
    
    document_type = document_data.get('document_type')
    file_name = document_data.get('file_name')
    file_data = document_data.get('file_data')
    file_extension = document_data.get('file_extension')
    
    if not all([document_type, file_name, file_data, file_extension]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required document data"
        )
    
    try:
        # Decode base64
        file_bytes = base64.b64decode(file_data)
        
        # Create upload directory
        upload_dir = Path(f"uploads/events/{event_id}/participants/{participation.id}")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = upload_dir / f"{document_type}_{participation.id}.{file_extension}"
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        
        # Update participation record
        if document_type == 'passport':
            participation.passport_document = str(file_path)
        elif document_type == 'ticket':
            participation.ticket_document = str(file_path)
        
        db.commit()
        
        return {
            "message": f"{document_type.title()} uploaded successfully",
            "file_path": str(file_path)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )