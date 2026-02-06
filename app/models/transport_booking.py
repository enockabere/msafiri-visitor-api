from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Enum, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class BookingType(enum.Enum):
    AIRPORT_PICKUP = "airport_pickup"
    EVENT_TRANSFER = "event_transfer"
    OFFICE_VISIT = "office_visit"
    CUSTOM = "custom"

class BookingStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PACKAGE_COLLECTED = "package_collected"
    VISITOR_PICKED_UP = "visitor_picked_up"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class VendorType(enum.Enum):
    ABSOLUTE_TAXI = "absolute_taxi"
    MANUAL_VENDOR = "manual_vendor"

class TransportBooking(BaseModel):
    __tablename__ = "transport_bookings"
    
    # Basic booking info
    booking_type = Column(Enum(BookingType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    status = Column(Enum(BookingStatus, values_callable=lambda obj: [e.value for e in obj]), default=BookingStatus.PENDING)
    
    # Participants (JSON array of participant IDs)
    participant_ids = Column(JSON, nullable=False)
    
    # Trip details
    pickup_locations = Column(JSON, nullable=False)  # Array of locations in order
    destination = Column(String(500), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    
    # Welcome package integration
    has_welcome_package = Column(Boolean, default=False)
    package_pickup_location = Column(String(500))  # MSF Office location
    package_collected = Column(Boolean, default=False)
    package_collected_at = Column(DateTime)
    package_collected_by = Column(String(255))
    
    # Vendor details
    vendor_type = Column(Enum(VendorType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    vendor_name = Column(String(255))
    driver_name = Column(String(255))
    driver_phone = Column(String(50))
    driver_email = Column(String(255))
    vehicle_details = Column(String(255))
    
    # API integration
    external_booking_id = Column(String(255))  # For Absolute Taxi API
    api_response = Column(JSON)  # Store API response
    
    # Instructions and notes
    special_instructions = Column(Text)
    admin_notes = Column(Text)
    
    # Tracking
    visitor_picked_up = Column(Boolean, default=False)
    visitor_picked_up_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Flight details (for airport pickups)
    flight_number = Column(String(50))
    arrival_time = Column(DateTime)
    
    # Event reference (for event transfers)
    event_id = Column(Integer, ForeignKey("events.id"))
    
    # Admin tracking
    created_by = Column(String(255), nullable=False)
    confirmed_by = Column(String(255))
    confirmed_at = Column(DateTime)
    
    # Relationships
    event = relationship("Event")
    status_updates = relationship("TransportStatusUpdate", back_populates="booking")

class TransportStatusUpdate(BaseModel):
    __tablename__ = "transport_status_updates"
    
    booking_id = Column(Integer, ForeignKey("transport_bookings.id"), nullable=False)
    status = Column(Enum(BookingStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    notes = Column(Text)
    location = Column(String(255))
    updated_by = Column(String(255), nullable=False)
    
    # Relationships
    booking = relationship("TransportBooking", back_populates="status_updates")

class TransportVendor(BaseModel):
    __tablename__ = "transport_vendors"
    
    name = Column(String(255), nullable=False)
    vendor_type = Column(Enum(VendorType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    contact_person = Column(String(255))
    phone = Column(String(50))
    email = Column(String(255))
    
    # API configuration (for Absolute Taxi)
    api_endpoint = Column(String(500))
    api_key = Column(String(255))
    api_config = Column(JSON)
    
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255), nullable=False)
