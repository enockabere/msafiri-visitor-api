from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class GuestHouse(BaseModel):
    __tablename__ = "guest_houses"
    
    name = Column(String(255), nullable=False)
    location = Column(String(500), nullable=False)
    address = Column(Text, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    contact_person = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Facilities and amenities
    facilities = Column(JSON, nullable=True)  # WiFi, Kitchen, Parking, etc.
    house_rules = Column(Text, nullable=True)
    check_in_time = Column(String(10), nullable=True)  # e.g., "14:00"
    check_out_time = Column(String(10), nullable=True)  # e.g., "11:00"
    
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String(50), nullable=False)
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    rooms = relationship("GuestHouseRoom", back_populates="guest_house")
    bookings = relationship("GuestHouseBooking", back_populates="guest_house")

class GuestHouseRoom(BaseModel):
    __tablename__ = "guest_house_rooms"
    
    guest_house_id = Column(Integer, ForeignKey("guest_houses.id"), nullable=False)
    room_number = Column(String(50), nullable=False)
    room_name = Column(String(255), nullable=True)  # Optional friendly name
    capacity = Column(Integer, nullable=False)  # Number of people
    room_type = Column(String(100), nullable=True)  # Single, Double, Shared, etc.
    
    # Room facilities
    facilities = Column(JSON, nullable=True)  # AC, TV, Private bathroom, etc.
    description = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    guest_house = relationship("GuestHouse", back_populates="rooms")
    bookings = relationship("GuestHouseBooking", back_populates="room")

class GuestHouseBooking(BaseModel):
    __tablename__ = "guest_house_bookings"
    
    guest_house_id = Column(Integer, ForeignKey("guest_houses.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("guest_house_rooms.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False)
    
    # Booking details
    check_in_date = Column(DateTime, nullable=False)
    check_out_date = Column(DateTime, nullable=False)
    number_of_guests = Column(Integer, default=1)
    
    # Status tracking
    status = Column(String(50), default="booked")  # booked, checked_in, checked_out, cancelled
    checked_in = Column(Boolean, default=False)
    checked_in_at = Column(DateTime, nullable=True)
    checked_out = Column(Boolean, default=False)
    checked_out_at = Column(DateTime, nullable=True)
    
    # Notes and special requests
    special_requests = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Booking metadata
    booked_by = Column(String(255), nullable=False)
    booking_reference = Column(String(100), nullable=True)
    
    # Relationships
    guest_house = relationship("GuestHouse", back_populates="bookings")
    room = relationship("GuestHouseRoom", back_populates="bookings")
    participant = relationship("EventParticipant")