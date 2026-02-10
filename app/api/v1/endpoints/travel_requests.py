"""Travel request API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
import logging
import os

from app.db.database import get_db
from app.models.travel_request import (
    TravelRequest, TravelRequestDestination, TravelRequestMessage, TravelRequestDocument,
    TravelRequestStatus, TransportMode, MessageSenderType, DocumentType,
    TravelRequestTraveler, TravelerType, Dependant
)
from app.models.user import User
from app.schemas.travel_request import (
    TravelRequestCreate, TravelRequestUpdate, TravelRequestResponse, TravelRequestDetailResponse,
    TravelRequestListResponse, DestinationCreate, DestinationUpdate, DestinationResponse,
    MessageCreate, MessageResponse, DocumentResponse, ApprovalAction, RejectionAction,
    TravelRequestSummary, TravelerCreate, TravelerResponse
)
from app.api.deps import get_current_user

# Azure Blob Storage
try:
    from azure.storage.blob import BlobServiceClient
    azure_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    azure_container_name = os.getenv("AZURE_STORAGE_CONTAINER", "travel-tickets")
    if azure_connection_string:
        blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)
        azure_available = True
    else:
        blob_service_client = None
        azure_available = False
except Exception as e:
    blob_service_client = None
    azure_available = False

router = APIRouter()
logger = logging.getLogger(__name__)


# ===== User Travel Request Endpoints =====

@router.get("/", response_model=List[TravelRequestResponse])
async def get_user_travel_requests(
    tenant_id: Optional[int] = None,
    status_filter: Optional[TravelRequestStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all travel requests for the current user."""
    query = db.query(TravelRequest).filter(TravelRequest.user_id == current_user.id)

    if tenant_id:
        query = query.filter(TravelRequest.tenant_id == tenant_id)

    if status_filter:
        query = query.filter(TravelRequest.status == status_filter)

    requests = query.order_by(desc(TravelRequest.created_at)).all()

    # Add user names
    for req in requests:
        req.user_name = f"{req.user.first_name} {req.user.last_name}" if req.user else None
        if req.approver:
            req.approver_name = f"{req.approver.first_name} {req.approver.last_name}"

    return requests


@router.post("/", response_model=TravelRequestResponse)
async def create_travel_request(
    request_data: TravelRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new travel request."""
    travel_request = TravelRequest(
        tenant_id=request_data.tenant_id,
        user_id=current_user.id,
        title=request_data.title,
        purpose=request_data.purpose,
        status=TravelRequestStatus.DRAFT
    )

    db.add(travel_request)
    db.flush()

    # Add destinations if provided
    if request_data.destinations:
        for idx, dest_data in enumerate(request_data.destinations):
            destination = TravelRequestDestination(
                travel_request_id=travel_request.id,
                origin=dest_data.origin,
                destination=dest_data.destination,
                departure_date=dest_data.departure_date,
                return_date=dest_data.return_date,
                transport_mode=dest_data.transport_mode,
                notes=dest_data.notes,
                order=idx
            )
            db.add(destination)

    # Add travelers if provided
    if request_data.travelers:
        for traveler_data in request_data.travelers:
            traveler = TravelRequestTraveler(
                travel_request_id=travel_request.id,
                traveler_type=traveler_data.traveler_type,
                user_id=traveler_data.user_id,
                dependant_id=traveler_data.dependant_id,
                traveler_name=traveler_data.traveler_name,
                traveler_email=traveler_data.traveler_email,
                traveler_phone=traveler_data.traveler_phone,
                is_primary=traveler_data.is_primary
            )
            db.add(traveler)
    else:
        # Add the current user as the primary traveler by default
        traveler = TravelRequestTraveler(
            travel_request_id=travel_request.id,
            traveler_type=TravelerType.SELF,
            user_id=current_user.id,
            traveler_name=f"{current_user.first_name} {current_user.last_name}",
            traveler_email=current_user.email,
            traveler_phone=current_user.phone_number,
            is_primary=1
        )
        db.add(traveler)

    # Add system message
    system_message = TravelRequestMessage(
        travel_request_id=travel_request.id,
        sender_id=current_user.id,
        sender_type=MessageSenderType.SYSTEM,
        content="Travel request created. Add your destinations and submit for approval."
    )
    db.add(system_message)

    db.commit()
    db.refresh(travel_request)

    travel_request.user_name = f"{current_user.first_name} {current_user.last_name}"

    return travel_request


@router.get("/{request_id}", response_model=TravelRequestDetailResponse)
async def get_travel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific travel request with details."""
    travel_request = db.query(TravelRequest).options(
        joinedload(TravelRequest.destinations),
        joinedload(TravelRequest.messages).joinedload(TravelRequestMessage.sender),
        joinedload(TravelRequest.documents),
        joinedload(TravelRequest.travelers)
    ).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    # Add user names to messages
    for msg in travel_request.messages:
        if msg.sender:
            msg.sender_name = f"{msg.sender.first_name} {msg.sender.last_name}"

    # Add uploader names to documents
    for doc in travel_request.documents:
        if doc.uploader:
            doc.uploader_name = f"{doc.uploader.first_name} {doc.uploader.last_name}"

    travel_request.user_name = f"{travel_request.user.first_name} {travel_request.user.last_name}"
    if travel_request.approver:
        travel_request.approver_name = f"{travel_request.approver.first_name} {travel_request.approver.last_name}"

    return travel_request


@router.put("/{request_id}", response_model=TravelRequestResponse)
async def update_travel_request(
    request_id: int,
    request_data: TravelRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a travel request (only draft requests)."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if travel_request.status != TravelRequestStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update draft travel requests"
        )

    for field, value in request_data.dict(exclude_unset=True).items():
        setattr(travel_request, field, value)

    db.commit()
    db.refresh(travel_request)

    return travel_request


@router.delete("/{request_id}")
async def delete_travel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a draft travel request."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if travel_request.status != TravelRequestStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete draft travel requests"
        )

    db.delete(travel_request)
    db.commit()

    return {"message": "Travel request deleted successfully"}


@router.post("/{request_id}/submit", response_model=TravelRequestResponse)
async def submit_travel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a travel request for approval."""
    travel_request = db.query(TravelRequest).options(
        joinedload(TravelRequest.destinations)
    ).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if travel_request.status != TravelRequestStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit draft travel requests"
        )

    if not travel_request.destinations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please add at least one destination before submitting"
        )

    travel_request.status = TravelRequestStatus.PENDING_APPROVAL
    travel_request.submitted_at = datetime.utcnow()

    # Add system message
    system_message = TravelRequestMessage(
        travel_request_id=travel_request.id,
        sender_id=current_user.id,
        sender_type=MessageSenderType.SYSTEM,
        content="Travel request submitted for approval."
    )
    db.add(system_message)

    db.commit()
    db.refresh(travel_request)

    return travel_request


# ===== Destination Endpoints =====

@router.post("/{request_id}/destinations", response_model=DestinationResponse)
async def add_destination(
    request_id: int,
    dest_data: DestinationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a destination to a travel request."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if travel_request.status != TravelRequestStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add destinations to draft travel requests"
        )

    # Get the next order number
    max_order = db.query(TravelRequestDestination).filter(
        TravelRequestDestination.travel_request_id == request_id
    ).count()

    destination = TravelRequestDestination(
        travel_request_id=request_id,
        origin=dest_data.origin,
        destination=dest_data.destination,
        departure_date=dest_data.departure_date,
        return_date=dest_data.return_date,
        transport_mode=dest_data.transport_mode,
        notes=dest_data.notes,
        order=max_order
    )

    db.add(destination)
    db.commit()
    db.refresh(destination)

    return destination


@router.put("/{request_id}/destinations/{dest_id}", response_model=DestinationResponse)
async def update_destination(
    request_id: int,
    dest_id: int,
    dest_data: DestinationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a destination."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if travel_request.status != TravelRequestStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update destinations in draft travel requests"
        )

    destination = db.query(TravelRequestDestination).filter(
        TravelRequestDestination.id == dest_id,
        TravelRequestDestination.travel_request_id == request_id
    ).first()

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found"
        )

    for field, value in dest_data.dict(exclude_unset=True).items():
        setattr(destination, field, value)

    db.commit()
    db.refresh(destination)

    return destination


@router.delete("/{request_id}/destinations/{dest_id}")
async def delete_destination(
    request_id: int,
    dest_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a destination."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if travel_request.status != TravelRequestStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete destinations from draft travel requests"
        )

    destination = db.query(TravelRequestDestination).filter(
        TravelRequestDestination.id == dest_id,
        TravelRequestDestination.travel_request_id == request_id
    ).first()

    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found"
        )

    db.delete(destination)
    db.commit()

    return {"message": "Destination deleted successfully"}


# ===== Message Endpoints =====

@router.get("/{request_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat messages for a travel request."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    messages = db.query(TravelRequestMessage).options(
        joinedload(TravelRequestMessage.sender)
    ).filter(
        TravelRequestMessage.travel_request_id == request_id
    ).order_by(TravelRequestMessage.created_at).all()

    for msg in messages:
        if msg.sender:
            msg.sender_name = f"{msg.sender.first_name} {msg.sender.last_name}"

    return messages


@router.post("/{request_id}/messages", response_model=MessageResponse)
async def send_message(
    request_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a chat message for a travel request."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    message = TravelRequestMessage(
        travel_request_id=request_id,
        sender_id=current_user.id,
        sender_type=MessageSenderType.USER,
        content=message_data.content
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    message.sender_name = f"{current_user.first_name} {current_user.last_name}"

    return message


# ===== Document Endpoints =====

@router.get("/{request_id}/documents", response_model=List[DocumentResponse])
async def get_documents(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get documents for a travel request."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    documents = db.query(TravelRequestDocument).options(
        joinedload(TravelRequestDocument.uploader)
    ).filter(
        TravelRequestDocument.travel_request_id == request_id
    ).order_by(TravelRequestDocument.uploaded_at.desc()).all()

    for doc in documents:
        if doc.uploader:
            doc.uploader_name = f"{doc.uploader.first_name} {doc.uploader.last_name}"

    return documents
