# File: app/api/v1/endpoints/events.py
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
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
        EventParticipant.email.ilike(current_user.email),
        EventParticipant.status.in_(['approved', 'confirmed', 'checked_in'])
    ).first()
    
    return {
        "has_participation": participation is not None,
        "participant_id": participation.id if participation else None,
        "event_id": participation.event_id if participation else None,
        "status": participation.status if participation else None
    }

@router.get("/my-events", response_model=List[schemas.Event])
def get_my_selected_events(
    *,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get events that the current user is selected for (mobile endpoint)."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🎯 === MY EVENTS REQUEST START ===")
        logger.info(f"👤 User: {current_user.email}")
        logger.info(f"📊 Skip: {skip}, Limit: {limit}")
        
        from app.models.event_participant import EventParticipant
        from app.models.event import Event
        
        # Get events where user is selected/approved/confirmed (exclude declined)
        selected_statuses = ['selected', 'approved', 'confirmed', 'checked_in']
        
        # Query to get events through participation (excluding declined)
        events_query = db.query(Event).join(
            EventParticipant, Event.id == EventParticipant.event_id
        ).filter(
            EventParticipant.email.ilike(current_user.email),
            EventParticipant.status.in_(selected_statuses)
        ).distinct()
        
        events = events_query.offset(skip).limit(limit).all()
        
        logger.info(f"📊 Found {len(events)} events for user {current_user.email} (declined events excluded)")
        logger.info(f"🎯 === MY EVENTS REQUEST END ===")
        
        return events
        
    except Exception as e:
        logger.error(f"💥 MY EVENTS ERROR: {str(e)}")
        logger.exception("Full traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

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

@router.get("/{event_id}/public", response_model=schemas.Event)
def get_event_public(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get specific event details for public registration (no auth required)."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🎯 === PUBLIC EVENT DETAILS REQUEST START ===")
        logger.info(f"📝 Event ID: {event_id}")
        
        event = crud.event.get(db, id=event_id)
        if not event:
            logger.error(f"❌ Event not found: {event_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        logger.info(f"✅ Returning public event details: {event.title}")
        return event
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 PUBLIC EVENT DETAILS ERROR: {str(e)}")
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
        try:
            event = crud.event.create_with_tenant(
                db, 
                obj_in=event_in, 
                tenant_id=tenant_obj.id,
                created_by=current_user.email
            )
        except Exception as e:
            if "duplicate key value violates unique constraint" in str(e).lower() and "title" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An event with this title already exists. Please choose a different title."
                )
            raise e
        
        # Send notifications to tenant admins
        from app.services.notification_service import send_event_notifications
        send_event_notifications(db, event, "created", current_user.email)
        
        # Auto-create chat room for the event
        try:
            from app.models.chat import ChatRoom, ChatType
            
            chat_room = ChatRoom(
                name=f"{event.title} - Event Chat",
                chat_type=ChatType.EVENT_CHATROOM,
                event_id=event.id,
                tenant_id=tenant_obj.id,
                created_by=current_user.id
            )
            db.add(chat_room)
            logger.info(f"✅ Auto-created chat room for event: {event.title}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create chat room for event: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Auto-create vendor event accommodation setup if vendor is specified
        try:
            if event.vendor_accommodation_id and event.single_rooms is not None and event.double_rooms is not None:
                from app.models.guesthouse import VendorEventAccommodation
                
                # Check if setup already exists
                existing_setup = db.query(VendorEventAccommodation).filter(
                    VendorEventAccommodation.vendor_accommodation_id == event.vendor_accommodation_id,
                    VendorEventAccommodation.event_id == event.id,
                    VendorEventAccommodation.tenant_id == tenant_obj.id
                ).first()
                
                if not existing_setup:
                    total_capacity = event.single_rooms + (event.double_rooms * 2)
                    
                    vendor_setup = VendorEventAccommodation(
                        tenant_id=tenant_obj.id,
                        vendor_accommodation_id=event.vendor_accommodation_id,
                        event_id=event.id,
                        event_name=event.title,
                        single_rooms=event.single_rooms,
                        double_rooms=event.double_rooms,
                        total_capacity=total_capacity,
                        current_occupants=0,
                        is_active=True,
                        created_by=current_user.email
                    )
                    
                    db.add(vendor_setup)
                    logger.info(f"✅ Auto-created vendor event accommodation setup for event: {event.title}")
                    logger.info(f"📊 Room allocation: {event.single_rooms} single, {event.double_rooms} double rooms")
                    
                    # Refresh automatic room booking for any existing confirmed participants
                    try:
                        from app.services.automatic_room_booking_service import refresh_automatic_room_booking
                        refresh_automatic_room_booking(db, event.id, tenant_obj.id)
                    except Exception as booking_error:
                        logger.warning(f"⚠️ Failed to refresh room booking during event creation: {str(booking_error)}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create vendor event accommodation setup: {str(e)}")
            import traceback
            traceback.print_exc()
        
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
    
    # If no tenant specified, return all events
    if not tenant:
        events = crud.event.get_multi(db, skip=skip, limit=limit)
        return events
    
    # Convert tenant slug to tenant ID if tenant is specified
    tenant_obj = crud.tenant.get_by_slug(db, slug=tenant)
    if not tenant_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant} not found"
        )
    
    events = crud.event.get_by_tenant(
        db, tenant_id=tenant_obj.id, skip=skip, limit=limit
    )
    return events

@router.get("/{event_id}", response_model=schemas.Event)
def get_event(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant: Optional[str] = Query(None)
) -> Any:
    """Get specific event."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🎯 === GET EVENT REQUEST START ===")
    logger.info(f"📝 Event ID: {event_id}")
    logger.info(f"👤 User: {current_user.email}")
    logger.info(f"🏢 Tenant param: {tenant}")
    logger.info(f"👤 User tenant_id: {current_user.tenant_id}")
    logger.info(f"👤 User role: {current_user.role}")
    
    event = crud.event.get(db, id=event_id)
    if not event:
        logger.error(f"❌ Event not found: {event_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    logger.info(f"📊 Event found - Title: {event.title}, Tenant ID: {event.tenant_id}")
    
    # If tenant parameter is provided, use it for access control
    if tenant:
        logger.info(f"🔍 Using tenant parameter for access control: {tenant}")
        tenant_obj = crud.tenant.get_by_slug(db, slug=tenant)
        if not tenant_obj:
            logger.error(f"❌ Tenant not found: {tenant}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant} not found"
            )
        
        logger.info(f"🏢 Tenant found - Name: {tenant_obj.name}, ID: {tenant_obj.id}")
        
        # Check if event belongs to the specified tenant
        if event.tenant_id != tenant_obj.id:
            logger.error(f"❌ Event {event_id} belongs to tenant {event.tenant_id}, not {tenant_obj.id}")
            logger.error(f"❌ Event tenant_id type: {type(event.tenant_id)}, Tenant obj ID type: {type(tenant_obj.id)}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access events from other tenants"
            )
        
        logger.info(f"✅ Access granted via tenant parameter: {tenant}")
        logger.info(f"🎯 === GET EVENT REQUEST END (SUCCESS) ===")
        return event
    
    # Check if user can access this event (same tenant or super admin)
    logger.info(f"🔍 Using user-based access control")
    if current_user.role != UserRole.SUPER_ADMIN:
        # Convert user's tenant slug to tenant ID for comparison
        user_tenant_obj = None
        if current_user.tenant_id:
            user_tenant_obj = crud.tenant.get_by_slug(db, slug=current_user.tenant_id)
        
        user_tenant_id = user_tenant_obj.id if user_tenant_obj else None
        
        logger.info(f"🔍 Tenant check - Event tenant: {event.tenant_id}, User tenant: {user_tenant_id} (from slug: {current_user.tenant_id})")
        logger.info(f"🔍 Event tenant_id type: {type(event.tenant_id)}, User tenant_id type: {type(user_tenant_id)}")
        
        if event.tenant_id != user_tenant_id:
            logger.error(f"❌ Tenant mismatch - Event: {event.tenant_id}, User: {user_tenant_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access events from other tenants"
            )
    
    logger.info(f"✅ Access granted - Event: {event_id}")
    logger.info(f"🎯 === GET EVENT REQUEST END (SUCCESS) ===")
    return event

@router.put("/{event_id}", response_model=schemas.Event)
def update_event(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    event_update: schemas.EventUpdate,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update event."""
    import logging
    logger = logging.getLogger(__name__)
    
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    logger.info(f"🔄 Updating event {event_id}: {event.title}")
    
    # Check if room allocation is being updated
    room_allocation_changed = False
    old_single_rooms = event.single_rooms
    old_double_rooms = event.double_rooms
    old_vendor_id = event.vendor_accommodation_id
    
    # Get the update data
    update_data = event_update.dict(exclude_unset=True)
    new_single_rooms = update_data.get('single_rooms', old_single_rooms)
    new_double_rooms = update_data.get('double_rooms', old_double_rooms)
    new_vendor_id = update_data.get('vendor_accommodation_id', old_vendor_id)
    
    if (old_single_rooms != new_single_rooms or 
        old_double_rooms != new_double_rooms or 
        old_vendor_id != new_vendor_id):
        room_allocation_changed = True
        logger.info(f"🏨 Room allocation changed:")
        logger.info(f"   Single rooms: {old_single_rooms} → {new_single_rooms}")
        logger.info(f"   Double rooms: {old_double_rooms} → {new_double_rooms}")
        logger.info(f"   Vendor ID: {old_vendor_id} → {new_vendor_id}")
    
    # Update the event
    updated_event = crud.event.update(db, db_obj=event, obj_in=event_update)
    
    # Refresh vendor event accommodation setup if room allocation changed
    if room_allocation_changed and new_vendor_id:
        try:
            from app.models.guesthouse import VendorEventAccommodation
            
            logger.info(f"🔄 Refreshing vendor event accommodation setup...")
            
            # Find existing setup
            existing_setup = db.query(VendorEventAccommodation).filter(
                VendorEventAccommodation.event_id == event_id,
                VendorEventAccommodation.tenant_id == updated_event.tenant_id
            ).first()
            
            if existing_setup:
                # Check if we can update (no current occupants or reducing capacity safely)
                new_total_capacity = new_single_rooms + (new_double_rooms * 2)
                
                if existing_setup.current_occupants > new_total_capacity:
                    logger.warning(f"⚠️ Cannot reduce capacity below current occupants ({existing_setup.current_occupants})")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot reduce room capacity below current occupants ({existing_setup.current_occupants}). Please reassign participants first."
                    )
                
                # Update existing setup
                existing_setup.vendor_accommodation_id = new_vendor_id
                existing_setup.single_rooms = new_single_rooms
                existing_setup.double_rooms = new_double_rooms
                existing_setup.total_capacity = new_total_capacity
                existing_setup.event_name = updated_event.title
                
                logger.info(f"✅ Updated existing vendor event accommodation setup")
                logger.info(f"📊 New allocation: {new_single_rooms} single, {new_double_rooms} double rooms")
                
            else:
                # Create new setup if none exists
                if new_single_rooms is not None and new_double_rooms is not None:
                    total_capacity = new_single_rooms + (new_double_rooms * 2)
                    
                    vendor_setup = VendorEventAccommodation(
                        tenant_id=updated_event.tenant_id,
                        vendor_accommodation_id=new_vendor_id,
                        event_id=event_id,
                        event_name=updated_event.title,
                        single_rooms=new_single_rooms,
                        double_rooms=new_double_rooms,
                        total_capacity=total_capacity,
                        current_occupants=0,
                        is_active=True,
                        created_by=current_user.email
                    )
                    
                    db.add(vendor_setup)
                    logger.info(f"✅ Created new vendor event accommodation setup")
                    logger.info(f"📊 Room allocation: {new_single_rooms} single, {new_double_rooms} double rooms")
            
            db.commit()
            
            # Refresh automatic room booking for confirmed participants
            try:
                from app.services.automatic_room_booking_service import refresh_automatic_room_booking
                
                logger.info(f"🔄 Refreshing automatic room assignments...")
                success = refresh_automatic_room_booking(db, event_id, updated_event.tenant_id)
                
                if success:
                    logger.info(f"✅ Automatic room booking refresh completed successfully")
                else:
                    logger.warning(f"⚠️ Automatic room booking refresh failed")
                    
            except Exception as e:
                logger.error(f"💥 Error during automatic room booking refresh: {str(e)}")
                # Don't fail the update if room reassignment fails
                logger.warning(f"⚠️ Event updated but automatic room reassignment failed")
            
            logger.info(f"🔄 Room booking refresh completed for event {event_id}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"💥 Failed to refresh vendor event accommodation setup: {str(e)}")
            # Don't fail the entire update if accommodation setup fails
            logger.warning(f"⚠️ Event updated but accommodation setup refresh failed")
            import traceback
            traceback.print_exc()
    
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
    
    # Delete related records that don't have proper cascade relationships
    try:
        from app.models.guesthouse import AccommodationAllocation
        from app.models.flight_itinerary import FlightItinerary
        from app.models.participant_qr import ParticipantQR
        from app.models.event_participant import EventParticipant

        # 1. Delete transport requests first (they reference flight_itineraries) - if table exists
        try:
            from app.models.transport_request import TransportRequest
            transport_requests = db.query(TransportRequest).filter(
                TransportRequest.event_id == event_id
            ).all()
            for request in transport_requests:
                db.delete(request)
            logger.info(f"🗑️ Deleted {len(transport_requests)} transport requests for event {event_id}")
        except Exception as e:
            # Table might not exist yet, rollback and continue
            logger.warning(f"⚠️ Could not delete transport requests (table may not exist): {str(e)}")
            db.rollback()  # Rollback the failed transaction to continue with other deletions
        
        # 2. Delete participant QR codes (they reference event_participants)
        try:
            qr_codes = db.query(ParticipantQR).join(
                EventParticipant, ParticipantQR.participant_id == EventParticipant.id
            ).filter(EventParticipant.event_id == event_id).all()
            for qr_code in qr_codes:
                db.delete(qr_code)
            logger.info(f"🗑️ Deleted {len(qr_codes)} participant QR codes for event {event_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete participant QR codes (table may not exist): {str(e)}")
            db.rollback()

        # 3. Delete accommodation allocations (they reference event_participants)
        try:
            allocations = db.query(AccommodationAllocation).filter(
                AccommodationAllocation.event_id == event_id
            ).all()
            for allocation in allocations:
                db.delete(allocation)
            logger.info(f"🗑️ Deleted {len(allocations)} accommodation allocations for event {event_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete accommodation allocations (table may not exist): {str(e)}")
            db.rollback()

        # 4. Delete flight itineraries
        try:
            flight_itineraries = db.query(FlightItinerary).filter(
                FlightItinerary.event_id == event_id
            ).all()
            for itinerary in flight_itineraries:
                db.delete(itinerary)
            logger.info(f"🗑️ Deleted {len(flight_itineraries)} flight itineraries for event {event_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete flight itineraries (table may not exist): {str(e)}")
            db.rollback()
        
        # 5. Delete passport records manually (table may not exist)
        try:
            from app.models.passport_record import PassportRecord
            passport_records = db.query(PassportRecord).filter(
                PassportRecord.event_id == event_id
            ).all()
            for record in passport_records:
                db.delete(record)
            logger.info(f"🗑️ Deleted {len(passport_records)} passport records for event {event_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete passport records (table may not exist): {str(e)}")
            db.rollback()

        # 6. Delete chat rooms manually (table may not exist)
        try:
            from app.models.chat import ChatRoom
            chat_rooms = db.query(ChatRoom).filter(
                ChatRoom.event_id == event_id
            ).all()
            for room in chat_rooms:
                db.delete(room)
            logger.info(f"🗑️ Deleted {len(chat_rooms)} chat rooms for event {event_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete chat rooms (table may not exist): {str(e)}")
            db.rollback()

        # 7. Delete event participants manually (should exist)
        try:
            participants = db.query(EventParticipant).filter(
                EventParticipant.event_id == event_id
            ).all()
            for participant in participants:
                db.delete(participant)
            logger.info(f"🗑️ Deleted {len(participants)} event participants for event {event_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete event participants: {str(e)}")
            db.rollback()

        # 8. Delete event attachments manually (should exist)
        try:
            from app.models.event_attachment import EventAttachment
            attachments = db.query(EventAttachment).filter(
                EventAttachment.event_id == event_id
            ).all()
            for attachment in attachments:
                db.delete(attachment)
            logger.info(f"🗑️ Deleted {len(attachments)} event attachments for event {event_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete event attachments: {str(e)}")
            db.rollback()

        # 9. Delete vendor event accommodations using raw SQL
        try:
            result = db.execute(
                text("DELETE FROM vendor_event_accommodations WHERE event_id = :event_id"),
                {"event_id": event_id}
            )
            db.commit()
            logger.info(f"🗑️ Deleted {result.rowcount} vendor event accommodations for event {event_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete vendor event accommodations: {str(e)}")
            db.rollback()

        # 10. Finally delete the event itself using raw SQL to avoid cascade loading
        logger.info(f"✅ Deleting draft event: {event_id}")
        db.execute(text("DELETE FROM events WHERE id = :event_id"), {"event_id": event_id})
        db.commit()
        logger.info(f"🎉 Event deleted successfully: {event_id}")
        
    except Exception as e:
        logger.error(f"💥 Error during event deletion: {str(e)}")
        logger.exception("Full traceback:")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event: {str(e)}"
        )
    
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
    
    event.status = new_status
    db.commit()
    db.refresh(event)
    return {"message": f"Event status updated to {new_status}", "status": new_status}

# Role update endpoint moved to participant_role_update.py to avoid router conflicts

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
    from sqlalchemy import text
    
    # Get participation with registration data
    result = db.execute(
        text("""
            SELECT 
                ep.id, ep.status, ep.requires_eta, ep.passport_document, ep.ticket_document,
                pr.travelling_internationally
            FROM event_participants ep
            LEFT JOIN public_registrations pr ON ep.id = pr.participant_id
            WHERE ep.event_id = :event_id AND ep.email = :email
        """),
        {"event_id": event_id, "email": current_user.email}
    ).fetchone()
    
    logger.info(f"🎯 Get attendance status - Event: {event_id}, User: {current_user.email}")
    if not result:
        return {
            "status": None,
            "participant_id": None,
            "requires_eta": False,
            "has_passport": False,
            "has_ticket": False,
        }
    
    # Check if user is traveling internationally
    requires_eta = result.requires_eta or False
    
    # Check various possible values for travelling_internationally
    is_international = False
    if result.travelling_internationally:
        travel_value = str(result.travelling_internationally).lower().strip()
        is_international = travel_value in ['yes', 'true', '1', 'y']
    
    if is_international:
        requires_eta = True
        
        # Update the participant record if not already set
        if not result.requires_eta:
            db.execute(
                text("UPDATE event_participants SET requires_eta = true WHERE id = :participant_id"),
                {"participant_id": result.id}
            )
            db.commit()
    
    response_data = {
        "status": result.status,
        "participant_id": result.id,
        "requires_eta": requires_eta,
        "has_passport": bool(result.passport_document),
        "has_ticket": bool(result.ticket_document),
    }
    return response_data

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
    if registration_data.get('department'):
        current_user.project = registration_data['department']  # Map department to project field
    if registration_data.get('gender'):
        current_user.gender = registration_data['gender']
    
    # Create attendance request with additional data
    participant = EventParticipant(
        event_id=event_id,
        full_name=current_user.full_name,
        email=current_user.email,
        role='attendee',
        status='registered',  # Changed from 'requested' to 'registered'
        invited_by=current_user.email,
        country=registration_data.get('country'),
        position=registration_data.get('position'),
        project=registration_data.get('department'),  # Store department in project field
        gender=registration_data.get('gender'),
        eta=registration_data.get('eta') if registration_data.get('requires_eta') else None,
        requires_eta=registration_data.get('requires_eta', False)
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    
    return {
        "message": "Registration submitted successfully",
        "status": "registered",
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
        # If already confirmed, just return success
        if participation.status == 'confirmed':
            logger.info(f"✅ User already confirmed for event {event_id}")
            return {
                "message": "Attendance already confirmed",
                "status": "confirmed"
            }
        
        logger.error(f"❌ Invalid status for confirmation: '{participation.status}' (expected 'approved' or 'selected')")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only confirm attendance for approved or selected participants. Current status: {participation.status}"
        )
    
    # Update status to confirmed
    logger.info(f"✅ Updating status from '{participation.status}' to 'confirmed'")
    participation.status = 'confirmed'
    
    db.commit()
    
    # Create accommodation booking for confirmed participant with room sharing
    try:
        from app.models.guesthouse import AccommodationAllocation
        from app.models.event import Event
        from app.services.room_assignment_service import assign_room_with_sharing
        
        # Check if booking already exists
        existing_booking = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participation.id,
            AccommodationAllocation.status.in_(['booked', 'checked_in'])
        ).first()
        
        if not existing_booking:
            event = db.query(Event).filter(Event.id == event_id).first()
            if event:
                # Use intelligent room assignment with sharing
                allocation = assign_room_with_sharing(
                    db, participation.id, event_id, event.tenant_id
                )
                if allocation:
                    logger.info(f"🏨 Created accommodation booking for participant {participation.id}")
                else:
                    logger.warning(f"⚠️ Failed to create accommodation booking for participant {participation.id}")
        else:
            logger.info(f"🏨 Accommodation booking already exists for participant {participation.id}")
            
    except Exception as e:
        logger.warning(f"⚠️ Failed to create accommodation booking: {str(e)}")
    
    return {
        "message": "Attendance confirmed successfully",
        "status": "confirmed"
    }

@router.post("/{event_id}/admin-confirm-participant/{participant_id}")
def admin_confirm_participant(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Admin endpoint to confirm any participant"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Check admin permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin roles can confirm participants"
        )
    
    from app.models.event_participant import EventParticipant
    
    # Find the participation record
    participation = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    logger.info(f"🎯 Admin confirm - Event: {event_id}, Participant: {participant_id}")
    
    if not participation:
        logger.error(f"❌ No participation record found for participant {participant_id} in event {event_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation record not found"
        )
    
    logger.info(f"📊 Current participation status: '{participation.status}'")
    
    # Update status to confirmed
    logger.info(f"✅ Admin updating status from '{participation.status}' to 'confirmed'")
    participation.status = 'confirmed'
    
    db.commit()
    
    # Create accommodation booking for confirmed participant with room sharing
    try:
        from app.models.guesthouse import AccommodationAllocation
        from app.models.event import Event
        from app.services.room_assignment_service import assign_room_with_sharing
        
        # Check if booking already exists
        existing_booking = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participation.id,
            AccommodationAllocation.status.in_(['booked', 'checked_in'])
        ).first()
        
        if not existing_booking:
            event = db.query(Event).filter(Event.id == event_id).first()
            if event:
                # Use intelligent room assignment with sharing
                allocation = assign_room_with_sharing(
                    db, participation.id, event_id, event.tenant_id
                )
                if allocation:
                    logger.info(f"🏨 Created accommodation booking for participant {participation.id}")
                else:
                    logger.warning(f"⚠️ Failed to create accommodation booking for participant {participation.id}")
        else:
            logger.info(f"🏨 Accommodation booking already exists for participant {participation.id}")
            
    except Exception as e:
        logger.warning(f"⚠️ Failed to create accommodation booking: {str(e)}")
    
    return {
        "message": f"Participant {participation.full_name} confirmed successfully",
        "status": "confirmed",
        "participant_id": participation.id
    }

@router.post("/{event_id}/upload-document")
def upload_event_document(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    document_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Mock document upload for event participation."""
    import logging
    logger = logging.getLogger(__name__)
    
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
    
    if not document_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document type is required"
        )
    
    logger.info(f"📄 Mock document upload - User: {current_user.email}, Event: {event_id}, Type: {document_type}")
    
    # Mock successful upload by updating participation record
    if document_type == 'passport':
        participation.passport_document = f"mock_passport_{participation.id}.jpg"
        logger.info(f"✅ Passport document marked as uploaded for participant {participation.id}")
    elif document_type == 'ticket':
        participation.ticket_document = f"mock_ticket_{participation.id}.jpg"
        logger.info(f"✅ Ticket document marked as uploaded for participant {participation.id}")
    
    db.commit()
    
    return {
        "message": f"{document_type.title()} uploaded successfully",
        "file_path": f"mock_{document_type}_{participation.id}.jpg"
    }

@router.get("/test/participant-statuses")
def test_get_participant_statuses(
    *,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Test endpoint to see all participant statuses for current user"""
    from app.models.event_participant import EventParticipant
    from app.models.event import Event
    
    # Get all participations for current user
    participations = db.query(EventParticipant).join(
        Event, EventParticipant.event_id == Event.id
    ).filter(
        EventParticipant.email == current_user.email
    ).all()
    
    result = []
    for p in participations:
        result.append({
            "event_id": p.event_id,
            "event_title": p.event.title if p.event else "Unknown",
            "participant_id": p.id,
            "status": p.status,
            "decline_reason": getattr(p, 'decline_reason', None),
            "declined_at": getattr(p, 'declined_at', None)
        })
    
    return {
        "user_email": current_user.email,
        "total_participations": len(result),
        "participations": result
    }

@router.post("/{event_id}/decline-attendance")
def decline_event_attendance(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    request_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Decline attendance for an event with reason."""
    import logging
    from datetime import datetime
    logger = logging.getLogger(__name__)
    
    from app.models.event_participant import EventParticipant
    from app.models.guesthouse import AccommodationAllocation
    from sqlalchemy import text
    
    # Find the user's participation record
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    logger.info(f"🎯 Decline attendance - Event: {event_id}, User: {current_user.email}")
    
    if not participation:
        logger.error(f"❌ No participation record found for user {current_user.email} in event {event_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No participation record found"
        )
    
    if participation.status not in ["selected", "approved", "confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only selected, approved, or confirmed participants can decline attendance"
        )
    
    decline_reason = request_data.get("reason", "").strip()
    if not decline_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decline reason is required"
        )
    
    # Update status to declined with reason and timestamp
    participation.status = "declined"
    participation.decline_reason = decline_reason
    participation.declined_at = datetime.utcnow()
    
    # Cancel any existing accommodation bookings with room sharing logic
    try:
        from app.services.room_assignment_service import handle_room_cancellation
        handle_room_cancellation(db, participation.id)
    except Exception as e:
        logger.error(f"Error cancelling accommodations: {str(e)}")
    
    db.commit()
    
    # Note: Room booking system temporarily disabled during migration
    # Will be re-enabled with new room planning system
    logger.info(f"🏨 Room booking system temporarily disabled during migration")
    
    return {
        "message": "Attendance declined successfully",
        "status": "declined"
    }

@router.post("/test/simulate-selection/{event_id}")
def test_simulate_selection(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Test endpoint to simulate being selected for an event"""
    from app.models.event_participant import EventParticipant
    
    # Check if participation exists
    participation = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == current_user.email
    ).first()
    
    if participation:
        # Update existing to selected
        participation.status = "selected"
        db.commit()
        return {"message": f"Updated existing participation to selected", "participant_id": participation.id}
    else:
        # Create new participation as selected
        new_participation = EventParticipant(
            event_id=event_id,
            full_name=current_user.full_name,
            email=current_user.email,
            role='visitor',
            status='selected',
            invited_by='test_admin'
        )
        db.add(new_participation)
        db.commit()
        db.refresh(new_participation)
        return {"message": f"Created new participation as selected", "participant_id": new_participation.id}

@router.post("/{event_id}/refresh-room-booking")
def refresh_event_room_booking(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Manually refresh automatic room booking for an event"""
    import logging
    logger = logging.getLogger(__name__)
    
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
            detail="Only admin roles can refresh room booking"
        )
    
    # Get event
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    logger.info(f"🔄 Manual room booking refresh requested for event {event_id}: {event.title}")
    
    try:
        from app.services.automatic_room_booking_service import refresh_automatic_room_booking
        
        success = refresh_automatic_room_booking(db, event_id, event.tenant_id)
        
        if success:
            return {
                "message": "Room booking refreshed successfully",
                "event_id": event_id,
                "event_title": event.title
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to refresh room booking"
            )
            
    except Exception as e:
        logger.error(f"💥 Error refreshing room booking for event {event_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing room booking: {str(e)}"
        )