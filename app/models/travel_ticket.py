from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class ParticipantTicket(BaseModel):
    __tablename__ = "participant_tickets"
    
    participant_id = Column(Integer, ForeignKey("event_participants.id"), nullable=False, unique=True)
    departure_date = Column(Date, nullable=False)
    arrival_date = Column(Date, nullable=False)
    departure_airport = Column(String(100), nullable=False)
    arrival_airport = Column(String(100), nullable=False)
    flight_number = Column(String(50))
    airline = Column(String(100))
    ticket_reference = Column(String(100))
    notes = Column(Text)
    
    # Relationships
    participant = relationship("EventParticipant", back_populates="ticket")