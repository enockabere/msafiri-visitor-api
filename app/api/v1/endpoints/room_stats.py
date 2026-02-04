from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db

router = APIRouter()

@router.get("/{event_id}/room-stats")
def get_event_room_stats(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> dict:
    """Get detailed room statistics for an event"""
    import logging
    logger = logging.getLogger(__name__)
    
    
    # Debug: Check all allocations for this event
    debug_result = db.execute(
        text("""
            SELECT id, room_type, status, participant_id, vendor_accommodation_id, check_in_date, check_out_date
            FROM accommodation_allocations aa
            WHERE aa.event_id = :event_id
        """),
        {"event_id": event_id}
    ).fetchall()
    
    # Get room occupancy statistics - count actual rooms occupied
    single_result = db.execute(
        text("""
            SELECT 
                COUNT(*) as single_rooms_occupied,
                COUNT(*) as single_guests
            FROM accommodation_allocations aa
            WHERE aa.event_id = :event_id 
            AND aa.status IN ('booked', 'checked_in')
            AND aa.room_type = 'single'
        """),
        {"event_id": event_id}
    ).fetchone()
    

    
    # For double rooms, count unique shared rooms (2 people = 1 room)
    double_result = db.execute(
        text("""
            SELECT 
                COUNT(DISTINCT CONCAT(aa.vendor_accommodation_id, '-', aa.check_in_date, '-', aa.check_out_date)) as double_rooms_occupied,
                COUNT(*) as double_guests
            FROM accommodation_allocations aa
            WHERE aa.event_id = :event_id 
            AND aa.status IN ('booked', 'checked_in')
            AND aa.room_type = 'double'
        """),
        {"event_id": event_id}
    ).fetchone()
    

    
    # Get event room planning details
    event_result = db.execute(
        text("""
            SELECT single_rooms, double_rooms, expected_participants
            FROM events 
            WHERE id = :event_id
        """),
        {"event_id": event_id}
    ).fetchone()
    
    if not event_result:
        raise HTTPException(status_code=404, detail="Event not found")
    

    
    # Calculate room occupancy
    single_rooms_occupied = single_result.single_rooms_occupied if single_result else 0
    double_rooms_occupied = double_result.double_rooms_occupied if double_result else 0
    single_room_guests = single_result.single_guests if single_result else 0
    double_room_guests = double_result.double_guests if double_result else 0
    
    result = {
        "single_rooms": {
            "occupied": single_rooms_occupied,
            "total": event_result.single_rooms or 0,
            "guests": single_room_guests
        },
        "double_rooms": {
            "occupied": double_rooms_occupied,
            "total": event_result.double_rooms or 0,
            "guests": double_room_guests
        },
        "expected_participants": event_result.expected_participants or 0,
        "total_capacity": (event_result.single_rooms or 0) + ((event_result.double_rooms or 0) * 2),
        "total_occupied_guests": single_room_guests + double_room_guests
    }
    

    return result