"""Pydantic schemas for travel request API."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from enum import Enum


class TravelRequestStatus(str, Enum):
    """Status options for travel requests."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class TransportMode(str, Enum):
    """Transport mode options."""
    FLIGHT = "flight"
    BUS = "bus"
    TRAIN = "train"
    CAR = "car"
    OTHER = "other"


class MessageSenderType(str, Enum):
    """Sender type for chat messages."""
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class DocumentType(str, Enum):
    """Document type options."""
    TICKET = "ticket"
    ITINERARY = "itinerary"
    BOARDING_PASS = "boarding_pass"
    OTHER = "other"


# ===== Destination Schemas =====

class DestinationBase(BaseModel):
    """Base schema for destination."""
    origin: str = Field(..., min_length=1, max_length=255)
    destination: str = Field(..., min_length=1, max_length=255)
    departure_date: date
    return_date: Optional[date] = None
    transport_mode: TransportMode = TransportMode.FLIGHT
    notes: Optional[str] = None


class DestinationCreate(DestinationBase):
    """Schema for creating a destination."""
    pass


class DestinationUpdate(BaseModel):
    """Schema for updating a destination."""
    origin: Optional[str] = Field(None, min_length=1, max_length=255)
    destination: Optional[str] = Field(None, min_length=1, max_length=255)
    departure_date: Optional[date] = None
    return_date: Optional[date] = None
    transport_mode: Optional[TransportMode] = None
    notes: Optional[str] = None


class DestinationResponse(DestinationBase):
    """Schema for destination response."""
    id: UUID
    travel_request_id: UUID
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Message Schemas =====

class MessageCreate(BaseModel):
    """Schema for creating a message."""
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: UUID
    travel_request_id: UUID
    sender_id: UUID
    sender_type: MessageSenderType
    content: str
    created_at: datetime
    sender_name: Optional[str] = None

    class Config:
        from_attributes = True


# ===== Document Schemas =====

class DocumentCreate(BaseModel):
    """Schema for creating a document."""
    document_type: DocumentType = DocumentType.TICKET
    file_name: str = Field(..., min_length=1, max_length=255)


class DocumentResponse(BaseModel):
    """Schema for document response."""
    id: UUID
    travel_request_id: UUID
    document_type: DocumentType
    file_name: str
    file_url: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_by: UUID
    uploaded_at: datetime
    uploader_name: Optional[str] = None

    class Config:
        from_attributes = True


# ===== Travel Request Schemas =====

class TravelRequestBase(BaseModel):
    """Base schema for travel request."""
    title: str = Field(..., min_length=1, max_length=255)
    purpose: Optional[str] = None


class TravelRequestCreate(TravelRequestBase):
    """Schema for creating a travel request."""
    tenant_id: UUID
    destinations: Optional[List[DestinationCreate]] = None


class TravelRequestUpdate(BaseModel):
    """Schema for updating a travel request."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    purpose: Optional[str] = None


class TravelRequestResponse(TravelRequestBase):
    """Schema for travel request response."""
    id: UUID
    tenant_id: UUID
    user_id: UUID
    status: TravelRequestStatus
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    rejected_by: Optional[UUID] = None
    rejected_at: Optional[datetime] = None
    user_name: Optional[str] = None
    approver_name: Optional[str] = None

    class Config:
        from_attributes = True


class TravelRequestDetailResponse(TravelRequestResponse):
    """Detailed response including destinations, messages, and documents."""
    destinations: List[DestinationResponse] = []
    messages: List[MessageResponse] = []
    documents: List[DocumentResponse] = []


class TravelRequestListResponse(BaseModel):
    """Response for listing travel requests."""
    items: List[TravelRequestResponse]
    total: int
    page: int
    page_size: int


# ===== Admin Action Schemas =====

class ApprovalAction(BaseModel):
    """Schema for approval action."""
    pass


class RejectionAction(BaseModel):
    """Schema for rejection action."""
    reason: str = Field(..., min_length=1)


class TravelRequestSummary(BaseModel):
    """Summary for booking purposes."""
    id: UUID
    title: str
    purpose: Optional[str]
    user_name: str
    user_email: str
    status: TravelRequestStatus
    created_at: datetime
    submitted_at: Optional[datetime]
    destinations: List[DestinationResponse]
