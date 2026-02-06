"""Vetting Chat API endpoints for committee discussions."""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.chat import ChatRoom, ChatMessage, ChatType, VettingChatRoom, VettingChatMember
from app.models.vetting_committee import VettingCommittee, VettingStatus

router = APIRouter()


# Schemas
class VettingChatMessageCreate(BaseModel):
    message: Optional[str] = None
    file_url: Optional[str] = None
    file_type: Optional[str] = None  # 'image', 'document', 'voice', 'video'
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None  # For voice/video in seconds
    reply_to_message_id: Optional[int] = None


class VettingChatMessageResponse(BaseModel):
    id: int
    chat_room_id: int
    sender_email: str
    sender_name: str
    message: Optional[str]
    file_url: Optional[str]
    file_type: Optional[str]
    file_name: Optional[str]
    file_size: Optional[int]
    duration: Optional[int]
    reply_to_message_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class VettingChatStatusResponse(BaseModel):
    chat_room_id: int
    event_id: int
    event_title: str
    is_locked: bool
    locked_reason: Optional[str]
    can_send_messages: bool
    days_until_deletion: Optional[int]
    scheduled_deletion_date: Optional[str]
    committee_status: str
    members: List[dict]


def get_vetting_chat_for_event(db: Session, event_id: int) -> Optional[VettingChatRoom]:
    """Get the vetting chat room for an event."""
    return db.query(VettingChatRoom).filter(
        VettingChatRoom.event_id == event_id
    ).first()


def check_user_can_chat(
    db: Session,
    vetting_chat: VettingChatRoom,
    user_email: str
) -> tuple[bool, str]:
    """Check if user can send messages in the vetting chat."""
    # Check if chat is locked
    if vetting_chat.is_locked:
        return False, vetting_chat.locked_reason or "Chat is locked"

    # Check if user is a member
    member = db.query(VettingChatMember).filter(
        VettingChatMember.vetting_chat_id == vetting_chat.id,
        VettingChatMember.user_email.ilike(user_email)
    ).first()

    if not member:
        return False, "User is not a member of this chat"

    if not member.can_send_messages:
        return False, member.muted_reason or "You cannot send messages"

    return True, ""


@router.get("/events/{event_id}/vetting-chat/status", response_model=VettingChatStatusResponse)
def get_vetting_chat_status(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the status of the vetting chat for an event."""
    from app.models.event import Event

    vetting_chat = get_vetting_chat_for_event(db, event_id)
    if not vetting_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting chat not found for this event"
        )

    # Verify user has access
    member = db.query(VettingChatMember).filter(
        VettingChatMember.vetting_chat_id == vetting_chat.id,
        VettingChatMember.user_email.ilike(current_user.email)
    ).first()

    is_admin = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.EVENT_ADMIN]

    if not member and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this vetting chat"
        )

    # Get event details
    event = db.query(Event).filter(Event.id == event_id).first()

    # Calculate days until deletion
    days_until_deletion = None
    if vetting_chat.scheduled_deletion_date:
        today = datetime.utcnow().date()
        delta = vetting_chat.scheduled_deletion_date - today
        days_until_deletion = max(0, delta.days)

    # Get committee status
    committee = db.query(VettingCommittee).filter(
        VettingCommittee.id == vetting_chat.vetting_committee_id
    ).first()

    # Get all members
    members = db.query(VettingChatMember).filter(
        VettingChatMember.vetting_chat_id == vetting_chat.id
    ).all()

    can_send, _ = check_user_can_chat(db, vetting_chat, current_user.email)

    return {
        "chat_room_id": vetting_chat.chat_room_id,
        "event_id": event_id,
        "event_title": event.title if event else "Unknown Event",
        "is_locked": vetting_chat.is_locked,
        "locked_reason": vetting_chat.locked_reason,
        "can_send_messages": can_send,
        "days_until_deletion": days_until_deletion,
        "scheduled_deletion_date": vetting_chat.scheduled_deletion_date.isoformat() if vetting_chat.scheduled_deletion_date else None,
        "committee_status": committee.status.value if committee else "unknown",
        "members": [
            {
                "email": m.user_email,
                "name": m.user_name,
                "role": m.role,
                "can_send_messages": m.can_send_messages
            }
            for m in members
        ]
    }


@router.get("/events/{event_id}/vetting-chat/messages", response_model=List[VettingChatMessageResponse])
def get_vetting_chat_messages(
    event_id: int,
    limit: int = 50,
    before_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages from the vetting chat."""
    vetting_chat = get_vetting_chat_for_event(db, event_id)
    if not vetting_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting chat not found for this event"
        )

    # Verify user has access
    member = db.query(VettingChatMember).filter(
        VettingChatMember.vetting_chat_id == vetting_chat.id,
        VettingChatMember.user_email.ilike(current_user.email)
    ).first()

    is_admin = current_user.role in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.EVENT_ADMIN]

    if not member and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this vetting chat"
        )

    # Query messages
    query = db.query(ChatMessage).filter(
        ChatMessage.chat_room_id == vetting_chat.chat_room_id
    )

    if before_id:
        query = query.filter(ChatMessage.id < before_id)

    messages = query.order_by(ChatMessage.created_at.desc()).limit(limit).all()

    # Return in chronological order
    return list(reversed(messages))


@router.post("/events/{event_id}/vetting-chat/messages", response_model=VettingChatMessageResponse)
def send_vetting_chat_message(
    event_id: int,
    message_data: VettingChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to the vetting chat."""
    vetting_chat = get_vetting_chat_for_event(db, event_id)
    if not vetting_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting chat not found for this event"
        )

    # Check if user can send messages
    can_send, reason = check_user_can_chat(db, vetting_chat, current_user.email)
    if not can_send:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Validate message content
    if not message_data.message and not message_data.file_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message must contain text or a file"
        )

    # Get member info for sender name
    member = db.query(VettingChatMember).filter(
        VettingChatMember.vetting_chat_id == vetting_chat.id,
        VettingChatMember.user_email.ilike(current_user.email)
    ).first()

    # Create message
    new_message = ChatMessage(
        chat_room_id=vetting_chat.chat_room_id,
        sender_email=current_user.email,
        sender_name=member.user_name if member else current_user.full_name or current_user.email,
        message=message_data.message,
        file_url=message_data.file_url,
        file_type=message_data.file_type,
        file_name=message_data.file_name,
        file_size=message_data.file_size,
        duration=message_data.duration,
        reply_to_message_id=message_data.reply_to_message_id,
        is_admin_message=False
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return new_message


@router.post("/events/{event_id}/vetting-chat/upload")
async def upload_vetting_chat_file(
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a file (document, voice note, image) to Azure storage for vetting chat."""
    from azure.storage.blob import BlobServiceClient
    import os
    import uuid

    vetting_chat = get_vetting_chat_for_event(db, event_id)
    if not vetting_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vetting chat not found for this event"
        )

    # Check if user can send messages
    can_send, reason = check_user_can_chat(db, vetting_chat, current_user.email)
    if not can_send:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Determine file type
    content_type = file.content_type or ""
    if content_type.startswith("image/"):
        file_type = "image"
        subfolder = "images"
    elif content_type.startswith("audio/") or file.filename.endswith(('.mp3', '.wav', '.ogg', '.m4a', '.webm')):
        file_type = "voice"
        subfolder = "voice-notes"
    elif content_type.startswith("video/"):
        file_type = "video"
        subfolder = "videos"
    else:
        file_type = "document"
        subfolder = "documents"

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Size limits
    max_size = 15 * 1024 * 1024  # 15MB for most files
    if file_type == "voice":
        max_size = 5 * 1024 * 1024  # 5MB for voice notes

    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {max_size // (1024 * 1024)}MB"
        )

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    blob_path = f"msafiri-documents/vetting-chat/{event_id}/{subfolder}/{unique_filename}"

    try:
        # Upload to Azure Blob Storage
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "uploads")

        if not connection_string:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Azure storage not configured"
            )

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)

        # Create container if it doesn't exist
        try:
            container_client.create_container()
        except Exception:
            pass  # Container already exists

        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(file_content, overwrite=True, content_settings={
            'content_type': content_type
        })

        # Get the URL
        file_url = blob_client.url

        return {
            "file_url": file_url,
            "file_type": file_type,
            "file_name": file.filename,
            "file_size": file_size
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.post("/events/{event_id}/vetting-chat/mute-member")
def mute_member_on_submission(
    event_id: int,
    member_email: str,
    reason: str = "submitted_vetting",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mute a committee member when they submit their vetting (internal use)."""
    vetting_chat = get_vetting_chat_for_event(db, event_id)
    if not vetting_chat:
        return {"status": "no_chat"}

    member = db.query(VettingChatMember).filter(
        VettingChatMember.vetting_chat_id == vetting_chat.id,
        VettingChatMember.user_email.ilike(member_email)
    ).first()

    if member:
        member.can_send_messages = False
        member.muted_at = datetime.utcnow()
        member.muted_reason = reason
        db.commit()
        return {"status": "muted", "member_email": member_email}

    return {"status": "member_not_found"}


@router.post("/events/{event_id}/vetting-chat/lock")
def lock_vetting_chat(
    event_id: int,
    reason: str = "approved",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lock the vetting chat when vetting is approved (internal use)."""
    vetting_chat = get_vetting_chat_for_event(db, event_id)
    if not vetting_chat:
        return {"status": "no_chat"}

    vetting_chat.is_locked = True
    vetting_chat.locked_at = datetime.utcnow()
    vetting_chat.locked_reason = reason
    db.commit()

    return {"status": "locked", "reason": reason}


@router.delete("/vetting-chats/cleanup-expired")
def cleanup_expired_vetting_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clean up vetting chats that are 30+ days past event end date."""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can run cleanup"
        )

    today = datetime.utcnow().date()

    # Find expired vetting chats
    expired_chats = db.query(VettingChatRoom).filter(
        VettingChatRoom.scheduled_deletion_date <= today
    ).all()

    deleted_count = 0
    for vetting_chat in expired_chats:
        # Delete the chat room (cascades to messages and vetting chat data)
        chat_room = db.query(ChatRoom).filter(
            ChatRoom.id == vetting_chat.chat_room_id
        ).first()

        if chat_room:
            db.delete(chat_room)
            deleted_count += 1

    db.commit()

    return {
        "status": "cleanup_complete",
        "deleted_chats": deleted_count
    }
