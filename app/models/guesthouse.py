from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base

class GuestHouse(Base):
    __tablename__ = "guesthouses"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    address = Column(Text, nullable=True)  # Legacy field
    location = Column(String(500), nullable=True)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    contact_person = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    facilities = Column(Text, nullable=True)  # JSON string
    house_rules = Column(Text, nullable=True)
    check_in_time = Column(String(10), nullable=True)
    check_out_time = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)
    total_rooms = Column(Integer, default=0)
    occupied_rooms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(200), nullable=True)

    # Relationships
    rooms = relationship("Room", back_populates="guesthouse", cascade="all, delete-orphan", lazy="select")

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    guesthouse_id = Column(Integer, ForeignKey("guesthouses.id"), nullable=False)
    tenant_id = Column(Integer, nullable=False, index=True)
    room_number = Column(String(50), nullable=False)
    room_type = Column(String(20), nullable=False)  # single, double, suite
    capacity = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    amenities = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_occupied = Column(Boolean, default=False)
    current_occupants = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    guesthouse = relationship("GuestHouse", back_populates="rooms")
    allocations = relationship("AccommodationAllocation", back_populates="room")

class VendorAccommodation(Base):
    __tablename__ = "vendor_accommodations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    vendor_name = Column(String(200), nullable=False)
    location = Column(String(500), nullable=True)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    contact_person = Column(String(200), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(100), nullable=True)
    capacity = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    current_occupants = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    allocations = relationship("AccommodationAllocation", back_populates="vendor_accommodation")

class AccommodationAllocation(Base):
    __tablename__ = "accommodation_allocations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    accommodation_type = Column(String(20), nullable=False)  # guesthouse, vendor
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    vendor_accommodation_id = Column(Integer, ForeignKey("vendor_accommodations.id"), nullable=True)
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    guest_name = Column(String(200), nullable=False)
    guest_email = Column(String(100), nullable=True)
    guest_phone = Column(String(20), nullable=True)
    check_in_date = Column(Date, nullable=False)
    check_out_date = Column(Date, nullable=False)
    number_of_guests = Column(Integer, nullable=False)
    purpose = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), default="booked")  # booked, checked_in, released, cancelled
    room_type = Column(String(20), nullable=True)  # single, double - for vendor accommodations
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, nullable=True)

    # Relationships
    room = relationship("Room", back_populates="allocations")
    vendor_accommodation = relationship("VendorAccommodation", back_populates="allocations")
    participant = relationship("EventParticipant", foreign_keys=[participant_id])
    event = relationship("Event", foreign_keys=[event_id])

class VendorEventAccommodation(Base):
    __tablename__ = "vendor_event_accommodations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    vendor_accommodation_id = Column(Integer, ForeignKey("vendor_accommodations.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)  # Nullable for custom events
    event_name = Column(String(200), nullable=True)  # For custom event names
    single_rooms = Column(Integer, default=0)
    double_rooms = Column(Integer, default=0)
    total_capacity = Column(Integer, nullable=False)  # Calculated: single_rooms + (double_rooms * 2)
    current_occupants = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(200), nullable=True)

    # Relationships
    vendor_accommodation = relationship("VendorAccommodation")
    event = relationship("Event", foreign_keys=[event_id])