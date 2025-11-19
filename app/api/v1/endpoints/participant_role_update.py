# File: app/api/v1/endpoints/participant_role_update.py
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole

router = APIRouter()

@router.put("/{event_id}/participants/{participant_id}/role")
def update_participant_role(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    participant_id: int,
    role_update: dict,
    current_user: schemas.User = Depends(deps.get_current_user)
) -> Any:
    """Update participant role and trigger accommodation reallocation."""
    import logging
    logger = logging.getLogger(__name__)
    
    print(f"🔥🔥🔥 ROLE UPDATE ENDPOINT HIT - Event: {event_id}, Participant: {participant_id} 🔥🔥🔥")
    print(f"🔥🔥🔥 TIMESTAMP: {__import__('datetime').datetime.now()} 🔥🔥🔥")
    print(f"🔥🔥🔥 REQUEST PATH: /api/v1/events/{event_id}/participants/{participant_id}/role 🔥🔥🔥")
    logger.info(f"🔥 ROLE UPDATE ENDPOINT HIT - Event: {event_id}, Participant: {participant_id}")
    print(f"👤 Current user: {current_user.email}, Role: {current_user.role}")
    print(f"📝 Role update data: {role_update}")
    print(f"📝 Role update type: {type(role_update)}")
    logger.info(f"👤 Current user: {current_user.email}, Role: {current_user.role}")
    logger.info(f"📝 Role update data: {role_update}")
    
    # Check admin permissions
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]:
        logger.error(f"❌ Permission denied - User role: {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin roles can update participant roles"
        )
    
    from app.models.event_participant import EventParticipant
    
    # Find the participation record
    participation = db.query(EventParticipant).filter(
        EventParticipant.id == participant_id,
        EventParticipant.event_id == event_id
    ).first()
    
    if not participation:
        logger.error(f"❌ Participation record not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participation record not found"
        )
    
    new_role = role_update.get("role")
    if not new_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role is required"
        )
    
    old_role = participation.role
    print(f"🔄 Role change: {old_role} -> {new_role}")
    print(f"📊 Participant status: {participation.status}")
    print(f"📊 Participant name: {participation.full_name}")
    print(f"📊 Participant email: {participation.email}")
    
    # Update both role fields to ensure consistency
    participation.role = new_role
    participation.participant_role = new_role
    
    try:
        db.commit()
        print(f"✅ Database commit successful - role updated")
    except Exception as e:
        print(f"❌ Database commit failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update role: {str(e)}")
    
    # Force accommodation reallocation for confirmed participants
    print(f"🏨 Checking if accommodation reallocation needed...")
    print(f"🏨 Participation status: {participation.status}")
    print(f"🏨 Role changed: {old_role != new_role}")
    
    if participation.status == 'confirmed':
        print(f"🏨 Participant is confirmed, proceeding with accommodation reallocation")
        
        from app.models.guesthouse import AccommodationAllocation
        from sqlalchemy import text
        
        # Delete ALL existing allocations for this participant
        print(f"🗑️ Searching for existing accommodation allocations...")
        existing_allocations = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participant_id,
            AccommodationAllocation.status.in_(["booked", "checked_in"])
        ).all()
        
        print(f"🗑️ Found {len(existing_allocations)} existing allocations to delete")
        
        for allocation in existing_allocations:
            print(f"🗑️ Deleting allocation ID {allocation.id}, type: {allocation.accommodation_type}, room_type: {getattr(allocation, 'room_type', 'N/A')}")
            
            # Restore room counts to vendor_event_accommodations
            if allocation.vendor_accommodation_id:
                # Find the accommodation setup for this event
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
        
        # Trigger auto-booking with new role
        print(f"🏨 Starting auto-booking with new role: {new_role}")
        try:
            from app.api.v1.endpoints.auto_booking import _auto_book_participant_internal
            
            tenant_context = str(current_user.tenant_id) if current_user.tenant_id else "default"
            print(f"🏨 Using tenant_context: {tenant_context}")
            
            booking_result = _auto_book_participant_internal(
                event_id=event_id,
                participant_id=participation.id,
                db=db,
                current_user=current_user,
                tenant_context=tenant_context
            )
            
            print(f"🏨 Auto-booking result: {booking_result}")
            
        except Exception as e:
            print(f"⚠️ Auto-booking failed: {e}")
            print(f"⚠️ Exception type: {type(e)}")
            import traceback
            print(f"⚠️ Traceback: {traceback.format_exc()}")
            pass  # Continue even if auto-booking fails
    

    print(f"🎉 Role update process completed successfully")
    print(f"🎉 Final result: {old_role} -> {new_role}")
    
    return {
        "message": f"Role updated from {old_role} to {new_role}",
        "old_role": old_role,
        "new_role": new_role
    }