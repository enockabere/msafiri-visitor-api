"""Pydantic schemas for travel request API."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
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


class TravelerType(str, Enum):
    """Type of traveler."""
    SELF = "self"
    DEPENDANT = "dependant"
    STAFF = "staff"


class TravelerAcceptanceStatus(str, Enum):
    """Acceptance status for colleague travelers."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class ApprovalActionType(str, Enum):
    """Type of approval action."""
    APPROVED = "approved"
    REJECTED = "rejected"


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
    id: int
    travel_request_id: int
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
    id: int
    travel_request_id: int
    sender_id: int
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
    id: int
    travel_request_id: int
    document_type: DocumentType
    file_name: str
    file_url: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_by: int
    uploaded_at: datetime
    uploader_name: Optional[str] = None

    class Config:
        from_attributes = True


# ===== Traveler Schemas =====

class TravelerCreate(BaseModel):
    """Schema for adding a traveler to a request."""
    traveler_type: TravelerType
    user_id: Optional[int] = None  # For SELF or STAFF
    dependant_id: Optional[int] = None  # For DEPENDANT
    traveler_name: str = Field(..., min_length=1, max_length=255)
    traveler_email: Optional[str] = None
    traveler_phone: Optional[str] = None
    is_primary: int = 0
    relation_type: Optional[str] = None  # e.g., "child", "spouse"
    # Passport fields
    passport_file_url: Optional[str] = None
    passport_number: Optional[str] = None
    passport_full_name: Optional[str] = None
    passport_date_of_birth: Optional[date] = None
    passport_expiry_date: Optional[date] = None
    passport_nationality: Optional[str] = None
    passport_gender: Optional[str] = None


class TravelerResponse(BaseModel):
    """Schema for traveler response."""
    id: int
    travel_request_id: int
    traveler_type: TravelerType
    user_id: Optional[int] = None
    dependant_id: Optional[int] = None
    traveler_name: str
    traveler_email: Optional[str] = None
    traveler_phone: Optional[str] = None
    is_primary: int
    created_at: datetime
    # Acceptance tracking for STAFF travelers
    acceptance_status: TravelerAcceptanceStatus = TravelerAcceptanceStatus.PENDING
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    decline_reason: Optional[str] = None
    # Passport data
    passport_file_url: Optional[str] = None
    passport_uploaded_at: Optional[datetime] = None
    passport_number: Optional[str] = None
    passport_full_name: Optional[str] = None
    passport_date_of_birth: Optional[date] = None
    passport_expiry_date: Optional[date] = None
    passport_nationality: Optional[str] = None
    passport_gender: Optional[str] = None
    passport_verified: int = 0
    is_child_under_18: int = 0
    # Relation type for dependants
    relation_type: Optional[str] = None

    class Config:
        from_attributes = True


# ===== Travel Request Schemas =====

class TravelRequestBase(BaseModel):
    """Base schema for travel request."""
    title: str = Field(..., min_length=1, max_length=255)
    purpose: Optional[str] = None


class TravelRequestCreate(TravelRequestBase):
    """Schema for creating a travel request."""
    tenant_id: int
    event_id: Optional[int] = None  # For event-related travel
    visa_assistance_required: bool = False  # User needs help with visa application
    destinations: Optional[List[DestinationCreate]] = None
    travelers: Optional[List[TravelerCreate]] = None
    checklist_data: Optional[List[dict]] = None


class TravelRequestUpdate(BaseModel):
    """Schema for updating a travel request."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    purpose: Optional[str] = None
    visa_assistance_required: Optional[bool] = None


class TravelRequestResponse(TravelRequestBase):
    """Schema for travel request response."""
    id: int
    tenant_id: int
    user_id: int
    status: TravelRequestStatus
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    rejected_by: Optional[int] = None
    rejected_at: Optional[datetime] = None
    user_name: Optional[str] = None
    approver_name: Optional[str] = None
    # Workflow tracking
    workflow_id: Optional[int] = None
    current_approval_step: int = 0
    # Budget fields
    budget_code: Optional[str] = None
    activity_code: Optional[str] = None
    cost_center: Optional[str] = None
    section: Optional[str] = None
    # Event-related travel fields
    event_id: Optional[int] = None
    visa_assistance_required: bool = False

    class Config:
        from_attributes = True


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
    id: int
    title: str
    purpose: Optional[str]
    user_name: str
    user_email: str
    status: TravelRequestStatus
    created_at: datetime
    submitted_at: Optional[datetime]
    destinations: List[DestinationResponse]


# ===== Approval History Schemas =====

class ApprovalHistoryResponse(BaseModel):
    """Schema for approval history entry."""
    id: int
    travel_request_id: int
    step_number: int
    step_name: Optional[str] = None
    approver_id: int
    approver_name: Optional[str] = None
    action: ApprovalActionType
    comments: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Traveler Acceptance Schemas =====

class TravelerAcceptAction(BaseModel):
    """Schema for accepting a travel invitation."""
    pass


class TravelerDeclineAction(BaseModel):
    """Schema for declining a travel invitation."""
    reason: Optional[str] = None


# ===== Travel Invitation Schema =====

class TravelInvitationResponse(BaseModel):
    """Schema for travel invitation (requests where user is a traveler but not owner)."""
    id: int
    title: str
    purpose: Optional[str] = None
    status: TravelRequestStatus
    created_at: datetime
    submitted_at: Optional[datetime] = None
    # Owner info
    owner_id: int
    owner_name: str
    owner_email: Optional[str] = None
    # Traveler's acceptance status
    traveler_id: int
    acceptance_status: TravelerAcceptanceStatus
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    # Destinations for context
    destinations: List[DestinationResponse] = []

    class Config:
        from_attributes = True


class TravelRequestDetailResponse(TravelRequestResponse):
    """Detailed response including destinations, messages, documents, travelers, and approval history."""
    destinations: List[DestinationResponse] = []
    messages: List[MessageResponse] = []
    documents: List[DocumentResponse] = []
    travelers: List[TravelerResponse] = []
    approval_history: List[ApprovalHistoryResponse] = []


# ===== Passport Schemas =====

class PassportSaveRequest(BaseModel):
    """Schema for saving passport data to a traveler."""
    file_url: str
    passport_number: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    expiry_date: Optional[date] = None
    nationality: Optional[str] = None
    gender: Optional[str] = None
    verified: bool = False  # User confirmed the extracted data


class PassportValidationResponse(BaseModel):
    """Schema for passport validation result."""
    can_submit: bool
    missing_child_passports: List[int] = []  # Traveler IDs without passports
    age_warnings: List[str] = []  # Warning messages about age
    age_errors: List[str] = []  # Error messages about age (18+)
    travelers_to_remove: List[int] = []  # Traveler IDs that should be removed (18+)
    error: Optional[str] = None


class TravelerPassportStatus(BaseModel):
    """Schema for individual traveler's passport status."""
    traveler_id: int
    traveler_name: str
    traveler_type: TravelerType
    relation_type: Optional[str] = None
    passport_required: bool
    has_passport: bool
    passport_file_url: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry_date: Optional[date] = None
    is_child_under_18: bool = False
    age_at_travel: Optional[int] = None
