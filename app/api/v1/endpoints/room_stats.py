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
    
    # Get room occupancy statistics - count actual rooms occupied
    result = db.execute(
        text("""
            SELECT 
                room_type,
                COUNT(CASE WHEN room_type = 'single' THEN 1 END) as single_allocations,
                COUNT(CASE WHEN room_type = 'double' THEN 1 END) as double_allocations,
                SUM(CASE WHEN room_type = 'single' THEN 1 ELSE 0 END) as single_guests,
                SUM(CASE WHEN room_type = 'double' THEN 2 ELSE 0 END) as double_guests
            FROM accommodation_allocations aa
            WHERE aa.event_id = :event_id 
            AND aa.status IN ('booked', 'checked_in')
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
    single_rooms_occupied = result.single_allocations if result else 0
    double_rooms_occupied = (result.double_allocations // 2) if result and result.double_allocations else 0
    single_room_guests = result.single_guests if result else 0
    double_room_guests = result.double_guests if result else 0
    
    return {
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