from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class AccommodationType(str, Enum):
    GUESTHOUSE = "guesthouse"
    VENDOR = "vendor"

class RoomType(str, Enum):
    SINGLE = "single"
    DOUBLE = "double"
    SUITE = "suite"
    APARTMENT = "apartment"

class AllocationStatus(str, Enum):
    BOOKED = "booked"
    CHECKED_IN = "checked_in"
    RELEASED = "released"
    CANCELLED = "cancelled"

# Base schemas
class GuestHouseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = Field(None, max_length=500)
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True

class GuestHouseCreate(GuestHouseBase):
    pass

class GuestHouseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    location: Optional[str] = Field(None, max_length=500)
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class GuestHouse(GuestHouseBase):
    id: int
    tenant_id: int
    total_rooms: int = 0
    occupied_rooms: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Room schemas
class RoomBase(BaseModel):
    room_number: str = Field(..., min_length=1, max_length=50)
    room_type: RoomType
    capacity: int = Field(..., ge=1, le=10)
    description: Optional[str] = None
    amenities: Optional[str] = None
    is_active: bool = True

class RoomCreate(RoomBase):
    guesthouse_id: int

class RoomUpdate(BaseModel):
    room_number: Optional[str] = Field(None, min_length=1, max_length=50)
    room_type: Optional[RoomType] = None
    capacity: Optional[int] = Field(None, ge=1, le=10)
    description: Optional[str] = None
    amenities: Optional[str] = None
    is_active: Optional[bool] = None

class Room(RoomBase):
    id: int
    guesthouse_id: int
    tenant_id: int
    is_occupied: bool = False
    current_occupants: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Vendor accommodation schemas
class VendorAccommodationBase(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=200)
    accommodation_type: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=500)
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    single_rooms: int = Field(default=0, ge=0)
    double_rooms: int = Field(default=0, ge=0)
    description: Optional[str] = None
    is_active: bool = True

class VendorAccommodationCreate(VendorAccommodationBase):
    pass

class VendorAccommodationUpdate(BaseModel):
    vendor_name: Optional[str] = Field(None, min_length=1, max_length=200)
    accommodation_type: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=500)
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    single_rooms: Optional[int] = Field(None, ge=0)
    double_rooms: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    is_active: Optional[bool] = None

class VendorAccommodation(VendorAccommodationBase):
    id: int
    tenant_id: int
    current_occupants: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Allocation schemas
class AccommodationAllocationBase(BaseModel):
    guest_name: str = Field(..., min_length=1, max_length=200)
    guest_email: Optional[str] = Field(None, max_length=100)
    guest_phone: Optional[str] = Field(None, max_length=20)
    check_in_date: date
    check_out_date: date
    number_of_guests: int = Field(..., ge=1)
    purpose: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    participant_id: Optional[int] = None

class AccommodationAllocationCreate(AccommodationAllocationBase):
    accommodation_type: AccommodationType
    room_id: Optional[int] = None
    vendor_accommodation_id: Optional[int] = None
    event_id: Optional[int] = None

class AccommodationAllocationUpdate(BaseModel):
    guest_name: Optional[str] = Field(None, min_length=1, max_length=200)
    guest_email: Optional[str] = Field(None, max_length=100)
    guest_phone: Optional[str] = Field(None, max_length=20)
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    number_of_guests: Optional[int] = Field(None, ge=1)
    purpose: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    status: Optional[AllocationStatus] = None

class AccommodationAllocation(AccommodationAllocationBase):
    id: int
    tenant_id: int
    accommodation_type: AccommodationType
    room_id: Optional[int] = None
    vendor_accommodation_id: Optional[int] = None
    status: AllocationStatus = AllocationStatus.BOOKED
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None
    event_id: Optional[int] = None

    class Config:
        from_attributes = True