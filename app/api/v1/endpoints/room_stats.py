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
    
    # Get room occupancy statistics using raw SQL
    result = db.execute(
        text("""
            SELECT 
                room_type,
                COUNT(*) as occupied_rooms,
                SUM(number_of_guests) as total_guests
            FROM accommodation_allocations aa
            WHERE aa.event_id = :event_id 
            AND aa.status IN ('booked', 'checked_in')
            GROUP BY room_type
        """),
        {"event_id": event_id}
    ).fetchall()
    
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
    
    # Initialize counters
    single_rooms_occupied = 0
    double_rooms_occupied = 0
    single_room_guests = 0
    double_room_guests = 0
    
    # Process results
    for row in result:
        if row.room_type == 'single':
            single_rooms_occupied = row.occupied_rooms
            single_room_guests = row.total_guests
        elif row.room_type == 'double':
            double_rooms_occupied = row.occupied_rooms
            double_room_guests = row.total_guests
    
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