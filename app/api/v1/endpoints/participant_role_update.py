# File: app/api/v1/endpoints/participant_role_update.py
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import schemas
from app.api import deps
from app.db.database import get_db
from app.models.user import UserRole

router = APIRouter()

# Test endpoint to verify routing
@router.get("/{event_id}/participants/{participant_id}/role-test")
def test_role_endpoint(
    event_id: int,
    participant_id: int
):
    """Test endpoint to verify routing works"""

    return {
        "message": "Role endpoint routing works",
        "event_id": event_id,
        "participant_id": participant_id,
        "timestamp": str(__import__('datetime').datetime.now())
    }

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
    
    logger.info(f"Role update endpoint - Event: {event_id}, Participant: {participant_id}")
    logger.info(f"Current user: {current_user.email}, Role: {current_user.role}")
    logger.info(f"Role update data: {role_update}")
    
    # Check permissions - allow vetting approvers during approval phase
    from app.core.permissions import can_edit_vetting_participants

    has_admin_permission = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN, UserRole.EVENT_ADMIN]
    vetting_permissions = can_edit_vetting_participants(current_user, db, event_id)
    has_vetting_permission = vetting_permissions['can_edit']

    if not (has_admin_permission or has_vetting_permission):
        logger.error(f"❌ Permission denied - User role: {current_user.role}, Reason: {vetting_permissions['reason']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions to update participant roles: {vetting_permissions['reason']}"
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

    
    # Update both role fields to ensure consistency
    participation.role = new_role
    participation.participant_role = new_role
    
    try:
        db.commit()

    except Exception as e:

        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update role: {str(e)}")
    
    # Force accommodation reallocation for confirmed participants

    
    if participation.status == 'confirmed':

        
        from app.models.guesthouse import AccommodationAllocation
        from sqlalchemy import text
        
        # Delete ALL existing allocations for this participant

        existing_allocations = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.participant_id == participant_id,
            AccommodationAllocation.status.in_(["booked", "checked_in"])
        ).all()
        

        
        for allocation in existing_allocations:

            
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

        try:
            from app.api.v1.endpoints.auto_booking import _auto_book_participant_internal
            
            tenant_context = str(current_user.tenant_id) if current_user.tenant_id else "default"

            
            booking_result = _auto_book_participant_internal(
                event_id=event_id,
                participant_id=participation.id,
                db=db,
                current_user=current_user,
                tenant_context=tenant_context
            )
            

            
        except Exception as e:
            import traceback
            pass  # Continue even if auto-booking fails

    return {
        "message": f"Role updated from {old_role} to {new_role}",
        "old_role": old_role,
        "new_role": new_role
    }
