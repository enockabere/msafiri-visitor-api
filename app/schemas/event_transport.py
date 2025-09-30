from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class EventRideBase(BaseModel):
    departure_location: str
    destination: str
    departure_time: datetime
    driver_name: str
    driver_phone: str
    vehicle_details: Optional[str] = None
    max_capacity: int = 4
    special_instructions: Optional[str] = None

class EventRideCreate(EventRideBase):
    event_id: int

class EventRide(EventRideBase):
    id: int
    event_id: int
    current_occupancy: int
    status: str
    created_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class RideAssignmentBase(BaseModel):
    pickup_location: Optional[str] = None
    pickup_time: Optional[datetime] = None

class RideAssignmentCreate(RideAssignmentBase):
    ride_id: int
    participant_id: int

class RideAssignment(RideAssignmentBase):
    id: int
    ride_id: int
    participant_id: int
    confirmed: bool
    boarded: bool
    assigned_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class RideRequestBase(BaseModel):
    pickup_location: str
    preferred_time: datetime
    special_requirements: Optional[str] = None

class RideRequestCreate(RideRequestBase):
    event_id: int

class RideRequest(RideRequestBase):
    id: int
    participant_id: int
    event_id: int
    status: str
    admin_notes: Optional[str] = None
    approved_by: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class VisitorRideView(BaseModel):
    ride_id: int
    departure_location: str
    destination: str
    departure_time: datetime
    driver_name: str
    driver_phone: str
    vehicle_details: Optional[str] = None
    pickup_location: Optional[str] = None
    pickup_time: Optional[datetime] = None
    fellow_passengers: List[dict]
    status: str
    confirmed: bool

class AdminRideAllocation(BaseModel):
    event_id: int
    destination: str
    participants_by_location: List[dict]
    available_rides: List[dict]
    unassigned_participants: List[dict]

class RideRequestAction(BaseModel):
    status: str  # "approved", "rejected", "assigned"
    admin_notes: Optional[str] = None
    ride_id: Optional[int] = None  # For assignment