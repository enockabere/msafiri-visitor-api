from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class BookingTypeEnum(str, Enum):
    AIRPORT_PICKUP = "airport_pickup"
    EVENT_TRANSFER = "event_transfer"
    OFFICE_VISIT = "office_visit"
    CUSTOM = "custom"

class BookingStatusEnum(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PACKAGE_COLLECTED = "package_collected"
    VISITOR_PICKED_UP = "visitor_picked_up"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class VendorTypeEnum(str, Enum):
    ABSOLUTE_TAXI = "absolute_taxi"
    MANUAL_VENDOR = "manual_vendor"

class TransportBookingBase(BaseModel):
    booking_type: BookingTypeEnum
    participant_ids: List[int]
    pickup_locations: List[str]
    destination: str
    scheduled_time: datetime
    has_welcome_package: bool = False
    package_pickup_location: Optional[str] = None
    vendor_type: VendorTypeEnum
    vendor_name: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    driver_email: Optional[str] = None
    vehicle_details: Optional[str] = None
    special_instructions: Optional[str] = None
    flight_number: Optional[str] = None
    arrival_time: Optional[datetime] = None
    event_id: Optional[int] = None

class TransportBookingCreate(TransportBookingBase):
    pass

class TransportBookingUpdate(BaseModel):
    status: Optional[BookingStatusEnum] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    driver_email: Optional[str] = None
    vehicle_details: Optional[str] = None
    special_instructions: Optional[str] = None
    admin_notes: Optional[str] = None

class TransportBooking(TransportBookingBase):
    id: int
    status: BookingStatusEnum
    package_collected: bool
    package_collected_at: Optional[datetime] = None
    package_collected_by: Optional[str] = None
    visitor_picked_up: bool
    visitor_picked_up_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    external_booking_id: Optional[str] = None
    admin_notes: Optional[str] = None
    created_by: str
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    
    # Participant details (populated from relationships)
    participants: Optional[List[Dict[str, Any]]] = None
    event_title: Optional[str] = None
    
    class Config:
        from_attributes = True

class TransportStatusUpdateCreate(BaseModel):
    status: BookingStatusEnum
    notes: Optional[str] = None
    location: Optional[str] = None

class TransportStatusUpdate(BaseModel):
    id: int
    booking_id: int
    status: BookingStatusEnum
    notes: Optional[str] = None
    location: Optional[str] = None
    updated_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TransportVendorBase(BaseModel):
    name: str
    vendor_type: VendorTypeEnum
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    api_config: Optional[Dict[str, Any]] = None
    is_active: bool = True

class TransportVendorCreate(TransportVendorBase):
    pass

class TransportVendor(TransportVendorBase):
    id: int
    created_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookingGroupRequest(BaseModel):
    """Request to group participants for shared bookings"""
    event_id: Optional[int] = None
    booking_type: BookingTypeEnum
    destination: str
    scheduled_time: datetime
    group_by_accommodation: bool = True
    max_passengers_per_booking: int = 4

class BookingGroupResponse(BaseModel):
    """Response with suggested booking groups"""
    suggested_groups: List[Dict[str, Any]]
    ungrouped_participants: List[Dict[str, Any]]

class WelcomePackageCheck(BaseModel):
    """Response for checking if participants have welcome packages"""
    participant_id: int
    has_package: bool
    package_items: List[str]