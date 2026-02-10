"""Admin travel request API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from uuid import UUID
import logging
import os
import io

from app.db.database import get_db
from app.models.travel_request import (
    TravelRequest, TravelRequestDestination, TravelRequestMessage, TravelRequestDocument,
    TravelRequestStatus, MessageSenderType, DocumentType, TravelRequestTraveler
)
from app.models.user import User
from app.schemas.travel_request import (
    TravelRequestResponse, TravelRequestDetailResponse, TravelRequestListResponse,
    MessageCreate, MessageResponse, DocumentResponse, ApprovalAction, RejectionAction,
    TravelRequestSummary, DestinationResponse
)
from app.api.deps import get_current_user

# Azure Blob Storage
try:
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
    from datetime import timedelta
    azure_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    azure_container_name = os.getenv("AZURE_TRAVEL_TICKETS_CONTAINER", "travel-tickets")
    azure_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    azure_account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
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


def check_admin_access(current_user: User, tenant_id: UUID):
    """Check if user has admin access to the tenant."""
    # Check if user has admin role for this tenant
    for user_tenant in current_user.user_tenants:
        if str(user_tenant.tenant_id) == str(tenant_id):
            if user_tenant.role in ['admin', 'super_admin', 'owner']:
                return True
    return False


@router.get("/", response_model=List[TravelRequestResponse])
async def get_all_travel_requests(
    tenant_id: UUID,
    status_filter: Optional[TravelRequestStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all travel requests for a tenant (admin only)."""
    if not check_admin_access(current_user, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    query = db.query(TravelRequest).filter(TravelRequest.tenant_id == tenant_id)

    if status_filter:
        query = query.filter(TravelRequest.status == status_filter)

    total = query.count()
    requests = query.order_by(desc(TravelRequest.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # Add user names
    for req in requests:
        req.user_name = f"{req.user.first_name} {req.user.last_name}" if req.user else None
        if req.approver:
            req.approver_name = f"{req.approver.first_name} {req.approver.last_name}"

    return requests


@router.get("/pending", response_model=List[TravelRequestResponse])
async def get_pending_travel_requests(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pending travel requests for a tenant (admin only)."""
    if not check_admin_access(current_user, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    requests = db.query(TravelRequest).filter(
        TravelRequest.tenant_id == tenant_id,
        TravelRequest.status == TravelRequestStatus.PENDING_APPROVAL
    ).order_by(TravelRequest.submitted_at).all()

    for req in requests:
        req.user_name = f"{req.user.first_name} {req.user.last_name}" if req.user else None

    return requests


@router.get("/{request_id}", response_model=TravelRequestDetailResponse)
async def get_travel_request_admin(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific travel request (admin view)."""
    travel_request = db.query(TravelRequest).options(
        joinedload(TravelRequest.destinations),
        joinedload(TravelRequest.messages).joinedload(TravelRequestMessage.sender),
        joinedload(TravelRequest.documents).joinedload(TravelRequestDocument.uploader),
        joinedload(TravelRequest.travelers)
    ).filter(TravelRequest.id == request_id).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if not check_admin_access(current_user, travel_request.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Add names
    for msg in travel_request.messages:
        if msg.sender:
            msg.sender_name = f"{msg.sender.first_name} {msg.sender.last_name}"

    for doc in travel_request.documents:
        if doc.uploader:
            doc.uploader_name = f"{doc.uploader.first_name} {doc.uploader.last_name}"

    travel_request.user_name = f"{travel_request.user.first_name} {travel_request.user.last_name}"
    if travel_request.approver:
        travel_request.approver_name = f"{travel_request.approver.first_name} {travel_request.approver.last_name}"

    return travel_request


@router.post("/{request_id}/approve", response_model=TravelRequestResponse)
async def approve_travel_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a travel request."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if not check_admin_access(current_user, travel_request.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    if travel_request.status != TravelRequestStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only approve pending travel requests"
        )

    travel_request.status = TravelRequestStatus.APPROVED
    travel_request.approved_by = current_user.id
    travel_request.approved_at = datetime.utcnow()

    # Add system message
    system_message = TravelRequestMessage(
        travel_request_id=travel_request.id,
        sender_id=current_user.id,
        sender_type=MessageSenderType.SYSTEM,
        content=f"Travel request approved by {current_user.first_name} {current_user.last_name}."
    )
    db.add(system_message)

    db.commit()
    db.refresh(travel_request)

    return travel_request


@router.post("/{request_id}/reject", response_model=TravelRequestResponse)
async def reject_travel_request(
    request_id: UUID,
    rejection: RejectionAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a travel request."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if not check_admin_access(current_user, travel_request.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    if travel_request.status != TravelRequestStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only reject pending travel requests"
        )

    travel_request.status = TravelRequestStatus.REJECTED
    travel_request.rejected_by = current_user.id
    travel_request.rejected_at = datetime.utcnow()
    travel_request.rejection_reason = rejection.reason

    # Add system message
    system_message = TravelRequestMessage(
        travel_request_id=travel_request.id,
        sender_id=current_user.id,
        sender_type=MessageSenderType.SYSTEM,
        content=f"Travel request rejected by {current_user.first_name} {current_user.last_name}. Reason: {rejection.reason}"
    )
    db.add(system_message)

    db.commit()
    db.refresh(travel_request)

    return travel_request


@router.post("/{request_id}/messages", response_model=MessageResponse)
async def send_admin_message(
    request_id: UUID,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message as admin on a travel request."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if not check_admin_access(current_user, travel_request.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    message = TravelRequestMessage(
        travel_request_id=request_id,
        sender_id=current_user.id,
        sender_type=MessageSenderType.ADMIN,
        content=message_data.content
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    message.sender_name = f"{current_user.first_name} {current_user.last_name}"

    return message


@router.post("/{request_id}/upload-ticket", response_model=DocumentResponse)
async def upload_ticket(
    request_id: UUID,
    file: UploadFile = File(...),
    document_type: DocumentType = DocumentType.TICKET,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a ticket document for a travel request."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if not check_admin_access(current_user, travel_request.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    if travel_request.status != TravelRequestStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only upload tickets for approved travel requests"
        )

    if not azure_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage service not available"
        )

    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Generate unique blob name
        blob_name = f"{travel_request.tenant_id}/{request_id}/{datetime.utcnow().timestamp()}_{file.filename}"

        # Upload to Azure
        container_client = blob_service_client.get_container_client(azure_container_name)

        # Create container if it doesn't exist
        try:
            container_client.create_container()
        except Exception:
            pass  # Container already exists

        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(file_content, overwrite=True)

        # Generate SAS URL for access
        if azure_account_name and azure_account_key:
            sas_token = generate_blob_sas(
                account_name=azure_account_name,
                container_name=azure_container_name,
                blob_name=blob_name,
                account_key=azure_account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(days=365)
            )
            file_url = f"https://{azure_account_name}.blob.core.windows.net/{azure_container_name}/{blob_name}?{sas_token}"
        else:
            file_url = blob_client.url

        # Create document record
        document = TravelRequestDocument(
            travel_request_id=request_id,
            document_type=document_type,
            file_name=file.filename,
            file_url=file_url,
            file_size=file_size,
            mime_type=file.content_type,
            uploaded_by=current_user.id
        )

        db.add(document)

        # Add system message
        system_message = TravelRequestMessage(
            travel_request_id=request_id,
            sender_id=current_user.id,
            sender_type=MessageSenderType.SYSTEM,
            content=f"Ticket uploaded: {file.filename}"
        )
        db.add(system_message)

        db.commit()
        db.refresh(document)

        document.uploader_name = f"{current_user.first_name} {current_user.last_name}"

        return document

    except Exception as e:
        logger.error(f"Failed to upload ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload ticket: {str(e)}"
        )


@router.get("/{request_id}/summary")
async def download_booking_summary(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download a booking summary for a travel request."""
    travel_request = db.query(TravelRequest).options(
        joinedload(TravelRequest.destinations),
        joinedload(TravelRequest.user),
        joinedload(TravelRequest.travelers)
    ).filter(TravelRequest.id == request_id).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if not check_admin_access(current_user, travel_request.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Generate CSV summary
    user = travel_request.user
    csv_content = io.StringIO()
    csv_content.write("TRAVEL REQUEST BOOKING SUMMARY\n")
    csv_content.write("=" * 50 + "\n\n")
    csv_content.write(f"Request ID: {travel_request.id}\n")
    csv_content.write(f"Title: {travel_request.title}\n")
    csv_content.write(f"Purpose: {travel_request.purpose or 'N/A'}\n")
    csv_content.write(f"Status: {travel_request.status.value}\n\n")

    csv_content.write("REQUESTER INFORMATION\n")
    csv_content.write("-" * 30 + "\n")
    csv_content.write(f"Name: {user.first_name} {user.last_name}\n")
    csv_content.write(f"Email: {user.email}\n")
    csv_content.write(f"Phone: {user.phone_number or 'N/A'}\n\n")

    csv_content.write("TRAVELERS\n")
    csv_content.write("-" * 30 + "\n")
    if travel_request.travelers:
        for idx, traveler in enumerate(travel_request.travelers, 1):
            primary_label = " (Primary)" if traveler.is_primary else ""
            csv_content.write(f"\n{idx}. {traveler.traveler_name}{primary_label}\n")
            csv_content.write(f"   Type: {traveler.traveler_type.value}\n")
            if traveler.traveler_email:
                csv_content.write(f"   Email: {traveler.traveler_email}\n")
            if traveler.traveler_phone:
                csv_content.write(f"   Phone: {traveler.traveler_phone}\n")
    else:
        csv_content.write(f"Name: {user.first_name} {user.last_name}\n")
        csv_content.write(f"Email: {user.email}\n")

    csv_content.write("\n\nDESTINATIONS\n")
    csv_content.write("-" * 30 + "\n")
    for idx, dest in enumerate(travel_request.destinations, 1):
        csv_content.write(f"\nLeg {idx}:\n")
        csv_content.write(f"  From: {dest.origin}\n")
        csv_content.write(f"  To: {dest.destination}\n")
        csv_content.write(f"  Departure: {dest.departure_date}\n")
        csv_content.write(f"  Return: {dest.return_date or 'N/A'}\n")
        csv_content.write(f"  Transport: {dest.transport_mode.value}\n")
        if dest.notes:
            csv_content.write(f"  Notes: {dest.notes}\n")

    csv_content.write("\n" + "=" * 50 + "\n")
    csv_content.write(f"Generated: {datetime.utcnow().isoformat()}\n")

    # Return as downloadable file
    output = io.BytesIO(csv_content.getvalue().encode('utf-8'))
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=travel_request_{request_id}_summary.txt"
        }
    )


@router.post("/{request_id}/complete", response_model=TravelRequestResponse)
async def complete_travel_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a travel request as completed (after travel is done)."""
    travel_request = db.query(TravelRequest).filter(
        TravelRequest.id == request_id
    ).first()

    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Travel request not found"
        )

    if not check_admin_access(current_user, travel_request.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    if travel_request.status != TravelRequestStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only complete approved travel requests"
        )

    travel_request.status = TravelRequestStatus.COMPLETED

    # Add system message
    system_message = TravelRequestMessage(
        travel_request_id=travel_request.id,
        sender_id=current_user.id,
        sender_type=MessageSenderType.SYSTEM,
        content="Travel request marked as completed."
    )
    db.add(system_message)

    db.commit()
    db.refresh(travel_request)

    return travel_request
