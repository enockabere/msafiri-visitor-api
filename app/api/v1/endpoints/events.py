# File: app/api/v1/endpoints/events.py
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole
from app.models.user_roles import UserRole as UserRoleModel
from app.models.vetting_committee import VettingCommittee, VettingStatus, VettingCommitteeMember

router = APIRouter()

def can_create_events(user_role: UserRole) -> bool:
    """Check if user role can create events (any role with ADMIN except SUPER_ADMIN)"""
    admin_roles = [UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    return user_role in admin_roles

def can_create_events_by_relationship_roles(user_roles: List[UserRoleModel]) -> bool:
    """Check if user has admin roles in the relationship table"""
    admin_role_types = ['MT_ADMIN', 'HR_ADMIN', 'EVENT_ADMIN']
    return any(role.role in admin_role_types for role in user_roles)

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
    """Get events that the current user is selected for (mobile endpoint).
    Only returns events where vetting has been approved."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🎯 === MY EVENTS REQUEST START ===")
        logger.info(f"👤 User: {current_user.email}")
        logger.info(f"📊 Skip: {skip}, Limit: {limit}")
        
        from app.models.event_participant import EventParticipant
        from app.models.event import Event
        from app.models.vetting_committee import VettingCommittee, VettingStatus
        from sqlalchemy import or_
        
        # Get events where user is selected/approved/confirmed (exclude declined)
        selected_statuses = ['selected', 'approved', 'confirmed', 'checked_in']
        
        # Query to get events through participation (excluding declined)
        # AND only include events where vetting has been approved
        events_query = db.query(Event).join(
            EventParticipant, Event.id == EventParticipant.event_id
        ).outerjoin(
            VettingCommittee, Event.id == VettingCommittee.event_id
        ).filter(
            EventParticipant.email.ilike(current_user.email),
            EventParticipant.status.in_(selected_statuses)
        ).filter(
            # Only show events where:
            # 1. No vetting committee exists (old events without vetting), OR
            # 2. Vetting committee exists and status is APPROVED
            or_(
                VettingCommittee.id.is_(None),
                VettingCommittee.status == VettingStatus.APPROVED
            )
        ).distinct()
        
        events = events_query.offset(skip).limit(limit).all()
        
        logger.info(f"📊 Found {len(events)} events for user {current_user.email} (only approved vetting)")
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
        
        # Add tenant_slug to response
        if hasattr(event, 'tenant') and event.tenant:
            event.tenant_slug = event.tenant.slug
        else:
            # Fallback: get tenant by ID
            tenant = crud.tenant.get(db, id=event.tenant_id)
            if tenant:
                event.tenant_slug = tenant.slug
        
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
        # Check user roles from relationship table
        user_roles = db.query(UserRoleModel).filter(
            UserRoleModel.user_id == current_user.id
        ).all()
        
        # Check if user has admin roles in the relationship table
        admin_role_types = ['MT_ADMIN', 'HR_ADMIN', 'EVENT_ADMIN']
        has_admin_role_in_relationship = any(role.role in admin_role_types for role in user_roles)
        
        # Check permissions - check both single role and relationship roles
        has_single_role_permission = can_create_events(current_user.role)
        
        # Allow if either permission method grants access
        if not has_single_role_permission and not has_admin_role_in_relationship:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin roles can create events"
            )
        
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
        

        
        # Clean up orphaned vetting roles before creating new event
        try:
            from app.services.vetting_role_cleanup_service import cleanup_orphaned_vetting_roles
            cleanup_orphaned_vetting_roles(db)
        except Exception as e:
            logger.warning(f"[WARNING] Failed to cleanup orphaned vetting roles: {str(e)}")

        # Auto-populate accommodation rate from vendor hotel if both vendor and accommodation_type are set
        event_data = event_in.model_dump() if hasattr(event_in, 'model_dump') else event_in.dict()
        if event_data.get('vendor_accommodation_id') and event_data.get('accommodation_type'):
            try:
                from app.models.guesthouse import VendorAccommodation
                vendor = db.query(VendorAccommodation).filter(
                    VendorAccommodation.id == event_data['vendor_accommodation_id']
                ).first()
                if vendor:
                    accommodation_type = event_data['accommodation_type']
                    rate = None
                    if accommodation_type == 'FullBoard':
                        rate = vendor.rate_full_board
                    elif accommodation_type == 'HalfBoard':
                        rate = vendor.rate_half_board
                    elif accommodation_type == 'BedAndBreakfast':
                        rate = vendor.rate_bed_breakfast
                    elif accommodation_type == 'BedOnly':
                        rate = vendor.rate_bed_only

                    if rate is not None:
                        event_data['accommodation_rate_per_day'] = rate
                        event_data['accommodation_rate_currency'] = vendor.rate_currency or 'KES'
                        # Update event_in with the rate data
                        event_in = schemas.EventCreate(**event_data)
                        logger.info(f"Set accommodation rate to {rate} {vendor.rate_currency or 'KES'} from vendor {vendor.vendor_name}")
            except Exception as e:
                logger.warning(f"[WARNING] Failed to auto-populate accommodation rate: {str(e)}")

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
        
        # Auto-create default form fields for the event
        try:
            from app.models.form_field import FormField
            import json
            
            # Check if form fields already exist
            existing_fields = db.query(FormField).filter(FormField.event_id == event.id).count()
            
            if existing_fields == 0:
                # Create default form fields
                default_fields = [
                    # Personal Information Section
                    {"field_name": "firstName", "field_label": "First Name", "field_type": "text", "is_required": True, "order_index": 101, "section": "personal", "is_protected": True},
                    {"field_name": "lastName", "field_label": "Last Name", "field_type": "text", "is_required": True, "order_index": 102, "section": "personal", "is_protected": True},
                    {"field_name": "oc", "field_label": "Operational Center (OC)", "field_type": "select", "field_options": '["OCA", "OCB", "OCBA", "OCG", "OCP", "WACA"]', "is_required": True, "order_index": 103, "section": "personal", "is_protected": True},
                    {"field_name": "contractStatus", "field_label": "Contract Status", "field_type": "select", "field_options": '["National Staff", "International Staff", "Consultant", "Volunteer"]', "is_required": True, "order_index": 104, "section": "personal", "is_protected": True},
                    {"field_name": "pronouns", "field_label": "Pronouns", "field_type": "select", "field_options": '["Mr", "Mrs", "Miss", "Ms", "Dr", "Prof", "Prefer not to say"]', "is_required": False, "order_index": 105, "section": "personal", "is_protected": True},
                    {"field_name": "genderIdentity", "field_label": "Gender Identity", "field_type": "select", "field_options": '["Male", "Female", "Non-binary", "Prefer not to say"]', "is_required": True, "order_index": 106, "section": "personal", "is_protected": True},
                    
                    # Contact Details Section
                    {"field_name": "personalEmail", "field_label": "Personal Email", "field_type": "email", "is_required": True, "order_index": 201, "section": "contact", "is_protected": True},
                    {"field_name": "phoneNumber", "field_label": "Phone Number", "field_type": "phone", "is_required": True, "order_index": 206, "section": "contact", "is_protected": True},
                    
                    # Final Details Section
                    {"field_name": "codeOfConductConfirm", "field_label": "I confirm that I have read and agree to abide by the MSF Code of Conduct", "field_type": "select", "field_options": '["I agree", "I do not agree"]', "is_required": True, "order_index": 401, "section": "final"},
                ]
                
                # Create form fields
                for field_data in default_fields:
                    form_field = FormField(
                        event_id=event.id,
                        **field_data
                    )
                    db.add(form_field)
                
        
        except Exception as e:
            logger.warning(f"[WARNING] Failed to create default form fields for event: {str(e)}")
            import traceback
            traceback.print_exc()
        
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

        except Exception as e:
            logger.warning(f"[WARNING] Failed to create chat room for event: {str(e)}")
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

                    
                    # Refresh automatic room booking for any existing confirmed participants
                    try:
                        from app.services.automatic_room_booking_service import refresh_automatic_room_booking
                        refresh_automatic_room_booking(db, event.id, tenant_obj.id)
                    except Exception as booking_error:
                        logger.warning(f"[WARNING] Failed to refresh room booking during event creation: {str(booking_error)}")
        except Exception as e:
            logger.warning(f"[WARNING] Failed to create vendor event accommodation setup: {str(e)}")
            import traceback
            traceback.print_exc()
        
        db.commit()
        

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
    event_ids: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    current_user: Optional[schemas.User] = Depends(deps.get_current_user)
) -> Any:
    """Get events (filtered by user role and vetting committee membership)."""
    import logging
    logger = logging.getLogger(__name__)
    
    # If specific event IDs are provided, filter by those
    if event_ids:
        try:
            event_id_list = [int(id.strip()) for id in event_ids.split(',') if id.strip()]
            events = crud.event.get_by_ids(db, event_ids=event_id_list)
            return events
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid event IDs format"
            )
    
    # Check if user only has GUEST and VETTING_COMMITTEE/VETTING_APPROVER roles
    all_roles = getattr(current_user, 'all_roles', [current_user.role.value if current_user.role else ''])
    admin_roles = ['SUPER_ADMIN', 'MT_ADMIN', 'EVENT_ADMIN', 'HR_ADMIN', 'super_admin', 'mt_admin', 'event_admin', 'hr_admin']
    vetting_roles = ['VETTING_COMMITTEE', 'VETTING_APPROVER', 'vetting_committee', 'vetting_approver']
    
    has_admin_role = any(role in admin_roles for role in all_roles)
    has_only_vetting_and_guest = (
        not has_admin_role and 
        any(role in vetting_roles for role in all_roles) and
        all(role in ['GUEST', 'VETTING_COMMITTEE', 'VETTING_APPROVER', 'guest', 'vetting_committee', 'vetting_approver'] for role in all_roles)
    )
    
    logger.info(f"🔍 GET EVENTS - User: {current_user.email}")
    logger.info(f"🔍 All roles: {all_roles}")
    logger.info(f"🔍 Has admin role: {has_admin_role}")
    logger.info(f"🔍 Has only vetting and guest: {has_only_vetting_and_guest}")
    
    # If user only has GUEST and VETTING_COMMITTEE roles, filter to only show vetting events
    if has_only_vetting_and_guest:
        logger.info(f"🔍 Filtering events for vetting committee member: {current_user.email}")
        
        # Get committees where user is member or approver
        from app.models.event import Event
        from sqlalchemy import or_
        
        vetting_event_ids = set()
        
        # Check if user is a committee member
        member_committees = db.query(VettingCommittee).join(
            VettingCommitteeMember, VettingCommittee.id == VettingCommitteeMember.committee_id
        ).filter(
            VettingCommitteeMember.email.ilike(current_user.email)
        ).all()
        
        logger.info(f"🔍 Found {len(member_committees)} committees where user is member")
        for committee in member_committees:
            logger.info(f"🔍 Member committee: ID={committee.id}, Event ID={committee.event_id}")
            vetting_event_ids.add(committee.event_id)
        
        # Check if user is an approver (legacy system)
        approver_committees = db.query(VettingCommittee).filter(
            or_(
                VettingCommittee.approver_email.ilike(current_user.email),
                VettingCommittee.approver_id == current_user.id
            )
        ).all()
        
        logger.info(f"🔍 Found {len(approver_committees)} committees where user is approver (legacy)")
        for committee in approver_committees:
            logger.info(f"🔍 Approver committee: ID={committee.id}, Event ID={committee.event_id}")
            vetting_event_ids.add(committee.event_id)
        
        # Check new approvers table
        from app.models.vetting_committee import VettingCommitteeApprover
        new_approver_records = db.query(VettingCommitteeApprover).filter(
            VettingCommitteeApprover.email.ilike(current_user.email)
        ).all()
        
        logger.info(f"🔍 Found {len(new_approver_records)} approver records in new table")
        for approver_record in new_approver_records:
            committee = db.query(VettingCommittee).filter(
                VettingCommittee.id == approver_record.committee_id
            ).first()
            if committee:
                logger.info(f"🔍 New approver committee: ID={committee.id}, Event ID={committee.event_id}")
                vetting_event_ids.add(committee.event_id)
        
        logger.info(f"🔍 Total vetting event IDs: {vetting_event_ids}")
        
        if not vetting_event_ids:
            logger.info(f"📊 No vetting events found for user {current_user.email}")
            return []
        
        # Get events by IDs
        events = db.query(Event).filter(Event.id.in_(vetting_event_ids)).offset(skip).limit(limit).all()
        logger.info(f"📊 Found {len(events)} vetting events for user {current_user.email}")
        return events
    
    # For admin users or users with other roles, show all events
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
    
    # Debug: Print registration data for maebaenock95@gmail.com when event page is accessed
    try:
        participant = db.execute(
            text("SELECT * FROM event_participants WHERE email = 'maebaenock95@gmail.com' AND event_id = :event_id"),
            {"event_id": event_id}
        ).fetchone()
        
        if participant:
            print(f"\n📋 AUTO DEBUG: Found participant maebaenock95@gmail.com in event {event_id}")
            print(f"  Participant ID: {participant.id}")
            print(f"  Full Name: {participant.full_name}")
            print(f"  Status: {participant.status}")
            
            # Get public registration details
            pub_reg = db.execute(
                text("SELECT * FROM public_registrations WHERE participant_id = :pid"),
                {"pid": participant.id}
            ).fetchone()
            
            if pub_reg:
                print(f"\n📝 AUTO DEBUG: Public registration data:")
                print(f"  Personal Email: {pub_reg.personal_email}")
                print(f"  MSF Email: {pub_reg.msf_email}")
                print(f"  Phone: {pub_reg.phone_number}")
                print(f"  OC: {pub_reg.oc}")
                print(f"  Contract Status: {pub_reg.contract_status}")
                print(f"  Gender Identity: {pub_reg.gender_identity}")
                print(f"  Sex: {pub_reg.sex}")
                print(f"  Line Manager Email: {pub_reg.line_manager_email}")
            else:
                print(f"\n❌ AUTO DEBUG: No public registration found for participant {participant.id}")
    except Exception as e:
        print(f"\n⚠️ AUTO DEBUG ERROR: {e}")
    
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
    
    # Check if user can access this event (same tenant, admin, or vetting member)
    logger.info(f"🔍 Using user-based access control")

    # Get all user roles (primary + secondary)
    all_roles = getattr(current_user, 'all_roles', [current_user.role.value if current_user.role else ''])
    admin_roles = ['SUPER_ADMIN', 'MT_ADMIN', 'EVENT_ADMIN', 'HR_ADMIN', 'super_admin', 'mt_admin', 'event_admin', 'hr_admin']

    has_admin_role = current_user.role == UserRole.SUPER_ADMIN or \
                     any(role in admin_roles for role in all_roles)

    # Admins can access any event
    if has_admin_role:
        logger.info(f"✅ Admin access granted via all_roles: {all_roles}")
    else:
        # Check if user is a vetting committee member or approver for this event
        from app.models.vetting_committee import VettingCommittee, VettingCommitteeMember
        from app.models.event_participant import EventParticipant
        is_vetting_member = db.query(VettingCommitteeMember).join(VettingCommittee).filter(
            VettingCommittee.event_id == event_id,
            VettingCommitteeMember.email == current_user.email
        ).first() is not None

        is_vetting_approver = db.query(VettingCommittee).filter(
            VettingCommittee.event_id == event_id,
            VettingCommittee.approver_email == current_user.email
        ).first() is not None

        # Check if user is a participant in this event
        is_participant = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.email == current_user.email
        ).first() is not None

        if is_vetting_member or is_vetting_approver or is_participant:
            logger.info(f"✅ Access granted - vetting_member: {is_vetting_member}, approver: {is_vetting_approver}, participant: {is_participant}")
        else:
            # Fall back to tenant check
            user_tenant_obj = None
            if current_user.tenant_id:
                user_tenant_obj = crud.tenant.get_by_slug(db, slug=current_user.tenant_id)

            user_tenant_id = user_tenant_obj.id if user_tenant_obj else None

            logger.info(f"🔍 Tenant check - Event tenant: {event.tenant_id}, User tenant: {user_tenant_id}")

            if event.tenant_id != user_tenant_id:
                logger.error(f"❌ Access denied - not admin, not vetting member, tenant mismatch")
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
    event_update: dict,
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant: Optional[str] = Query(None)
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
    
    # Validate room capacity if double_rooms is set to 0
    if 'double_rooms' in event_update and int(event_update['double_rooms']) == 0:
        # Count confirmed participants staying at venue
        from app.models.event_participant import EventParticipant
        confirmed_participants = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.status == "confirmed",
            EventParticipant.accommodation_preference == "staying_at_venue"
        ).count()
        
        single_rooms = int(event_update.get('single_rooms', event.single_rooms or 0))
        expected_participants = int(event_update.get('expected_participants', event.expected_participants or 0))
        
        # Use the higher of confirmed participants or expected participants
        participants_to_accommodate = max(confirmed_participants, expected_participants)
        
        if single_rooms < participants_to_accommodate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot set double rooms to 0: Single rooms ({single_rooms}) must be at least equal to expected participants ({participants_to_accommodate})"
            )
    
    # General room capacity validation
    single_rooms = int(event_update.get('single_rooms', event.single_rooms or 0))
    double_rooms = int(event_update.get('double_rooms', event.double_rooms or 0))
    expected_participants = int(event_update.get('expected_participants', event.expected_participants or 0))
    
    total_capacity = single_rooms + (double_rooms * 2)
    if total_capacity < expected_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room capacity ({total_capacity}) cannot be less than expected participants ({expected_participants})"
        )
    
    # Convert registration_deadline string to datetime if provided
    if 'registration_deadline' in event_update and event_update['registration_deadline']:
        from datetime import datetime
        try:
            dt_str = event_update['registration_deadline']
            dt_obj = datetime.fromisoformat(dt_str)
            event_update['registration_deadline'] = dt_obj
        except Exception:
            # Keep as string and let Pydantic handle it
            pass
    
    # Debug: Log what we're receiving
    logger.info(f"📝 Event update data received: {event_update}")
    logger.info(f"📝 accommodation_type in update: {event_update.get('accommodation_type', 'NOT PRESENT')}")

    # Convert dict to EventUpdate schema
    event_update_schema = schemas.EventUpdate(**event_update)
    logger.info(f"📝 Schema accommodation_type: {event_update_schema.accommodation_type}")

    # Check if room configuration changed
    room_config_changed = (
        'single_rooms' in event_update or 
        'double_rooms' in event_update or 
        'vendor_accommodation_id' in event_update
    )
    
    # Update the event
    updated_event = crud.event.update(db, db_obj=event, obj_in=event_update_schema)
    logger.info(f"📝 Updated event accommodation_type: {updated_event.accommodation_type}")

    # If room configuration changed, trigger automatic room reallocation
    if room_config_changed:
        try:
            from app.services.automatic_room_booking_service import refresh_automatic_room_booking
            logger.info(f"🏨 Room configuration changed for event {event_id}, triggering reallocation...")
            refresh_automatic_room_booking(db, event_id, updated_event.tenant_id)
            logger.info(f"✅ Room reallocation completed for event {event_id}")
        except Exception as e:
            logger.warning(f"[WARNING] Failed to refresh room booking after event update: {str(e)}")
    
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
        UserRoleModel.user_id == current_user.id
    ).all()
    
    logger.info(f"🔐 User roles from relationship: {[role.role for role in user_roles]}")
    
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
    
    # ULTIMATE SOLUTION: Use raw connection to bypass SQLAlchemy transaction management
    try:
        # Get raw connection
        connection = db.get_bind().raw_connection()
        cursor = connection.cursor()
        
        logger.info(f"✅ Using raw SQL connection for event deletion: {event_id}")
        
        # Execute deletion commands directly
        deletion_commands = [
            f"DELETE FROM accommodation_allocations WHERE participant_id IN (SELECT id FROM event_participants WHERE event_id = {event_id});",
            f"DELETE FROM accommodation_allocations WHERE event_id = {event_id};",
            f"DELETE FROM public_registrations WHERE participant_id IN (SELECT id FROM event_participants WHERE event_id = {event_id});",
            f"DELETE FROM line_manager_recommendations WHERE event_id = {event_id};",
            f"DELETE FROM transport_requests WHERE flight_itinerary_id IN (SELECT id FROM flight_itineraries WHERE event_id = {event_id});",
            f"DELETE FROM transport_requests WHERE event_id = {event_id};",
            f"DELETE FROM passport_records WHERE event_id = {event_id};",
            f"DELETE FROM flight_itineraries WHERE event_id = {event_id};",
            f"DELETE FROM event_participants WHERE event_id = {event_id};",
            f"DELETE FROM vendor_event_accommodations WHERE event_id = {event_id};",
            f"DELETE FROM event_agenda WHERE event_id = {event_id};",
            f"DELETE FROM chat_rooms WHERE event_id = {event_id};",
            f"DELETE FROM event_attachments WHERE event_id = {event_id};",
            f"DELETE FROM events WHERE id = {event_id};"
        ]
        
        for i, command in enumerate(deletion_commands):
            try:
                cursor.execute(command)
                logger.info(f"✅ Executed command {i+1}: {command[:50]}...")
            except Exception as e:
                logger.warning(f"⚠️ Command {i+1} failed: {str(e)[:100]}")
                # Continue with next command
        
        # Commit all changes
        connection.commit()
        cursor.close()
        connection.close()
        
        # Clean up vetting roles for users who were part of this event's vetting committee
        try:
            from app.services.vetting_role_cleanup_service import cleanup_orphaned_vetting_roles_for_deleted_event
            cleanup_orphaned_vetting_roles_for_deleted_event(db, event_id)
        except Exception as e:
            logger.warning(f"[WARNING] Failed to cleanup vetting roles for deleted event: {str(e)}")
        
        logger.info(f"🎉 Event deleted successfully using raw SQL: {event_id}")
        
    except Exception as e:
        logger.error(f"💥 Raw SQL deletion failed: {str(e)}")
        logger.exception("Full traceback:")
        try:
            if 'connection' in locals():
                connection.rollback()
                cursor.close()
                connection.close()
        except Exception:
            pass
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
        UserRoleModel.user_id == current_user.id
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

@router.get("/{event_id}/my-registration-data")
def get_my_registration_data(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get current user's registration data for an event."""
    import logging
    logger = logging.getLogger(__name__)
    
    from app.models.event_participant import EventParticipant
    from sqlalchemy import text
    
    # Get participation with registration data
    result = db.execute(
        text("""
            SELECT 
                ep.id, ep.status, ep.country, ep.travelling_internationally,
                pr.nationality, pr.travelling_from_country
            FROM event_participants ep
            LEFT JOIN public_registrations pr ON ep.id = pr.participant_id
            WHERE ep.event_id = :event_id AND ep.email = :email
        """),
        {"event_id": event_id, "email": current_user.email}
    ).fetchone()
    
    logger.info(f"🎯 Get registration data - Event: {event_id}, User: {current_user.email}")
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registration record found"
        )
    
    # Get nationality from either the participant record or public registration
    nationality = result.country or result.nationality
    travelling_internationally = result.travelling_internationally
    
    return {
        "participant_id": result.id,
        "status": result.status,
        "nationality": nationality,
        "travelling_internationally": travelling_internationally,
        "travelling_from_country": result.travelling_from_country
    }
@router.get("/{event_id}/my-attendance-status")
def get_my_attendance_status(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get current user's attendance status for a specific event.
    Only returns status if vetting has been approved."""
    import logging
    logger = logging.getLogger(__name__)
    
    from app.models.event_participant import EventParticipant
    from app.models.vetting_committee import VettingCommittee, VettingStatus
    from sqlalchemy import text
    
    # First check if vetting committee exists and is approved
    vetting_committee = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).first()
    
    if vetting_committee and vetting_committee.status != VettingStatus.APPROVED:
        logger.info(f"🔒 Vetting not approved for event {event_id}, status: {vetting_committee.status.value}")
        return {
            "status": None,
            "participant_id": None,
            "requires_eta": False,
            "has_passport": False,
            "has_ticket": False,
            "vetting_pending": True,
            "vetting_status": vetting_committee.status.value
        }
    
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
            "vetting_pending": False
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
        "vetting_pending": False
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
    confirmation_data: dict = None,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Confirm attendance for an approved event with additional questions."""
    import logging
    logger = logging.getLogger(__name__)
    
    from app.models.event_participant import EventParticipant
    from app.models.notification import Notification, NotificationPriority, NotificationType
    
    print(f"\n🔥 API: TRAVEL DETAILS SUBMISSION RECEIVED")
    print(f"🔥 API: Event ID = {event_id}")
    print(f"🔥 API: User = {current_user.email}")
    print(f"🔥 API: Confirmation Data = {confirmation_data}")
    
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
    
    # Update additional confirmation data if provided
    if confirmation_data:
        print(f"\n🔥 API: UPDATING TRAVEL DETAILS:")
        
        # Update travelling internationally status
        if 'travelling_internationally' in confirmation_data:
            participation.travelling_internationally = confirmation_data['travelling_internationally']
            print(f"🔥 API: Updated travelling_internationally: {confirmation_data['travelling_internationally']}")
            logger.info(f"📝 Updated travelling_internationally: {confirmation_data['travelling_internationally']}")
        
        # Update nationality if provided (this updates the existing nationality field)
        if 'nationality' in confirmation_data:
            participation.country = confirmation_data['nationality']
            print(f"🔥 API: Updated nationality: {confirmation_data['nationality']}")
            logger.info(f"📝 Updated nationality: {confirmation_data['nationality']}")
        
        # Update accommodation preference
        if 'accommodation_preference' in confirmation_data:
            participation.accommodation_preference = confirmation_data['accommodation_preference']
            print(f"🔥 API: Updated accommodation_preference: {confirmation_data['accommodation_preference']}")
            logger.info(f"📝 Updated accommodation_preference: {confirmation_data['accommodation_preference']}")
        
        # Update dietary requirements
        if 'has_dietary_requirements' in confirmation_data:
            participation.has_dietary_requirements = confirmation_data['has_dietary_requirements']
            if confirmation_data['has_dietary_requirements'] and 'dietary_requirements' in confirmation_data:
                participation.dietary_requirements = confirmation_data['dietary_requirements']
            else:
                participation.dietary_requirements = None
            print(f"🔥 API: Updated dietary requirements: {confirmation_data['has_dietary_requirements']}")
            logger.info(f"📝 Updated dietary requirements: {confirmation_data['has_dietary_requirements']}")
        
        # Update accommodation needs
        if 'has_accommodation_needs' in confirmation_data:
            participation.has_accommodation_needs = confirmation_data['has_accommodation_needs']
            if confirmation_data['has_accommodation_needs'] and 'accommodation_needs' in confirmation_data:
                participation.accommodation_needs = confirmation_data['accommodation_needs']
            else:
                participation.accommodation_needs = None
            print(f"🔥 API: Updated accommodation needs: {confirmation_data['has_accommodation_needs']}")
            logger.info(f"📝 Updated accommodation needs: {confirmation_data['has_accommodation_needs']}")
        
        # Update certificate and badge names
        if 'certificate_name' in confirmation_data:
            participation.certificate_name = confirmation_data['certificate_name']
            print(f"🔥 API: Updated certificate_name: {confirmation_data['certificate_name']}")
            logger.info(f"📝 Updated certificate_name: {confirmation_data['certificate_name']}")
        
        if 'badge_name' in confirmation_data:
            participation.badge_name = confirmation_data['badge_name']
            print(f"🔥 API: Updated badge_name: {confirmation_data['badge_name']}")
            logger.info(f"📝 Updated badge_name: {confirmation_data['badge_name']}")
    
    db.commit()
    print(f"🔥 API: DATABASE COMMIT SUCCESSFUL - Travel details saved!")
    
    # Create accommodation booking only if staying at venue
    accommodation_preference = confirmation_data.get('accommodation_preference') if confirmation_data else None
    should_book_accommodation = accommodation_preference != 'travelling_daily'
    
    if should_book_accommodation:
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
                        logger.info(f"[HOTEL] Created accommodation booking for participant {participation.id}")
                    else:
                        logger.warning(f"[WARNING] Failed to create accommodation booking for participant {participation.id}")
            else:
                logger.info(f"[HOTEL] Accommodation booking already exists for participant {participation.id}")
                
        except Exception as e:
            logger.warning(f"[WARNING] Failed to create accommodation booking: {str(e)}")
    else:
        logger.info(f"[HOTEL] Skipping accommodation booking - participant travelling daily")
    
    print(f"🔥 API: TRAVEL DETAILS SUBMISSION COMPLETE!\n")
    
    return {
        "message": "Attendance confirmed successfully",
        "status": "confirmed",
        "requires_travel_checklist": confirmation_data.get('travelling_internationally', '').lower() == 'yes' if confirmation_data else False
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
                    logger.info(f"[HOTEL] Created accommodation booking for participant {participation.id}")
                else:
                    logger.warning(f"[WARNING] Failed to create accommodation booking for participant {participation.id}")
        else:
            logger.info(f"[HOTEL] Accommodation booking already exists for participant {participation.id}")
            
    except Exception as e:
        logger.warning(f"[WARNING] Failed to create accommodation booking: {str(e)}")
    
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
    logger.info(f"[HOTEL] Room booking system temporarily disabled during migration")
    
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

@router.post("/{event_id}/participants/{participant_id}/generate-poa")
async def generate_poa_for_participant(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Generate POA document for a specific participant"""
    import logging
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    # Check permissions
    user_roles = db.query(UserRoleModel).filter(
        UserRoleModel.user_id == current_user.id
    ).all()
    
    has_single_role_permission = can_create_events(current_user.role)
    has_relationship_role_permission = can_create_events_by_relationship_roles(user_roles)
    
    if not has_single_role_permission and not has_relationship_role_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin roles can generate POA documents"
        )
    
    # Get event
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Get participant
    from app.models.event_participant import EventParticipant
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )
    
    # Only generate POA for confirmed participants
    if participant.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="POA can only be generated for confirmed participants"
        )
    
    # Get tenant
    tenant = crud.tenant.get(db, id=event.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Get vendor accommodation if specified
    vendor = None
    if event.vendor_accommodation_id:
        from app.models.guesthouse import VendorAccommodation
        vendor = db.query(VendorAccommodation).filter(
            VendorAccommodation.id == event.vendor_accommodation_id
        ).first()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event must have a vendor accommodation assigned to generate POA documents"
        )
    
    # Get POA template for the vendor
    from app.crud.poa_template import poa_template
    template = poa_template.get_by_vendor(db, vendor_accommodation_id=vendor.id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No POA template found for vendor '{vendor.vendor_name}'. Please create a template first."
        )
    
    logger.info(f"🎯 Generating POA for participant {participant_id} in event {event_id}")
    
    try:
        # Generate actual POA document using the same service as vendor setup
        from app.services.proof_of_accommodation import generate_proof_of_accommodation
        
        # Format dates
        check_in_date = event.start_date.strftime('%B %d, %Y') if event.start_date else 'TBD'
        check_out_date = event.end_date.strftime('%B %d, %Y') if event.end_date else 'TBD'
        event_dates = f"{check_in_date} - {check_out_date}"
        
        # Get allocation ID from accommodation_allocations table
        from app.models.guesthouse import AccommodationAllocation
        allocation = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participant.id,
            AccommodationAllocation.event_id == event_id
        ).first()
        
        allocation_id = allocation.id if allocation else 0
        room_type = allocation.room_type if allocation and allocation.room_type else "Standard"
        
        poa_url, poa_slug = await generate_proof_of_accommodation(
            participant_id=participant.id,
            event_id=event_id,
            allocation_id=allocation_id,
            template_html=template.template_content,
            hotel_name=vendor.vendor_name,
            hotel_address=vendor.location,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            room_type=room_type,
            event_name=event.title,
            event_dates=event_dates,
            participant_name=participant.full_name,
            tenant_name=tenant.name,
            logo_url=template.logo_url,
            signature_url=template.signature_url,
            enable_qr_code=template.enable_qr_code
        )
        
        # Update participant with actual POA URL and slug
        participant.proof_of_accommodation_url = poa_url
        participant.poa_slug = poa_slug
        participant.proof_generated_at = datetime.now()
        
        # Commit changes
        db.commit()
        
        logger.info(f"✅ Generated POA for participant {participant.id}: {participant.full_name}")
        
        return {
            "message": f"POA generated successfully for {participant.full_name}",
            "poa_url": poa_url
        }
        
    except Exception as e:
        error_msg = f"Failed to generate POA for participant {participant.id} ({participant.full_name}): {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@router.post("/{event_id}/generate-poa")
async def generate_poa_for_event(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Generate POA documents for all participants in an event"""
    import logging
    from datetime import datetime
    import qrcode
    from io import BytesIO
    import base64
    import os
    
    logger = logging.getLogger(__name__)
    
    # Check permissions
    user_roles = db.query(UserRoleModel).filter(
        UserRoleModel.user_id == current_user.id
    ).all()
    
    has_single_role_permission = can_create_events(current_user.role)
    has_relationship_role_permission = can_create_events_by_relationship_roles(user_roles)
    
    if not has_single_role_permission and not has_relationship_role_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin roles can generate POA documents"
        )
    
    # Get event
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Get tenant
    tenant = crud.tenant.get(db, id=event.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Get vendor accommodation if specified
    vendor = None
    if event.vendor_accommodation_id:
        from app.models.guesthouse import VendorAccommodation
        vendor = db.query(VendorAccommodation).filter(
            VendorAccommodation.id == event.vendor_accommodation_id
        ).first()
    
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event must have a vendor accommodation assigned to generate POA documents"
        )
    
    # Get POA template for the vendor
    from app.crud.poa_template import poa_template
    template = poa_template.get_by_vendor(db, vendor_accommodation_id=vendor.id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No POA template found for vendor '{vendor.vendor_name}'. Please create a template first."
        )
    
    # Get confirmed participants only
    from app.models.event_participant import EventParticipant
    participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.status == "confirmed"
    ).all()
    
    if not participants:
        raise HTTPException(
            status_code=404,
            detail="No confirmed participants found for POA generation"
        )
    
    logger.info(f"🎯 Generating POA for {len(participants)} confirmed participants in event {event_id}")
    
    successful = 0
    failed = 0
    errors = []
    
    for participant in participants:
        try:
            # Generate actual POA document using the same service as vendor setup
            from app.services.proof_of_accommodation import generate_proof_of_accommodation
            
            # Format dates
            check_in_date = event.start_date.strftime('%B %d, %Y') if event.start_date else 'TBD'
            check_out_date = event.end_date.strftime('%B %d, %Y') if event.end_date else 'TBD'
            event_dates = f"{check_in_date} - {check_out_date}"
            
            # Get allocation ID from accommodation_allocations table
            from app.models.guesthouse import AccommodationAllocation
            allocation = db.query(AccommodationAllocation).filter(
                AccommodationAllocation.participant_id == participant.id,
                AccommodationAllocation.event_id == event_id
            ).first()
            
            allocation_id = allocation.id if allocation else 0
            room_type = allocation.room_type if allocation and allocation.room_type else "Standard"
            
            poa_url, poa_slug = await generate_proof_of_accommodation(
                participant_id=participant.id,
                event_id=event_id,
                allocation_id=allocation_id,
                template_html=template.template_content,
                hotel_name=vendor.vendor_name,
                hotel_address=vendor.location,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                room_type=room_type,
                event_name=event.title,
                event_dates=event_dates,
                participant_name=participant.full_name,
                tenant_name=tenant.name,
                logo_url=template.logo_url,
                signature_url=template.signature_url,
                enable_qr_code=template.enable_qr_code
            )
            
            # Update participant with actual POA URL and slug
            participant.proof_of_accommodation_url = poa_url
            participant.poa_slug = poa_slug
            participant.proof_generated_at = datetime.now()
            
            successful += 1
            logger.info(f"✅ Generated POA for participant {participant.id}: {participant.full_name}")
            
        except Exception as e:
            failed += 1
            error_msg = f"Failed to generate POA for participant {participant.id} ({participant.full_name}): {str(e)}"
            errors.append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    # Commit all changes
    db.commit()
    
    logger.info(f"🎉 POA generation completed - Success: {successful}, Failed: {failed}")
    
    return {
        "message": "POA generation completed",
        "total_participants": len(participants),
        "successful": successful,
        "failed": failed,
        "errors": errors if errors else None
    }


@router.get("/{event_id}/loi-template")
def get_event_loi_template(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Get the LOI template assigned to an event"""
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    return {
        "invitation_template_id": event.invitation_template_id
    }

@router.put("/{event_id}/loi-template")
def update_event_loi_template(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    template_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Assign an LOI template to an event"""
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Check permissions
    user_roles = db.query(UserRoleModel).filter(
        UserRoleModel.user_id == current_user.id,
        UserRoleModel.user_id == current_user.id
    ).all()
    
    has_single_role_permission = can_create_events(current_user.role)
    has_relationship_role_permission = can_create_events_by_relationship_roles(user_roles)
    
    if not has_single_role_permission and not has_relationship_role_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin roles can update event LOI template"
        )
    
    # Update the event's invitation template
    event.invitation_template_id = template_data.get("invitation_template_id")
    db.commit()
    db.refresh(event)
    
    return {
        "message": "LOI template updated successfully",
        "invitation_template_id": event.invitation_template_id
    }
