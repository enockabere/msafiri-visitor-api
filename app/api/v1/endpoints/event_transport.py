from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from typing import List
from datetime import datetime, date
from app.db.database import get_db
from app.models.event_transport import EventRide, RideAssignment, RideRequest, RideStatus
from app.models.event_participant import EventParticipant
from app.models.event import Event
from app.schemas.event_transport import (
    EventRideCreate, EventRide as RideSchema,
    RideAssignmentCreate, RideAssignment as AssignmentSchema,
    RideRequestCreate, RideRequest as RequestSchema,
    VisitorRideView, AdminRideAllocation, RideRequestAction
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

# Admin endpoints for ride management
@router.post("/rides/", response_model=RideSchema)
def create_event_ride(
    ride: EventRideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin creates event ride"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_ride = EventRide(
        **ride.dict(),
        created_by=current_user.email
    )
    db.add(db_ride)
    db.commit()
    db.refresh(db_ride)
    return db_ride

@router.get("/rides/{event_id}", response_model=List[RideSchema])
def get_event_rides(event_id: int, db: Session = Depends(get_db)):
    """Get all rides for an event"""
    return db.query(EventRide).filter(EventRide.event_id == event_id).all()

@router.post("/assignments/", response_model=AssignmentSchema)
def assign_participant_to_ride(
    assignment: RideAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin assigns participant to ride"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check ride capacity
    ride = db.query(EventRide).filter(EventRide.id == assignment.ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    if ride.current_occupancy >= ride.max_capacity:
        raise HTTPException(status_code=400, detail="Ride is at full capacity")
    
    # Check if participant already assigned to this event
    existing = db.query(RideAssignment).join(
        EventRide, RideAssignment.ride_id == EventRide.id
    ).filter(
        and_(
            RideAssignment.participant_id == assignment.participant_id,
            EventRide.event_id == ride.event_id
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Participant already has ride for this event")
    
    # Create assignment
    db_assignment = RideAssignment(
        **assignment.dict(),
        assigned_by=current_user.email
    )
    db.add(db_assignment)
    
    # Update ride occupancy
    ride.current_occupancy += 1
    
    db.commit()
    db.refresh(db_assignment)
    
    # Send notification
    from app.core.notifications import notify_ride_assigned
    participant = db.query(EventParticipant).filter(EventParticipant.id == assignment.participant_id).first()
    if participant:
        notify_ride_assigned(participant.email, {
            "destination": ride.destination,
            "departure_time": str(ride.departure_time),
            "driver_name": ride.driver_name
        })
    
    return db_assignment

@router.get("/allocation-helper/{event_id}", response_model=AdminRideAllocation)
def get_ride_allocation_helper(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin helper to see participants by location for ride allocation"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get event details
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get all participants for this event
    participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id
    ).all()
    
    # Get existing ride assignments
    assigned_participant_ids = db.query(RideAssignment.participant_id).join(
        EventRide, RideAssignment.ride_id == EventRide.id
    ).filter(EventRide.event_id == event_id).all()
    assigned_ids = {pid[0] for pid in assigned_participant_ids}
    
    # Group unassigned participants by their accommodation location
    from app.models.accommodation import RoomAssignment
    participants_by_location = {}
    unassigned_participants = []
    
    for participant in participants:
        if participant.id in assigned_ids:
            continue
            
        # Get participant's accommodation
        room = db.query(RoomAssignment).filter(
            RoomAssignment.participant_id == participant.id
        ).first()
        
        location = room.hotel_name if room else "No accommodation assigned"
        
        if location not in participants_by_location:
            participants_by_location[location] = []
        
        participant_data = {
            "participant_id": participant.id,
            "name": participant.full_name or participant.email,
            "email": participant.email,
            "location": location
        }
        
        participants_by_location[location].append(participant_data)
        unassigned_participants.append(participant_data)
    
    # Format for response
    location_groups = [
        {
            "location": location,
            "participant_count": len(participants),
            "participants": participants
        }
        for location, participants in participants_by_location.items()
    ]
    
    # Get available rides
    available_rides = db.query(EventRide).filter(
        and_(
            EventRide.event_id == event_id,
            EventRide.current_occupancy < EventRide.max_capacity
        )
    ).all()
    
    rides_data = [
        {
            "ride_id": ride.id,
            "departure_location": ride.departure_location,
            "destination": ride.destination,
            "departure_time": ride.departure_time,
            "available_seats": ride.max_capacity - ride.current_occupancy,
            "driver_name": ride.driver_name
        }
        for ride in available_rides
    ]
    
    return AdminRideAllocation(
        event_id=event_id,
        destination=event.location or "Event Location",
        participants_by_location=location_groups,
        available_rides=rides_data,
        unassigned_participants=unassigned_participants
    )

# Visitor ride requests
@router.post("/requests/", response_model=RequestSchema)
def create_ride_request(
    request: RideRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor requests ride to event"""
    
    # Get participant record
    participant = db.query(EventParticipant).filter(
        and_(
            EventParticipant.email == current_user.email,
            EventParticipant.event_id == request.event_id
        )
    ).first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Not registered for this event")
    
    # Check if already has ride or request
    existing_assignment = db.query(RideAssignment).join(
        EventRide, RideAssignment.ride_id == EventRide.id
    ).filter(
        and_(
            RideAssignment.participant_id == participant.id,
            EventRide.event_id == request.event_id
        )
    ).first()
    
    if existing_assignment:
        raise HTTPException(status_code=400, detail="Already have ride assigned")
    
    existing_request = db.query(RideRequest).filter(
        and_(
            RideRequest.participant_id == participant.id,
            RideRequest.event_id == request.event_id,
            RideRequest.status.in_(["pending", "approved"])
        )
    ).first()
    
    if existing_request:
        raise HTTPException(status_code=400, detail="Ride request already exists")
    
    # Create request
    db_request = RideRequest(
        participant_id=participant.id,
        **request.dict()
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request

@router.get("/my-rides/", response_model=List[VisitorRideView])
def get_my_rides(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor gets their allocated rides"""
    
    # Get user's ride assignments
    assignments = db.query(RideAssignment, EventRide, Event).join(
        EventRide, RideAssignment.ride_id == EventRide.id
    ).join(
        Event, EventRide.event_id == Event.id
    ).join(
        EventParticipant, RideAssignment.participant_id == EventParticipant.id
    ).filter(EventParticipant.email == current_user.email).all()
    
    result = []
    for assignment, ride, event in assignments:
        # Get fellow passengers
        fellow_assignments = db.query(RideAssignment, EventParticipant).join(
            EventParticipant, RideAssignment.participant_id == EventParticipant.id
        ).filter(
            and_(
                RideAssignment.ride_id == ride.id,
                EventParticipant.email != current_user.email
            )
        ).all()
        
        fellow_passengers = [
            {
                "name": p.full_name or p.email,
                "email": p.email,
                "confirmed": a.confirmed
            }
            for a, p in fellow_assignments
        ]
        
        result.append(VisitorRideView(
            ride_id=ride.id,
            departure_location=ride.departure_location,
            destination=ride.destination,
            departure_time=ride.departure_time,
            driver_name=ride.driver_name,
            driver_phone=ride.driver_phone,
            vehicle_details=ride.vehicle_details,
            pickup_location=assignment.pickup_location,
            pickup_time=assignment.pickup_time,
            fellow_passengers=fellow_passengers,
            status=ride.status.value,
            confirmed=assignment.confirmed
        ))
    
    return result

@router.post("/my-rides/{assignment_id}/confirm")
def confirm_my_ride(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Visitor confirms their ride"""
    
    assignment = db.query(RideAssignment).join(
        EventParticipant, RideAssignment.participant_id == EventParticipant.id
    ).filter(
        and_(
            RideAssignment.id == assignment_id,
            EventParticipant.email == current_user.email
        )
    ).first()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Ride assignment not found")
    
    assignment.confirmed = True
    db.commit()
    
    return {"message": "Ride confirmed"}

# Admin ride request management
@router.get("/requests/pending", response_model=List[dict])
def get_pending_ride_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin gets pending ride requests"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    requests = db.query(RideRequest, EventParticipant, Event).join(
        EventParticipant, RideRequest.participant_id == EventParticipant.id
    ).join(
        Event, RideRequest.event_id == Event.id
    ).filter(RideRequest.status == "pending").all()
    
    result = []
    for request, participant, event in requests:
        result.append({
            "request_id": request.id,
            "participant_name": participant.full_name or participant.email,
            "participant_email": participant.email,
            "event_title": event.title,
            "pickup_location": request.pickup_location,
            "preferred_time": request.preferred_time,
            "special_requirements": request.special_requirements,
            "created_at": request.created_at
        })
    
    return result

@router.post("/requests/{request_id}/action")
def handle_ride_request(
    request_id: int,
    action: RideRequestAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin approves/rejects/assigns ride request"""
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    request = db.query(RideRequest).filter(RideRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request.status = action.status
    request.admin_notes = action.admin_notes
    request.approved_by = current_user.email
    
    # If assigning to ride, create assignment
    if action.status == "assigned" and action.ride_id:
        assignment = RideAssignment(
            ride_id=action.ride_id,
            participant_id=request.participant_id,
            assigned_by=current_user.email
        )
        db.add(assignment)
        
        # Update ride occupancy
        ride = db.query(EventRide).filter(EventRide.id == action.ride_id).first()
        if ride:
            ride.current_occupancy += 1
    
    db.commit()
    return {"message": f"Request {action.status}"}
