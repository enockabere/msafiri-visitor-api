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
    
    logger.info(f"🔥 ROLE UPDATE ENDPOINT HIT - Event: {event_id}, Participant: {participant_id}")
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
    print(f"DEBUG ROLE UPDATE: Participant: {participation.full_name}, Old: {old_role}, New: {new_role}")
    logger.info(f"🔄 Role change - Participant: {participation.full_name}, Old: {old_role}, New: {new_role}")
    
    # Update both role fields to ensure consistency
    participation.role = new_role
    participation.participant_role = new_role
    db.commit()
    print(f"DEBUG ROLE UPDATE: Database updated successfully")
    
    # Force accommodation reallocation for confirmed participants
    print(f"DEBUG ROLE UPDATE: Participant status: {participation.status}")
    if participation.status == 'confirmed':
        print(f"DEBUG ROLE UPDATE: Starting accommodation reallocation for confirmed participant")
        logger.info(f"Starting accommodation reallocation for confirmed participant")
        
        from app.models.guesthouse import AccommodationAllocation
        from sqlalchemy import text
        
        # Delete ALL existing allocations for this participant
        existing_allocations = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participant_id,
            AccommodationAllocation.status.in_(["booked", "checked_in"])
        ).all()
        
        for allocation in existing_allocations:
            print(f"DEBUG ROLE UPDATE: Deleting allocation {allocation.id} for {allocation.guest_name} (room_type: {allocation.room_type})")
            logger.info(f"Deleting allocation {allocation.id} for {allocation.guest_name}")
            
            # Restore room counts
            if allocation.vendor_accommodation_id:
                if allocation.room_type == 'single':
                    print(f"DEBUG ROLE UPDATE: Restoring 1 single room to vendor {allocation.vendor_accommodation_id}")
                    db.execute(text("""
                        UPDATE vendor_accommodations 
                        SET single_rooms = single_rooms + 1 
                        WHERE id = :vendor_id
                    """), {"vendor_id": allocation.vendor_accommodation_id})
                elif allocation.room_type == 'double':
                    print(f"DEBUG ROLE UPDATE: Restoring 1 double room to vendor {allocation.vendor_accommodation_id}")
                    db.execute(text("""
                        UPDATE vendor_accommodations 
                        SET double_rooms = double_rooms + 1 
                        WHERE id = :vendor_id
                    """), {"vendor_id": allocation.vendor_accommodation_id})
            
            db.delete(allocation)
        
        db.commit()
        print(f"DEBUG ROLE UPDATE: Deleted {len(existing_allocations)} existing allocations")
        logger.info(f"Deleted {len(existing_allocations)} existing allocations")
        
        # Trigger auto-booking with new role
        try:
            from app.api.v1.endpoints.auto_booking import _auto_book_participant_internal
            
            tenant_context = current_user.tenant_id or "default"
            print(f"DEBUG ROLE UPDATE: Triggering auto booking with role: {new_role}, tenant_context: {tenant_context}")
            logger.info(f"Triggering auto booking with role: {new_role}")
            
            booking_result = _auto_book_participant_internal(
                event_id=event_id,
                participant_id=participation.id,
                db=db,
                current_user=current_user,
                tenant_context=tenant_context
            )
            print(f"DEBUG ROLE UPDATE: Auto booking completed: {booking_result}")
            logger.info(f"Auto booking completed: {booking_result}")
            
        except Exception as e:
            print(f"DEBUG ROLE UPDATE: Auto booking failed: {str(e)}")
            logger.error(f"Auto booking failed: {str(e)}")
            import traceback
            print(f"DEBUG ROLE UPDATE: Traceback: {traceback.format_exc()}")
            logger.error(traceback.format_exc())
    
    print(f"DEBUG ROLE UPDATE: Process completed successfully")
    return {
        "message": f"Role updated from {old_role} to {new_role}",
        "old_role": old_role,
        "new_role": new_role
    }