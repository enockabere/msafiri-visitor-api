"""Travel request models for managing travel booking requests."""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Date, Enum
from sqlalchemy.orm import relationship

from app.db.database import Base


class TravelRequestStatus(str, PyEnum):
    """Status options for travel requests."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class TransportMode(str, PyEnum):
    """Transport mode options."""
    FLIGHT = "flight"
    BUS = "bus"
    TRAIN = "train"
    CAR = "car"
    OTHER = "other"


class MessageSenderType(str, PyEnum):
    """Sender type for chat messages."""
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class DocumentType(str, PyEnum):
    """Document type options."""
    TICKET = "ticket"
    ITINERARY = "itinerary"
    BOARDING_PASS = "boarding_pass"
    OTHER = "other"


class DependantRelationship(str, PyEnum):
    """Relationship types for dependants."""
    SPOUSE = "spouse"
    CHILD = "child"
    PARENT = "parent"
    SIBLING = "sibling"
    OTHER = "other"


class TravelerType(str, PyEnum):
    """Type of traveler in a travel request."""
    SELF = "self"  # The user making the request
    DEPENDANT = "dependant"  # User's dependant
    STAFF = "staff"  # Staff member from same tenant


class TravelRequest(Base):
    """Travel request model."""
    __tablename__ = "travel_requests"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    purpose = Column(Text, nullable=True)
    status = Column(
        Enum(TravelRequestStatus),
        default=TravelRequestStatus.DRAFT,
        nullable=False,
        index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    user = relationship("User", foreign_keys=[user_id], backref="travel_requests")
    approver = relationship("User", foreign_keys=[approved_by])
    rejector = relationship("User", foreign_keys=[rejected_by])
    destinations = relationship("TravelRequestDestination", back_populates="travel_request", cascade="all, delete-orphan", order_by="TravelRequestDestination.order")
    messages = relationship("TravelRequestMessage", back_populates="travel_request", cascade="all, delete-orphan", order_by="TravelRequestMessage.created_at")
    documents = relationship("TravelRequestDocument", back_populates="travel_request", cascade="all, delete-orphan")
    travelers = relationship("TravelRequestTraveler", back_populates="travel_request", cascade="all, delete-orphan")


class TravelRequestDestination(Base):
    """Destination leg for a travel request."""
    __tablename__ = "travel_request_destinations"

    id = Column(Integer, primary_key=True, index=True)
    travel_request_id = Column(Integer, ForeignKey("travel_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    origin = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    departure_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    transport_mode = Column(Enum(TransportMode), default=TransportMode.FLIGHT, nullable=False)
    notes = Column(Text, nullable=True)
    order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    travel_request = relationship("TravelRequest", back_populates="destinations")


class TravelRequestMessage(Base):
    """Chat message for a travel request."""
    __tablename__ = "travel_request_messages"

    id = Column(Integer, primary_key=True, index=True)
    travel_request_id = Column(Integer, ForeignKey("travel_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_type = Column(Enum(MessageSenderType), default=MessageSenderType.USER, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    travel_request = relationship("TravelRequest", back_populates="messages")
    sender = relationship("User")


class TravelRequestDocument(Base):
    """Document/ticket attached to a travel request."""
    __tablename__ = "travel_request_documents"

    id = Column(Integer, primary_key=True, index=True)
    travel_request_id = Column(Integer, ForeignKey("travel_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(Enum(DocumentType), default=DocumentType.TICKET, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(1024), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    travel_request = relationship("TravelRequest", back_populates="documents")
    uploader = relationship("User")


class Dependant(Base):
    """User's dependant (family member) who can travel with them."""
    __tablename__ = "dependants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    relation_type = Column(Enum(DependantRelationship, values_callable=lambda x: [e.value for e in x]), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    passport_number = Column(String(50), nullable=True)
    passport_expiry = Column(Date, nullable=True)
    nationality = Column(String(100), nullable=True)
    phone_number = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="dependants")


class TravelRequestTraveler(Base):
    """Traveler in a travel request - can be self, dependant, or staff member."""
    __tablename__ = "travel_request_travelers"

    id = Column(Integer, primary_key=True, index=True)
    travel_request_id = Column(Integer, ForeignKey("travel_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    traveler_type = Column(Enum(TravelerType), nullable=False)
    # For SELF or STAFF type - reference to users table
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # For DEPENDANT type - reference to dependants table
    dependant_id = Column(Integer, ForeignKey("dependants.id"), nullable=True)
    # Denormalized fields for quick access
    traveler_name = Column(String(255), nullable=False)
    traveler_email = Column(String(255), nullable=True)
    traveler_phone = Column(String(50), nullable=True)
    is_primary = Column(Integer, default=0, nullable=False)  # 1 if this is the main traveler
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    travel_request = relationship("TravelRequest", back_populates="travelers")
    user = relationship("User", foreign_keys=[user_id])
    dependant = relationship("Dependant")
