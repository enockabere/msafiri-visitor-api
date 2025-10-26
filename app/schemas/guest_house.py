from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Guest House Schemas
class GuestHouseBase(BaseModel):
    name: str
    location: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    facilities: Optional[Dict[str, Any]] = None
    house_rules: Optional[str] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None

class GuestHouseCreate(GuestHouseBase):
    tenant_id: str

class GuestHouseUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    facilities: Optional[Dict[str, Any]] = None
    house_rules: Optional[str] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    is_active: Optional[bool] = None

# Guest House Room Schemas
class GuestHouseRoomBase(BaseModel):
    room_number: str
    room_name: Optional[str] = None
    capacity: int = Field(gt=0, description="Number of people the room can accommodate")
    room_type: Optional[str] = None
    facilities: Optional[Dict[str, Any]] = None
    description: Optional[str] = None

class GuestHouseRoomCreate(GuestHouseRoomBase):
    guest_house_id: int

class GuestHouseRoomUpdate(BaseModel):
    room_number: Optional[str] = None
    room_name: Optional[str] = None
    capacity: Optional[int] = Field(None, gt=0)
    room_type: Optional[str] = None
    facilities: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class GuestHouseRoom(GuestHouseRoomBase):
    id: int
    guest_house_id: int
    is_active: bool
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True

class GuestHouse(GuestHouseBase):
    id: int
    tenant_id: str
    is_active: bool
    created_at: datetime
    created_by: str
    rooms: List[GuestHouseRoom] = []

    class Config:
        from_attributes = True

# Guest House Booking Schemas
class GuestHouseBookingBase(BaseModel):
    check_in_date: datetime
    check_out_date: datetime
    number_of_guests: int = Field(default=1, gt=0)
    special_requests: Optional[str] = None

class GuestHouseBookingCreate(GuestHouseBookingBase):
    guest_house_id: int
    room_id: int
    participant_id: int

class GuestHouseBookingUpdate(BaseModel):
    check_in_date: Optional[datetime] = None
    check_out_date: Optional[datetime] = None
    number_of_guests: Optional[int] = Field(None, gt=0)
    special_requests: Optional[str] = None
    admin_notes: Optional[str] = None
    status: Optional[str] = None

class ParticipantInfo(BaseModel):
    id: int
    full_name: str
    email: str
    event_title: Optional[str] = None

class GuestHouseBooking(GuestHouseBookingBase):
    id: int
    guest_house_id: int
    room_id: int
    participant_id: int
    status: str
    checked_in: bool
    checked_in_at: Optional[datetime] = None
    checked_out: bool
    checked_out_at: Optional[datetime] = None
    admin_notes: Optional[str] = None
    booked_by: str
    booking_reference: Optional[str] = None
    created_at: datetime
    
    # Related data
    guest_house_name: Optional[str] = None
    room_number: Optional[str] = None
    participant: Optional[ParticipantInfo] = None

    class Config:
        from_attributes = True

# Room availability check
class RoomAvailabilityCheck(BaseModel):
    room_id: int
    check_in_date: datetime
    check_out_date: datetime

class RoomAvailabilityResponse(BaseModel):
    room_id: int
    room_number: str
    is_available: bool
    conflicting_bookings: List[Dict[str, Any]] = []

# Booking conflict check
class BookingConflictCheck(BaseModel):
    participant_id: int
    check_in_date: datetime
    check_out_date: datetime

class BookingConflictResponse(BaseModel):
    has_conflicts: bool
    conflicting_bookings: List[Dict[str, Any]] = []
    available_dates: List[Dict[str, str]] = []