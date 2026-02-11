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
    TravelRequestTraveler, TravelerType, Dependant, TravelerAcceptanceStatus,
    TravelRequestApproval, ApprovalActionType
)
from app.models.user import User
from app.models.approver import ApprovalWorkflow, ApprovalStep
from app.schemas.travel_request import (
    TravelRequestCreate, TravelRequestUpdate, TravelRequestResponse, TravelRequestDetailResponse,
    TravelRequestListResponse, DestinationCreate, DestinationUpdate, DestinationResponse,
    MessageCreate, MessageResponse, DocumentResponse, ApprovalAction, RejectionAction,
    TravelRequestSummary, TravelerCreate, TravelerResponse, TravelInvitationResponse,
    TravelerAcceptAction, TravelerDeclineAction, ApprovalHistoryResponse
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
    """Get a specific travel request with details.

    Users can view their own requests. Colleagues who are added as travelers
    can also view the request (but cannot modify it).
    """
    travel_request = db.query(TravelRequest).options(
        joinedload(TravelRequest.destinations),
        joinedload(TravelRequest.messages).joinedload(TravelRequestMessage.sender),
        joinedload(TravelRequest.documents),
        joinedload(TravelRequest.travelers),
        joinedload(TravelRequest.approval_history)
    ).filter(
        TravelRequest.id == request_id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    # Check if user is owner or a traveler
    is_owner = travel_request.user_id == current_user.id
    is_traveler = any(
        t.user_id == current_user.id and t.traveler_type == TravelerType.STAFF
        for t in travel_request.travelers
    )

    if not is_owner and not is_traveler:
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

    # Add approver names to approval history
    for approval in travel_request.approval_history:
        if approval.approver:
            approval.approver_name = f"{approval.approver.first_name} {approval.approver.last_name}"

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
    """Update a travel request (draft or rejected requests only).

    Users can edit their draft requests before submission.
    Users can also edit rejected requests to address feedback and resubmit.
    """
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    # Allow editing of DRAFT and REJECTED requests
    if travel_request.status not in [TravelRequestStatus.DRAFT, TravelRequestStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update draft or rejected travel requests"
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
        joinedload(TravelRequest.destinations),
        joinedload(TravelRequest.tenant)
    ).filter(
        TravelRequest.id == request_id,
        TravelRequest.user_id == current_user.id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    # Allow submission from DRAFT or REJECTED status (for resubmission)
    if travel_request.status not in [TravelRequestStatus.DRAFT, TravelRequestStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit draft or rejected travel requests"
        )

    if not travel_request.destinations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please add at least one destination before submitting"
        )

    # Find approval workflow for this tenant
    tenant_slug = travel_request.tenant.slug if travel_request.tenant else None
    workflow = None
    if tenant_slug:
        workflow = db.query(ApprovalWorkflow).filter(
            ApprovalWorkflow.tenant_id == tenant_slug,
            ApprovalWorkflow.workflow_type == "TRAVEL_REQUEST",
            ApprovalWorkflow.is_active == True
        ).first()

    # Set up workflow tracking
    if workflow:
        travel_request.workflow_id = workflow.id
        travel_request.current_approval_step = 1  # Start at step 1

    travel_request.status = TravelRequestStatus.PENDING_APPROVAL
    travel_request.submitted_at = datetime.utcnow()
    # Clear any previous rejection info
    travel_request.rejection_reason = None
    travel_request.rejected_by = None
    travel_request.rejected_at = None

    # Add system message
    is_resubmit = travel_request.status == TravelRequestStatus.REJECTED
    message_content = "Travel request resubmitted for approval." if is_resubmit else "Travel request submitted for approval."
    if workflow:
        message_content += f" Workflow: {workflow.name} ({len(workflow.steps)} approval step(s))."

    system_message = TravelRequestMessage(
        travel_request_id=travel_request.id,
        sender_id=current_user.id,
        sender_type=MessageSenderType.SYSTEM,
        content=message_content
    )
    db.add(system_message)

    db.commit()
    db.refresh(travel_request)

    return travel_request


# ===== Travel Invitations (for colleagues added as travelers) =====

@router.get("/invitations", response_model=List[TravelInvitationResponse])
async def get_travel_invitations(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get travel requests where the current user is added as a traveler (but not the owner).

    This allows colleagues to see travel requests they've been invited to join.
    """
    # Find travel requests where user is a traveler (STAFF type) but not the owner
    travelers = db.query(TravelRequestTraveler).filter(
        TravelRequestTraveler.user_id == current_user.id,
        TravelRequestTraveler.traveler_type == TravelerType.STAFF
    ).all()

    if not travelers:
        return []

    request_ids = [t.travel_request_id for t in travelers]

    query = db.query(TravelRequest).options(
        joinedload(TravelRequest.destinations),
        joinedload(TravelRequest.user)
    ).filter(
        TravelRequest.id.in_(request_ids),
        TravelRequest.user_id != current_user.id  # Exclude requests owned by the user
    )

    # Filter by acceptance status if provided
    if status_filter:
        if status_filter == "pending":
            # Get pending invitations
            pending_traveler_request_ids = [
                t.travel_request_id for t in travelers
                if t.acceptance_status == TravelerAcceptanceStatus.PENDING
            ]
            query = query.filter(TravelRequest.id.in_(pending_traveler_request_ids))
        elif status_filter == "accepted":
            accepted_traveler_request_ids = [
                t.travel_request_id for t in travelers
                if t.acceptance_status == TravelerAcceptanceStatus.ACCEPTED
            ]
            query = query.filter(TravelRequest.id.in_(accepted_traveler_request_ids))

    requests = query.order_by(desc(TravelRequest.created_at)).all()

    # Build response with traveler acceptance info
    traveler_map = {t.travel_request_id: t for t in travelers}
    result = []

    for req in requests:
        traveler = traveler_map.get(req.id)
        if traveler:
            result.append(TravelInvitationResponse(
                id=req.id,
                title=req.title,
                purpose=req.purpose,
                status=req.status,
                created_at=req.created_at,
                submitted_at=req.submitted_at,
                owner_id=req.user_id,
                owner_name=f"{req.user.first_name} {req.user.last_name}" if req.user else "Unknown",
                owner_email=req.user.email if req.user else None,
                traveler_id=traveler.id,
                acceptance_status=traveler.acceptance_status,
                accepted_at=traveler.accepted_at,
                declined_at=traveler.declined_at,
                destinations=[DestinationResponse.from_orm(d) for d in req.destinations]
            ))

    return result


@router.post("/{request_id}/accept", response_model=TravelerResponse)
async def accept_travel_invitation(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept a travel invitation (for colleagues added as travelers)."""
    # Find the traveler entry for this user
    traveler = db.query(TravelRequestTraveler).filter(
        TravelRequestTraveler.travel_request_id == request_id,
        TravelRequestTraveler.user_id == current_user.id,
        TravelRequestTraveler.traveler_type == TravelerType.STAFF
    ).first()

    if not traveler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel invitation not found"
        )

    if traveler.acceptance_status != TravelerAcceptanceStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation already {traveler.acceptance_status.value}"
        )

    # Accept the invitation
    traveler.acceptance_status = TravelerAcceptanceStatus.ACCEPTED
    traveler.accepted_at = datetime.utcnow()

    # Add system message to the request
    travel_request = db.query(TravelRequest).filter(TravelRequest.id == request_id).first()
    if travel_request:
        system_message = TravelRequestMessage(
            travel_request_id=request_id,
            sender_id=current_user.id,
            sender_type=MessageSenderType.SYSTEM,
            content=f"{current_user.first_name} {current_user.last_name} accepted the travel invitation."
        )
        db.add(system_message)

    db.commit()
    db.refresh(traveler)

    return traveler


@router.post("/{request_id}/decline", response_model=TravelerResponse)
async def decline_travel_invitation(
    request_id: int,
    decline_data: TravelerDeclineAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Decline a travel invitation (for colleagues added as travelers)."""
    # Find the traveler entry for this user
    traveler = db.query(TravelRequestTraveler).filter(
        TravelRequestTraveler.travel_request_id == request_id,
        TravelRequestTraveler.user_id == current_user.id,
        TravelRequestTraveler.traveler_type == TravelerType.STAFF
    ).first()

    if not traveler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel invitation not found"
        )

    if traveler.acceptance_status != TravelerAcceptanceStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation already {traveler.acceptance_status.value}"
        )

    # Decline the invitation
    traveler.acceptance_status = TravelerAcceptanceStatus.DECLINED
    traveler.declined_at = datetime.utcnow()
    traveler.decline_reason = decline_data.reason

    # Add system message to the request
    travel_request = db.query(TravelRequest).filter(TravelRequest.id == request_id).first()
    if travel_request:
        decline_msg = f"{current_user.first_name} {current_user.last_name} declined the travel invitation."
        if decline_data.reason:
            decline_msg += f" Reason: {decline_data.reason}"
        system_message = TravelRequestMessage(
            travel_request_id=request_id,
            sender_id=current_user.id,
            sender_type=MessageSenderType.SYSTEM,
            content=decline_msg
        )
        db.add(system_message)

    db.commit()
    db.refresh(traveler)

    return traveler


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

    if travel_request.status not in [TravelRequestStatus.DRAFT, TravelRequestStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add destinations to draft or rejected travel requests"
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
