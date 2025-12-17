from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.api import deps
from app.db.database import get_db
from app.models.event_participant import EventParticipant
from app.schemas.event_participant import EventParticipantCreate, EventParticipantUpdate

router = APIRouter()

@router.post("/", response_model=schemas.event_participant.EventParticipant, operation_id="create_event_participant_unique")
def create_participant(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_in: EventParticipantCreate
) -> Any:
    """Create new event participant"""
    
    # Verify event exists
    event = crud.event.get(db, id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if participant already exists
    existing = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.email == participant_in.email
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Participant already exists for this event")
    
    # Create participant
    participant = EventParticipant(
        event_id=event_id,
        full_name=participant_in.full_name,
        email=participant_in.email,
        role=getattr(participant_in, 'role', 'attendee'),
        status='invited',
        invited_by='admin'
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    
    return participant

@router.get("/", operation_id="get_event_participants_unique")
def get_participants(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    role: str = None,
    skip: int = 0,
    limit: int = 50
) -> Any:
    """Get event participants with optional role filtering and pagination"""

    query = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id
    )
    
    if role:
        # Check both role and participant_role columns
        from sqlalchemy import or_, text
        try:
            # Try to filter by both role and participant_role columns
            query = query.filter(
                or_(
                    EventParticipant.role == role,
                    text(f"participant_role = '{role}'")
                )
            )
        except Exception:
            # Fallback to just role column if participant_role doesn't exist
            query = query.filter(EventParticipant.role == role)
    
    participants = query.offset(skip).limit(limit).all()
    
    # Enrich participants with registration data
    from sqlalchemy import text
    enriched_participants = []
    
    for participant in participants:
        # Get registration data from public_registrations table
        registration_result = db.execute(
            text("""
                SELECT gender_identity, accommodation_needs, travelling_from_country 
                FROM public_registrations 
                WHERE event_id = :event_id AND (personal_email = :email OR msf_email = :email)
                LIMIT 1
            """),
            {"event_id": event_id, "email": participant.email}
        ).first()
        
        gender = None
        accommodation_needs = None
        
        if registration_result:
            gender_identity = registration_result[0]
            accommodation_needs = registration_result[1]
            
            # Convert gender_identity to standard format
            if gender_identity:
                if gender_identity.lower() in ['man', 'male']:
                    gender = 'male'
                elif gender_identity.lower() in ['woman', 'female']:
                    gender = 'female'
                else:
                    gender = 'other'
        
        # Create participant dict with additional fields
        participant_dict = {
            "id": participant.id,
            "event_id": participant.event_id,
            "full_name": participant.full_name,
            "email": participant.email,
            "role": participant.role,
            "status": participant.status,
            "gender": gender,
            "accommodation_needs": accommodation_needs
        }
        
        # Add participant_role if it exists
        try:
            result = db.execute(
                text("SELECT participant_role FROM event_participants WHERE id = :id"),
                {"id": participant.id}
            ).first()
            if result and result[0]:
                participant_dict["participant_role"] = result[0]
        except:
            pass
        
        enriched_participants.append(participant_dict)
    
    return enriched_participants

@router.put("/{participant_id}/role", operation_id="update_participant_role_unique")
async def update_participant_role(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_id: int,
    role_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update participant role with auto-booking"""
    
    # Check permissions - allow vetting approvers during approval phase
    from app.core.permissions import can_edit_vetting_participants
    from app.models.user import UserRole
    
    has_admin_permission = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    has_vetting_permission = can_edit_vetting_participants(current_user, db, event_id)
    
    if not (has_admin_permission or has_vetting_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update participant role"
        )
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    

    
    # Validate role
    valid_roles = ['visitor', 'facilitator', 'organizer']
    new_role = role_data.get('role', '').lower()
    if new_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    old_role = getattr(participant, 'participant_role', 'visitor')

    
    # Update both role fields for consistency
    try:
        from sqlalchemy import text
        db.execute(
            text("UPDATE event_participants SET role = :role, participant_role = :role WHERE id = :id"),
            {"role": new_role, "id": participant_id}
        )
        db.commit()

        
        # Trigger auto-booking if participant is confirmed
        if participant.status == 'confirmed':
            await trigger_auto_booking_after_role_change(event_id, participant_id, db)
        
        # Send role change notification email
        if old_role != new_role:
            await send_role_change_notification(participant, old_role, new_role, db)
        

        return {"message": "Role updated successfully", "new_role": new_role}
        
    except Exception as e:
        db.rollback()

        raise HTTPException(status_code=500, detail="Failed to update role")

async def trigger_auto_booking_after_role_change(event_id, participant_id, db):
    """Trigger auto-booking after role change"""
    try:

        
        # Delete ALL existing allocations for this event to prevent duplicates
        from app.models.guesthouse import AccommodationAllocation
        from sqlalchemy import text
        
        # Get all participants for this event
        all_participants_query = text("""
            SELECT id FROM event_participants 
            WHERE event_id = :event_id AND status = 'confirmed'
        """)
        all_participant_ids = [row[0] for row in db.execute(all_participants_query, {"event_id": event_id}).fetchall()]
        
        # Delete all existing allocations for all participants in this event
        existing_allocations = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id.in_(all_participant_ids),
            AccommodationAllocation.status.in_(["booked", "checked_in"])
        ).all()
        

        
        for allocation in existing_allocations:

            
            # Restore room counts
            if allocation.vendor_accommodation_id:
                if allocation.room_type == 'single':

                    db.execute(text("""
                        UPDATE vendor_accommodations 
                        SET single_rooms = single_rooms + 1 
                        WHERE id = :vendor_id
                    """), {"vendor_id": allocation.vendor_accommodation_id})
                elif allocation.room_type == 'double':
                    db.execute(text("""
                        UPDATE vendor_accommodations 
                        SET double_rooms = double_rooms + 1 
                        WHERE id = :vendor_id
                    """), {"vendor_id": allocation.vendor_accommodation_id})
            
            db.delete(allocation)
        
        db.commit()

        
        # Trigger mass auto-booking for all participants
        from app.api.v1.endpoints.auto_booking import auto_book_all_participants
        
        # Create a mock user for auto-booking
        class MockUser:
            def __init__(self):
                self.tenant_id = "msf-oca"
                self.id = 1
        
        mock_user = MockUser()
        tenant_context = "msf-oca"

        
        # Call the mass auto-booking function directly
        booking_result = auto_book_all_participants(
            event_id=event_id,
            db=db,
            current_user=mock_user,
            tenant_context=tenant_context
        )
        

        
    except Exception as e:
        import traceback

async def handle_participant_decline_reallocation(event_id, participant_id, db):
    """Handle room reallocation when a participant declines"""
    try:
        from app.models.guesthouse import AccommodationAllocation
        from sqlalchemy import text
        
        # Find existing allocations for this participant
        existing_allocations = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participant_id,
            AccommodationAllocation.status.in_(["booked", "checked_in"])
        ).all()
        
        for allocation in existing_allocations:
            print(f"DEBUG DECLINE: Processing allocation {allocation.id} for {allocation.guest_name}")
            
            # If this was a double room, find the roommate
            if allocation.room_type == 'double' and allocation.vendor_accommodation_id:
                # Find roommate in the same vendor accommodation with same dates
                roommate_allocation = db.query(AccommodationAllocation).filter(
                    AccommodationAllocation.vendor_accommodation_id == allocation.vendor_accommodation_id,
                    AccommodationAllocation.room_type == 'double',
                    AccommodationAllocation.check_in_date == allocation.check_in_date,
                    AccommodationAllocation.check_out_date == allocation.check_out_date,
                    AccommodationAllocation.id != allocation.id,
                    AccommodationAllocation.status.in_(["booked", "checked_in"])
                ).first()
                
                if roommate_allocation:
                    print(f"DEBUG DECLINE: Found roommate {roommate_allocation.guest_name}, reallocating...")
                    
                    # Try to find another single person to pair with
                    single_person = db.query(AccommodationAllocation).filter(
                        AccommodationAllocation.event_id == event_id,
                        AccommodationAllocation.room_type == 'single',
                        AccommodationAllocation.vendor_accommodation_id == allocation.vendor_accommodation_id,
                        AccommodationAllocation.check_in_date == allocation.check_in_date,
                        AccommodationAllocation.check_out_date == allocation.check_out_date,
                        AccommodationAllocation.status.in_(["booked", "checked_in"])
                    ).first()
                    
                    if single_person:
                        # Merge the single person with the roommate
                        print(f"DEBUG DECLINE: Merging {single_person.guest_name} with {roommate_allocation.guest_name}")
                        
                        # Update both to double room
                        single_person.room_type = 'double'
                        roommate_allocation.room_type = 'double'
                        
                        # Add roommate names
                        if hasattr(single_person, 'roommate_name'):
                            single_person.roommate_name = roommate_allocation.guest_name
                        if hasattr(roommate_allocation, 'roommate_name'):
                            roommate_allocation.roommate_name = single_person.guest_name
                        
                        # Restore one single room (since we're converting 2 singles to 1 double)
                        setup_query = text("""
                            SELECT accommodation_setup_id FROM events WHERE id = :event_id
                        """)
                        setup_result = db.execute(setup_query, {"event_id": event_id}).first()
                        
                        if setup_result and setup_result[0]:
                            db.execute(text("""
                                UPDATE vendor_event_accommodations 
                                SET single_rooms = single_rooms + 1 
                                WHERE id = :setup_id
                            """), {"setup_id": setup_result[0]})
                        
                        print(f"DEBUG DECLINE: Successfully merged rooms")
                    else:
                        # No single person to merge with, convert roommate to single
                        print(f"DEBUG DECLINE: No single person found, converting {roommate_allocation.guest_name} to single room")
                        roommate_allocation.room_type = 'single'
                        
                        # Clear roommate name if it exists
                        if hasattr(roommate_allocation, 'roommate_name'):
                            roommate_allocation.roommate_name = None
            
            # Delete the declining participant's allocation
            print(f"DEBUG DECLINE: Deleting allocation {allocation.id}")
            
            # Restore room counts
            if allocation.vendor_accommodation_id:
                setup_query = text("""
                    SELECT accommodation_setup_id FROM events WHERE id = :event_id
                """)
                setup_result = db.execute(setup_query, {"event_id": event_id}).first()
                
                if setup_result and setup_result[0]:
                    if allocation.room_type == 'single':
                        db.execute(text("""
                            UPDATE vendor_event_accommodations 
                            SET single_rooms = single_rooms + 1 
                            WHERE id = :setup_id
                        """), {"setup_id": setup_result[0]})
                    elif allocation.room_type == 'double':
                        db.execute(text("""
                            UPDATE vendor_event_accommodations 
                            SET double_rooms = double_rooms + 1 
                            WHERE id = :setup_id
                        """), {"setup_id": setup_result[0]})
            
            db.delete(allocation)
        
        db.commit()
        print(f"DEBUG DECLINE: Completed reallocation for {len(existing_allocations)} allocations")
        
    except Exception as e:
        print(f"DEBUG DECLINE: Error in reallocation: {str(e)}")
        import traceback
        print(f"DEBUG DECLINE: Traceback: {traceback.format_exc()}")
        db.rollback()
        raise e

async def send_role_change_notification(participant, old_role, new_role, db):
    """Send email notification when participant role changes"""
    try:
        if not participant.email or not participant.email.strip():
            return False
        
        from app.models.event import Event
        event = db.query(Event).filter(Event.id == participant.event_id).first()
        if not event:
            return False
        
        from app.core.email_service import email_service
        
        subject = f"Role Updated - {event.title}"
        
        role_descriptions = {
            'visitor': 'Event Participant',
            'facilitator': 'Event Facilitator', 
            'organizer': 'Event Organizer'
        }
        
        message = f"""
        <p>Dear {participant.full_name},</p>
        <p>Your role for <strong>{event.title}</strong> has been updated.</p>
        
        <div style="margin: 20px 0; padding: 20px; background-color: #f0f9ff; border-left: 4px solid #3b82f6;">
            <h3>Role Change Details:</h3>
            <p><strong>Event:</strong> {event.title}</p>
            <p><strong>Previous Role:</strong> {role_descriptions.get(old_role, old_role.title())}</p>
            <p><strong>New Role:</strong> {role_descriptions.get(new_role, new_role.title())}</p>
        </div>
        
        <p>Please check the Msafiri mobile app for any updated responsibilities or information related to your new role.</p>
        """
        
        return email_service.send_notification_email(
            to_email=participant.email,
            user_name=participant.full_name,
            title=subject,
            message=message
        )
        
    except Exception as e:
        print(f"Error sending role change notification: {e}")
        return False

@router.get("/{participant_id}/details", operation_id="get_participant_details_unique")
def get_participant_details(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_id: int
) -> Any:
    """Get detailed participant information including registration data"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Get registration data from public_registrations table
    from sqlalchemy import text
    registration_result = db.execute(
        text("""
            SELECT gender_identity, accommodation_needs 
            FROM public_registrations 
            WHERE event_id = :event_id AND (personal_email = :email OR msf_email = :email)
            LIMIT 1
        """),
        {"event_id": event_id, "email": participant.email}
    ).first()
    
    gender = None
    accommodation_needs = None
    travelling_from_country = None
    
    if registration_result:
        gender_identity = registration_result[0]
        accommodation_needs = registration_result[1]
        travelling_from_country = registration_result[2]
        
        # Convert gender_identity to standard format
        if gender_identity:
            if gender_identity.lower() in ['man', 'male']:
                gender = 'male'
            elif gender_identity.lower() in ['woman', 'female']:
                gender = 'female'
            else:
                gender = 'other'
    
    result = {
        "id": participant.id,
        "name": participant.full_name,
        "email": participant.email,
        "role": participant.role,
        "gender": gender,
        "accommodation_needs": accommodation_needs,
        "travelling_from_country": travelling_from_country
    }
    
    return result

@router.put("/{participant_id}/status", operation_id="update_participant_status_unique")
async def update_participant_status(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_id: int,
    status_data: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update participant status with auto-booking"""
    
    # Check permissions - allow vetting approvers during approval phase
    from app.core.permissions import can_edit_vetting_participants
    from app.models.user import UserRole
    
    has_admin_permission = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    has_vetting_permission = can_edit_vetting_participants(current_user, db, event_id)
    
    if not (has_admin_permission or has_vetting_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update participant status"
        )
    
    print(f"DEBUG STATUS UPDATE: Starting status update for participant {participant_id} in event {event_id}")
    print(f"DEBUG STATUS UPDATE: Status data: {status_data}")
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    print(f"DEBUG STATUS UPDATE: Found participant: {participant.full_name}")
    
    # Validate status
    valid_statuses = ['invited', 'confirmed', 'declined', 'waiting', 'selected', 'attended']
    new_status = status_data.get('status', '').lower()
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    old_status = participant.status
    print(f"DEBUG STATUS UPDATE: Status change - Old: {old_status}, New: {new_status}")
    
    # Update status
    try:
        participant.status = new_status
        db.commit()
        print(f"DEBUG STATUS UPDATE: Database updated successfully")
        
        # Trigger auto-booking if status changed to confirmed
        if new_status == 'confirmed' and old_status != 'confirmed':
            print(f"DEBUG STATUS UPDATE: Triggering auto-booking for newly confirmed participant")
            
            from app.api.v1.endpoints.auto_booking import _auto_book_participant_internal
            
            # Create a mock user for auto-booking
            class MockUser:
                def __init__(self):
                    self.tenant_id = "msf-oca"
                    self.id = 1
            
            mock_user = MockUser()
            tenant_context = "msf-oca"
            
            try:
                booking_result = _auto_book_participant_internal(
                    event_id=event_id,
                    participant_id=participant_id,
                    db=db,
                    current_user=mock_user,
                    tenant_context=tenant_context
                )
                print(f"DEBUG STATUS UPDATE: Auto-booking completed: {booking_result}")
            except Exception as e:
                print(f"DEBUG STATUS UPDATE: Auto-booking failed: {str(e)}")
                import traceback
                print(f"DEBUG STATUS UPDATE: Traceback: {traceback.format_exc()}")
        
        # Remove accommodation if status changed from confirmed to something else
        elif old_status == 'confirmed' and new_status != 'confirmed':
            print(f"DEBUG STATUS UPDATE: Removing accommodation for no longer confirmed participant")
            await handle_participant_decline_reallocation(event_id, participant_id, db)
        
        print(f"DEBUG STATUS UPDATE: Process completed successfully")
        return {"message": "Status updated successfully", "new_status": new_status}
        
    except Exception as e:
        db.rollback()
        print(f"DEBUG STATUS UPDATE: Error updating participant status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update status")

@router.get("/permissions", operation_id="get_participant_edit_permissions")
def get_participant_edit_permissions(
    *,
    db: Session = Depends(get_db),
    event_id: int = None,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Check if current user can edit participants for this event"""
    
    from app.core.permissions import can_edit_vetting_participants
    from app.models.user import UserRole
    from app.models.vetting_committee import VettingCommittee, VettingStatus
    
    has_admin_permission = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    has_vetting_permission = can_edit_vetting_participants(current_user, db, event_id)
    
    # Get vetting status for frontend
    committee = db.query(VettingCommittee).filter(
        VettingCommittee.event_id == event_id
    ).first()
    
    vetting_status = None
    can_approve_vetting = False
    
    if committee:
        vetting_status = committee.status.value if committee.status else None
        # Check if current user can approve vetting
        can_approve_vetting = (
            current_user.role == UserRole.VETTING_APPROVER and 
            committee.approver_email == current_user.email and
            committee.status == VettingStatus.PENDING_APPROVAL
        )
    
    return {
        "can_edit": has_admin_permission or has_vetting_permission,
        "has_admin_permission": has_admin_permission,
        "has_vetting_permission": has_vetting_permission,
        "vetting_status": vetting_status,
        "can_approve_vetting": can_approve_vetting
    }

@router.delete("/{participant_id}", operation_id="delete_event_participant_unique")
def delete_participant(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_id: int
) -> Any:
    """Delete event participant"""
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    db.delete(participant)
    db.commit()
    
    return {"message": "Participant deleted successfully"}