from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.guesthouse import AccommodationAllocation
from app.models.event_participant import EventParticipant
from sqlalchemy import text
from typing import Optional

router = APIRouter()

@router.post("/refresh-all")
async def refresh_all_accommodations(
    db: Session = Depends(get_db),
    x_tenant_id: Optional[str] = Header(None)
):
    """Refresh all accommodations by rebooking all confirmed visitors from all events"""
    
    try:
        print(f"DEBUG REFRESH: Starting accommodation refresh for tenant: {x_tenant_id}")
        
        # Get all confirmed participants from all events
        confirmed_participants = db.query(EventParticipant).filter(
            EventParticipant.status == 'confirmed'
        ).all()
        
        print(f"DEBUG REFRESH: Found {len(confirmed_participants)} confirmed participants")
        
        # Delete ALL existing allocations
        existing_allocations = db.query(AccommodationAllocation).filter(
            AccommodationAllocation.status.in_(["booked", "checked_in"])
        ).all()
        
        print(f"DEBUG REFRESH: Deleting {len(existing_allocations)} existing allocations")
        
        # Restore room counts for each deleted allocation
        for allocation in existing_allocations:
            if allocation.vendor_accommodation_id:
                # Find the accommodation setup for this event
                setup_query = text("""
                    SELECT accommodation_setup_id FROM events WHERE id = :event_id
                """)
                setup_result = db.execute(setup_query, {"event_id": allocation.event_id}).first()
                
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
        print(f"DEBUG REFRESH: Deleted all existing allocations")
        
        # Group participants by event and rebook each event
        events_to_rebook = {}
        for participant in confirmed_participants:
            if participant.event_id not in events_to_rebook:
                events_to_rebook[participant.event_id] = []
            events_to_rebook[participant.event_id].append(participant)
        
        print(f"DEBUG REFRESH: Rebooking {len(events_to_rebook)} events")
        
        total_rebooked = 0
        
        # Rebook each event
        for event_id, participants in events_to_rebook.items():
            try:
                print(f"DEBUG REFRESH: Rebooking event {event_id} with {len(participants)} participants")
                
                from app.api.v1.endpoints.auto_booking import auto_book_all_participants
                
                # Create a mock user for auto-booking
                class MockUser:
                    def __init__(self):
                        self.tenant_id = x_tenant_id or "msf-oca"
                        self.id = 1
                
                mock_user = MockUser()
                tenant_context = x_tenant_id or "msf-oca"
                
                # Call the mass auto-booking function
                booking_result = auto_book_all_participants(
                    event_id=event_id,
                    db=db,
                    current_user=mock_user,
                    tenant_context=tenant_context
                )
                
                if booking_result.get("success"):
                    total_rebooked += len(participants)
                    print(f"DEBUG REFRESH: Successfully rebooked event {event_id}")
                else:
                    print(f"DEBUG REFRESH: Failed to rebook event {event_id}: {booking_result}")
                
            except Exception as e:
                print(f"DEBUG REFRESH: Error rebooking event {event_id}: {str(e)}")
                import traceback
                print(f"DEBUG REFRESH: Traceback: {traceback.format_exc()}")
                continue
        
        print(f"DEBUG REFRESH: Completed refresh. Total rebooked: {total_rebooked}")
        
        return {
            "success": True,
            "message": "Accommodations refreshed successfully",
            "events_processed": len(events_to_rebook),
            "participants_found": len(confirmed_participants),
            "rebooked_count": total_rebooked,
            "allocations_cleared": len(existing_allocations)
        }
        
    except Exception as e:
        db.rollback()
        print(f"DEBUG REFRESH: Error in refresh process: {str(e)}")
        import traceback
        print(f"DEBUG REFRESH: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh accommodations: {str(e)}")
