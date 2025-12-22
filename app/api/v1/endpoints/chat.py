from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, select
from typing import List, Optional
import json
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv
from app.db.database import get_db
from app.models.chat import ChatRoom, ChatMessage, DirectMessage, ChatType
from app.models.user import User
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.schemas.chat import (
    ChatRoomCreate, ChatRoom as ChatRoomSchema, ChatMessage as MessageSchema,
    DirectMessageCreate, DirectMessage as DirectMessageSchema,
    MessageCreate, ChatRoomWithMessages, WebSocketMessage
)
from app.api.deps import get_current_user, get_tenant_context
from app.core.websocket_manager import manager, notification_manager

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

print(f"DEBUG CHAT: Cloudinary config - Cloud Name: {os.getenv('CLOUDINARY_CLOUD_NAME')}, API Key: {os.getenv('CLOUDINARY_API_KEY')}")

router = APIRouter()

# Chat Room Management
@router.post("/rooms/", response_model=ChatRoomSchema)
def create_chat_room(
    room: ChatRoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create chat room - admins only"""
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role.upper() not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_room = ChatRoom(
        **room.dict(),
        tenant_id=current_user.tenant_id,
        created_by=current_user.id
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@router.get("/rooms/")
def get_chat_rooms(
    event_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available chat rooms with last message info - auto-create missing event rooms and cleanup old ones"""
    # Auto-cleanup chat rooms for events ended more than 1 month ago
    one_month_ago = datetime.now() - timedelta(days=30)
    old_rooms = db.query(ChatRoom).join(Event).filter(
        and_(
            ChatRoom.chat_type == ChatType.EVENT_CHATROOM,
            Event.end_date < one_month_ago
        )
    ).all()
    
    for room in old_rooms:
        db.query(ChatMessage).filter(ChatMessage.chat_room_id == room.id).delete()
        db.delete(room)
    
    if old_rooms:
        db.commit()
        print(f"AUTO-DELETED: {len(old_rooms)} old chat rooms")
    
    # Auto-create chat rooms for events that don't have them
    events_without_rooms = db.query(Event).outerjoin(
        ChatRoom, and_(Event.id == ChatRoom.event_id, ChatRoom.chat_type == ChatType.EVENT_CHATROOM)
    ).filter(
        ChatRoom.id.is_(None)
    ).all()
    
    created_rooms = []
    for event in events_without_rooms:
        room = ChatRoom(
            name=f"{event.title} - Event Chat",
            chat_type=ChatType.EVENT_CHATROOM,
            event_id=event.id,
            tenant_id=event.tenant_id,
            created_by=1  # System user ID
        )
        db.add(room)
        created_rooms.append(room)
    
    if created_rooms:
        db.commit()
        print(f"AUTO-CREATED: {len(created_rooms)} chat rooms for events")
    
    # Get events user is selected or confirmed to participate in
    user_event_ids = select(EventParticipant.event_id).filter(
        and_(
            EventParticipant.email == current_user.email,
            EventParticipant.status.in_(["selected", "confirmed", "checked_in"])
        )
    )
    
    # Get chat rooms for user's selected events only
    query = db.query(ChatRoom).filter(
        and_(
            ChatRoom.is_active == True,
            ChatRoom.event_id.in_(user_event_ids)
        )
    )
    
    if event_id:
        query = query.filter(ChatRoom.event_id == event_id)
    
    query = query.order_by(ChatRoom.created_at.desc())
    
    rooms = query.all()
    print(f"DEBUG: Found {len(rooms)} chat rooms for user {current_user.email}")
    
    # Build response with last message info
    result = []
    for room in rooms:
        # Get the latest message for this room
        last_message = db.query(ChatMessage).filter(
            ChatMessage.chat_room_id == room.id
        ).order_by(desc(ChatMessage.created_at)).first()
        
        # Count unread group chat notifications from notifications table
        from app.models.notification import Notification, NotificationType
        unread_count = db.query(Notification).filter(
            and_(
                Notification.user_id == current_user.id,
                Notification.notification_type.in_([
                    NotificationType.CHAT_MESSAGE,
                    NotificationType.CHAT_MENTION
                ]),
                Notification.is_read == False,
                # Match notifications for this specific chat room
                Notification.title.like(f"%{room.name}%")
            )
        ).count()
        
        # Format last message with sender name
        formatted_last_message = None
        if last_message:
            sender_name = last_message.sender_name.split('@')[0] if '@' in last_message.sender_name else last_message.sender_name
            if last_message.message:
                formatted_last_message = f"{sender_name}: {last_message.message}"
            elif last_message.file_url:
                # Handle file-only messages
                file_type_display = {
                    'image': '📷 Photo',
                    'document': '📄 Document', 
                    'voice': '🎵 Voice message',
                    'video': '🎥 Video'
                }.get(last_message.file_type, '📎 File')
                formatted_last_message = f"{sender_name}: {file_type_display}"
            else:
                formatted_last_message = f"{sender_name}: Message"
        
        print(f"DEBUG ROOM: {room.name} - last_message obj: message='{last_message.message if last_message else None}', file_url='{last_message.file_url if last_message else None}', formatted='{formatted_last_message}'")
        
        room_data = {
            "id": room.id,
            "name": room.name,
            "description": "",  # Add description if needed
            "chat_type": room.chat_type.value,
            "event_id": room.event_id,
            "is_active": room.is_active,
            "created_by": room.created_by,
            "created_at": room.created_at,
            "event": {
                "id": room.event.id,
                "title": room.event.title
            } if room.event else None,
            "unread_count": unread_count,
            "last_message": formatted_last_message,
            "last_message_time": last_message.created_at if last_message else None
        }
        
        result.append(room_data)
        print(f"DEBUG: Room {room.name} - last_message: '{room_data['last_message']}', last_message_time: {room_data['last_message_time']}")
    
    return result

@router.post("/rooms/auto-create")
def auto_create_event_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-create chat rooms for events that don't have them"""
    
    # Get all events without chat rooms
    events_without_rooms = db.query(Event).outerjoin(
        ChatRoom, and_(Event.id == ChatRoom.event_id, ChatRoom.chat_type == ChatType.EVENT_CHATROOM)
    ).filter(
        ChatRoom.id.is_(None)
    ).all()
    
    created_rooms = []
    for event in events_without_rooms:
        room = ChatRoom(
            name=f"{event.title} - Event Chat",
            chat_type=ChatType.EVENT_CHATROOM,
            event_id=event.id,
            tenant_id=event.tenant_id,
            created_by=current_user.id
        )
        db.add(room)
        created_rooms.append(room)
    
    if created_rooms:
        db.commit()
    
    return {"message": f"Created {len(created_rooms)} chat rooms", "rooms": len(created_rooms)}

@router.post("/upload-attachment")
async def upload_chat_attachment(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload chat attachment (image, document, voice message) to Cloudinary"""
    
    print(f"DEBUG CHAT UPLOAD: File: {file.filename}, Content-Type: {file.content_type}, Size: {file.size}")
    print(f"DEBUG CHAT UPLOAD: User: {current_user.email}")

    # Validate file size (15MB limit for attachments, 5MB for voice)
    max_size = 5 * 1024 * 1024 if file.content_type and 'audio' in file.content_type else 15 * 1024 * 1024

    if file.size and file.size > max_size:
        print(f"DEBUG CHAT UPLOAD: File too large: {file.size} bytes")
        raise HTTPException(
            status_code=400,
            detail=f"File size must be less than {max_size // (1024 * 1024)}MB"
        )

    # Determine file type and folder
    file_type = "document"
    folder = "msafiri-documents/chat-files"
    resource_type = "auto"

    if file.content_type:
        if file.content_type.startswith('image/'):
            file_type = "image"
            folder = "msafiri-documents/chat-images"
            resource_type = "image"
        elif file.content_type.startswith('audio/'):
            file_type = "voice"
            folder = "msafiri-documents/chat-voice"
            resource_type = "video"  # Cloudinary uses 'video' for audio files
        elif file.content_type.startswith('video/'):
            file_type = "video"
            folder = "msafiri-documents/chat-videos"
            resource_type = "video"
        elif file.content_type == 'application/pdf':
            file_type = "document"
            resource_type = "raw"
    
    # Fallback: detect by filename extension if content-type is missing/wrong
    filename = file.filename or ""
    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
        file_type = "image"
        folder = "msafiri-documents/chat-images"
        resource_type = "image"
    elif filename.lower().endswith(('.mp3', '.wav', '.m4a', '.aac', '.ogg')):
        file_type = "voice"
        folder = "msafiri-documents/chat-voice"
        resource_type = "video"
    elif filename.lower().endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv')):
        file_type = "video"
        folder = "msafiri-documents/chat-videos"
        resource_type = "video"

    print(f"DEBUG CHAT UPLOAD: Determined file_type: {file_type}, folder: {folder}, resource_type: {resource_type}")

    try:
        # Validate Cloudinary configuration
        if not os.getenv("CLOUDINARY_CLOUD_NAME"):
            print("DEBUG CHAT UPLOAD: Cloudinary cloud name not configured")
            raise HTTPException(status_code=500, detail="Cloudinary cloud name is not configured")

        # Read file content
        file_content = await file.read()
        print(f"DEBUG CHAT UPLOAD: Read {len(file_content)} bytes from file")

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = file.filename or "file"
        public_id = f"{current_user.email.split('@')[0]}_{timestamp}_{filename.split('.')[0]}"
        
        print(f"DEBUG CHAT UPLOAD: Generated public_id: {public_id}")

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file_content,
            public_id=public_id,
            folder=folder,
            resource_type=resource_type,
            use_filename=True,
            unique_filename=True
        )

        print(f"DEBUG CHAT UPLOAD: Upload successful: {result['secure_url']}")
        print(f"DEBUG CHAT UPLOAD: Public ID: {result['public_id']}")

        return {
            "success": True,
            "file_url": result["secure_url"],
            "file_type": file_type,
            "file_name": filename,
            "file_size": file.size,
            "public_id": result["public_id"],
            "duration": result.get("duration"),  # For audio/video files
            "format": result.get("format")
        }

    except Exception as e:
        print(f"DEBUG CHAT UPLOAD: Upload failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/messages/", response_model=MessageSchema)
async def send_message(
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send message to chat room - allow cross-tenant messaging with mentions"""
    room = db.query(ChatRoom).filter(
        and_(
            ChatRoom.id == message.chat_room_id,
            ChatRoom.is_active == True
        )
    ).first()
    
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    if room.event_id:
        event = db.query(Event).filter(Event.id == room.event_id).first()
        if event and event.end_date < datetime.now().date():
            raise HTTPException(status_code=403, detail="Cannot send messages to ended event chat")
    
    sender_name = current_user.full_name or current_user.email
    print(f"DEBUG: Creating message with sender_name: {sender_name} for user: {current_user.email}")
    
    # Extract mentions from message
    mentioned_users = []
    message_text = message.message or ""
    if '@' in message_text:
        import re
        # Find @mentions in the message
        mention_pattern = r'@([^\s@]+)'
        mentions = re.findall(mention_pattern, message_text)

        for mention in mentions:
            # Find user by name or email
            mentioned_user = db.query(User).filter(
                or_(
                    User.full_name.ilike(f"%{mention}%"),
                    User.email.ilike(f"{mention}%")
                )
            ).first()

            if mentioned_user and mentioned_user.email != current_user.email:
                mentioned_users.append(mentioned_user)

    db_message = ChatMessage(
        chat_room_id=message.chat_room_id,
        sender_email=current_user.email,
        sender_name=sender_name,
        message=message.message,
        reply_to_message_id=getattr(message, 'reply_to_message_id', None),
        is_admin_message=(current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)).upper() in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"],
        file_url=getattr(message, 'file_url', None),
        file_type=getattr(message, 'file_type', None),
        file_name=getattr(message, 'file_name', None),
        file_size=getattr(message, 'file_size', None),
        duration=getattr(message, 'duration', None)
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # Send real-time notification to all users in the tenant
    await notification_manager.broadcast_chat_notification({
        "type": "chat_message",
        "data": {
            "chat_room_id": room.id,
            "chat_room_name": room.name,
            "sender_name": sender_name,
            "message": message.message,
            "timestamp": str(db_message.created_at)
        }
    }, current_user.tenant_id, exclude_user=current_user.email)
    
    # Send notifications and store in database
    try:
        from app.services.firebase_service import firebase_service
        from app.models.event_participant import EventParticipant
        from app import crud
        from app.models.notification import NotificationPriority, NotificationType
        
        print(f"CHAT: Sending notifications for message in room {room.name}")
        
        # Get users who are participants in this event (for event chat rooms)
        target_users = []
        if room.event_id:
            # Get event participants who are selected or confirmed
            participants = db.query(EventParticipant).filter(
                and_(
                    EventParticipant.event_id == room.event_id,
                    EventParticipant.status.in_(["selected", "confirmed"]),
                    EventParticipant.email != current_user.email  # Exclude sender
                )
            ).all()
            
            participant_emails = [p.email for p in participants]
            print(f"CHAT: Found {len(participant_emails)} event participants to notify")
            
            # Get user objects for participants
            target_users = db.query(User).filter(
                and_(
                    User.email.in_(participant_emails),
                    User.is_active == True
                )
            ).all()
        else:
            # For general chat rooms, notify all tenant users
            target_users = db.query(User).filter(
                and_(
                    User.tenant_id == current_user.tenant_id,
                    User.email != current_user.email,
                    User.is_active == True
                )
            ).all()
        
        # Send special notifications to mentioned users
        mention_notifications_sent = 0
        for mentioned_user in mentioned_users:
            try:
                mention_title = f"📢 You were mentioned in {room.name}"
                mention_body = f"{sender_name} mentioned you: {message.message[:80]}{'...' if len(message.message) > 80 else ''}"
                
                # Create database notification for mention
                try:
                    crud.notification.create_user_notification(
                        db,
                        user_id=mentioned_user.id,
                        title=mention_title,
                        message=mention_body,
                        tenant_id=mentioned_user.tenant_id or current_user.tenant_id,
                        priority="HIGH",
                        notification_type=NotificationType.CHAT_MENTION,
                        send_push=True,
                        triggered_by=current_user.email
                    )
                    print(f"CHAT: Created database notification for mention to {mentioned_user.email}")
                except Exception as db_error:
                    print(f"CHAT ERROR: Failed to create database notification for {mentioned_user.email}: {db_error}")
                
                # Send push notification
                if mentioned_user.fcm_token:
                    success = firebase_service.send_to_user(
                        db=db,
                        user_email=mentioned_user.email,
                        title=mention_title,
                        body=mention_body,
                        data={
                            "type": "chat_mention",
                            "chat_room_id": str(room.id),
                            "chat_room_name": room.name,
                            "sender_name": sender_name,
                            "message_preview": message.message[:100],
                            "mentioned": True
                        }
                    )
                    if success:
                        mention_notifications_sent += 1
                        print(f"CHAT: Mention push notification sent to {mentioned_user.email}")
            except Exception as e:
                print(f"CHAT ERROR: Failed to send mention notification to {mentioned_user.email}: {e}")
        
        print(f"CHAT: Sent {mention_notifications_sent} mention notifications")
        
        # Send regular notifications to other participants (only if no mentions or for non-mentioned users)
        if not mentioned_users:  # Only send group notifications if no mentions
            print(f"CHAT: Sending group notifications to {len(target_users)} users")
            
            notification_title = f"💬 {room.name}"
            notification_body = f"{sender_name}: {message.message[:100]}{'...' if len(message.message) > 100 else ''}"
            
            notifications_sent = 0
            for user in target_users:
                try:
                    # Create database notification for group message
                    try:
                        crud.notification.create_user_notification(
                            db,
                            user_id=user.id,
                            title=notification_title,
                            message=notification_body,
                            tenant_id=user.tenant_id or current_user.tenant_id,
                            priority="MEDIUM",
                            notification_type=NotificationType.CHAT_MESSAGE,
                            send_push=True,
                            triggered_by=current_user.email
                        )
                        print(f"CHAT: Created database notification for {user.email}")
                    except Exception as db_error:
                        print(f"CHAT ERROR: Failed to create database notification for {user.email}: {db_error}")
                    
                    # Send push notification
                    if user.fcm_token:
                        success = firebase_service.send_to_user(
                            db=db,
                            user_email=user.email,
                            title=notification_title,
                            body=notification_body,
                            data={
                                "type": "chat_message",
                                "chat_room_id": str(room.id),
                                "chat_room_name": room.name,
                                "sender_name": sender_name,
                                "message_preview": message.message[:100]
                            }
                        )
                        if success:
                            notifications_sent += 1
                            print(f"CHAT: Push notification sent to {user.email}")
                    else:
                        print(f"CHAT: Skipping push for {user.email} (no FCM token)")
                except Exception as user_error:
                    print(f"CHAT ERROR: Failed to send notification to {user.email}: {user_error}")
            
            print(f"CHAT: Successfully sent {notifications_sent} group notifications")
        else:
            print(f"CHAT: Skipping group notifications because message contains mentions")
        
    except Exception as e:
        print(f"CHAT ERROR: Failed to send push notifications: {e}")
        import traceback
        traceback.print_exc()
    
    return db_message

@router.get("/rooms/{room_id}/messages", response_model=List[MessageSchema])
def get_room_messages(
    room_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat room messages with reply context - allow cross-tenant access"""
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.chat_room_id == room_id
    ).order_by(desc(ChatMessage.created_at)).limit(limit).all()
    
    # Add reply context to messages
    result_messages = []
    for message in messages:
        message_dict = {
            "id": message.id,
            "chat_room_id": message.chat_room_id,
            "sender_email": message.sender_email,
            "sender_name": message.sender_name,
            "message": message.message,
            "reply_to_message_id": message.reply_to_message_id,
            "is_admin_message": message.is_admin_message,
            "created_at": message.created_at,
            "file_url": message.file_url,
            "file_type": message.file_type,
            "file_name": message.file_name,
            "file_size": message.file_size,
            "duration": message.duration,
            "reply_to": None
        }
        
        if message.reply_to_message_id:
            reply_to = db.query(ChatMessage).filter(
                ChatMessage.id == message.reply_to_message_id
            ).first()
            if reply_to:
                message_dict["reply_to"] = {
                    "id": reply_to.id,
                    "sender_name": reply_to.sender_name,
                    "message": reply_to.message
                }
        
        result_messages.append(message_dict)
    
    return result_messages

@router.get("/rooms/{room_id}/status")
def get_room_status(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat room status - allow cross-tenant access"""
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    can_send_messages = True
    event_status = "active"
    
    if room.event_id:
        event = db.query(Event).filter(Event.id == room.event_id).first()
        if event:
            now = datetime.now().date()
            if event.end_date < now:
                can_send_messages = False
                event_status = "ended"
            elif event.start_date > now:
                event_status = "upcoming"
            else:
                event_status = "ongoing"
    
    return {
        "room_id": room_id,
        "can_send_messages": can_send_messages,
        "event_status": event_status,
        "room_name": room.name
    }

@router.delete("/cleanup-ended-events")
def cleanup_ended_event_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cleanup chat rooms for events ended more than 1 month ago"""
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role.upper() not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    one_month_ago = datetime.now() - timedelta(days=30)
    
    rooms_to_delete = db.query(ChatRoom).join(Event).filter(
        and_(
            ChatRoom.chat_type == ChatType.EVENT_CHATROOM,
            Event.end_date < one_month_ago
        )
    ).all()
    
    deleted_count = 0
    for room in rooms_to_delete:
        db.query(ChatMessage).filter(ChatMessage.chat_room_id == room.id).delete()
        db.delete(room)
        deleted_count += 1
    
    db.commit()
    return {"message": f"Deleted {deleted_count} ended event chat rooms"}





# Direct Messages
@router.post("/direct-messages/", response_model=DirectMessageSchema)
async def send_direct_message(
    dm: DirectMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_context: str = Depends(get_tenant_context)
):
    """Send direct message to any user"""
    print(f"DEBUG: Direct message - Current user: {current_user.email}")
    print(f"DEBUG: Direct message - Current user tenant_id: {current_user.tenant_id}")
    print(f"DEBUG: Direct message - Tenant context: {tenant_context}")
    print(f"DEBUG: Direct message - Request data: {dm.dict()}")
    
    # Ensure tenant_context is not None
    if not tenant_context:
        print(f"ERROR: Direct message - tenant_context is None or empty")
        print(f"ERROR: Direct message - current_user.tenant_id: {current_user.tenant_id}")
        print(f"ERROR: Direct message - current_user.role: {current_user.role}")
        raise HTTPException(status_code=400, detail="No tenant context available")
    
    # Verify recipient exists - allow cross-tenant messaging
    recipient = db.query(User).filter(
        and_(
            User.email == dm.recipient_email,
            User.is_active == True
        )
    ).first()
    
    if not recipient:
        raise HTTPException(status_code=400, detail="Recipient not found")
    
    # Use tenant_context which properly extracts from X-Tenant-ID header
    db_dm = DirectMessage(
        sender_email=current_user.email,
        sender_name=current_user.full_name or current_user.email,
        recipient_email=dm.recipient_email,
        recipient_name=recipient.full_name or recipient.email,
        message=dm.message,
        reply_to_message_id=dm.reply_to_message_id,
        tenant_id=tenant_context,
        file_url=getattr(dm, 'file_url', None),
        file_type=getattr(dm, 'file_type', None),
        file_name=getattr(dm, 'file_name', None),
        file_size=getattr(dm, 'file_size', None),
        duration=getattr(dm, 'duration', None)
    )
    
    print(f"DEBUG: Direct message - Creating DB record with tenant_id: {tenant_context}")
    db.add(db_dm)
    db.commit()
    db.refresh(db_dm)
    
    # Send real-time notification to recipient
    await notification_manager.send_user_notification({
        "type": "chat_message",
        "data": {
            "sender_name": current_user.full_name or current_user.email,
            "message": dm.message,
            "timestamp": str(db_dm.created_at)
        }
    }, dm.recipient_email)
    
    # Send notification and store in database
    try:
        from app.services.firebase_service import firebase_service
        from app import crud
        from app.models.notification import NotificationPriority, NotificationType
        
        print(f"CHAT: Sending direct message notification to {recipient.email}")
        
        notification_title = f"💬 {current_user.full_name or current_user.email}"
        notification_body = (dm.message[:100] + "..." if len(dm.message) > 100 else dm.message) if dm.message else "📎 Attachment"
        
        # Create database notification for direct message
        try:
            crud.notification.create_user_notification(
                db,
                user_id=recipient.id,
                title=notification_title,
                message=notification_body,
                tenant_id=recipient.tenant_id or current_user.tenant_id,
                priority="MEDIUM",
                notification_type=NotificationType.CHAT_MESSAGE,
                send_push=True,
                triggered_by=current_user.email
            )
            print(f"CHAT: Created database notification for direct message to {recipient.email}")
        except Exception as db_error:
            print(f"CHAT ERROR: Failed to create database notification for {recipient.email}: {db_error}")
        
        # Send push notification
        if recipient.fcm_token:
            success = firebase_service.send_to_user(
                db=db,
                user_email=recipient.email,
                title=notification_title,
                body=notification_body,
                data={
                    "type": "direct_message",
                    "sender_email": current_user.email,
                    "sender_name": current_user.full_name or current_user.email,
                    "message_preview": dm.message[:100]
                }
            )
            
            if success:
                print(f"CHAT: Direct message push notification sent to {recipient.email}")
            else:
                print(f"CHAT: Failed to send push notification to {recipient.email}")
        else:
            print(f"CHAT: Recipient {recipient.email} has no FCM token")
            
    except Exception as e:
        print(f"CHAT ERROR: Failed to send direct message push notification: {e}")
        import traceback
        traceback.print_exc()
    
    return db_dm

@router.get("/direct-messages/", response_model=List[DirectMessageSchema])
def get_direct_messages(
    with_user: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get direct messages (sent or received) - allow cross-tenant messaging"""
    query = db.query(DirectMessage).filter(
        or_(
            DirectMessage.sender_email == current_user.email,
            DirectMessage.recipient_email == current_user.email
        )
    )
    
    if with_user:
        query = query.filter(
            or_(
                and_(DirectMessage.sender_email == current_user.email, DirectMessage.recipient_email == with_user),
                and_(DirectMessage.sender_email == with_user, DirectMessage.recipient_email == current_user.email)
            )
        )
    
    messages = query.order_by(desc(DirectMessage.created_at)).all()
    
    # Add reply context to messages
    result_messages = []
    for message in messages:
        message_dict = {
            "id": message.id,
            "sender_email": message.sender_email,
            "sender_name": message.sender_name,
            "recipient_email": message.recipient_email,
            "recipient_name": message.recipient_name,
            "message": message.message,
            "reply_to_message_id": message.reply_to_message_id,
            "is_read": message.is_read,
            "tenant_id": message.tenant_id,
            "created_at": message.created_at,
            "file_url": message.file_url,
            "file_type": message.file_type,
            "file_name": message.file_name,
            "file_size": message.file_size,
            "duration": message.duration,
            "reply_to": None
        }
        
        if message.reply_to_message_id:
            reply_to = db.query(DirectMessage).filter(
                DirectMessage.id == message.reply_to_message_id
            ).first()
            if reply_to:
                message_dict["reply_to"] = {
                    "id": reply_to.id,
                    "sender_name": reply_to.sender_name,
                    "message": reply_to.message
                }
        
        result_messages.append(message_dict)
    
    return result_messages

@router.get("/conversations/")
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of users with whom current user has conversations"""

    
    # Get unique conversation partners - allow cross-tenant conversations
    sent_to = db.query(DirectMessage.recipient_email, DirectMessage.recipient_name).filter(
        DirectMessage.sender_email == current_user.email
    ).distinct()
    
    received_from = db.query(DirectMessage.sender_email, DirectMessage.sender_name).filter(
        DirectMessage.recipient_email == current_user.email
    ).distinct()
    
    conversations = []
    
    # Process sent messages
    for email, name in sent_to:
        if email != current_user.email:
            # Get last message
            last_msg = db.query(DirectMessage).filter(
                or_(
                    and_(DirectMessage.sender_email == current_user.email, DirectMessage.recipient_email == email),
                    and_(DirectMessage.sender_email == email, DirectMessage.recipient_email == current_user.email)
                )
            ).order_by(desc(DirectMessage.created_at)).first()
            
            # Count unread messages (only messages FROM other user TO current user)
            unread_count = db.query(DirectMessage).filter(
                and_(
                    DirectMessage.sender_email == email,
                    DirectMessage.recipient_email == current_user.email,
                    DirectMessage.is_read == False
                )
            ).count()
            

            
            conversations.append({
                "email": email,
                "name": name,
                "last_message": last_msg.message if last_msg else None,
                "last_message_time": last_msg.created_at if last_msg else None,
                "unread_count": unread_count
            })
    
    # Process received messages
    for email, name in received_from:
        if email != current_user.email and not any(c["email"] == email for c in conversations):
            # Get last message
            last_msg = db.query(DirectMessage).filter(
                or_(
                    and_(DirectMessage.sender_email == current_user.email, DirectMessage.recipient_email == email),
                    and_(DirectMessage.sender_email == email, DirectMessage.recipient_email == current_user.email)
                )
            ).order_by(desc(DirectMessage.created_at)).first()
            
            # Count unread messages (only messages FROM other user TO current user)
            unread_count = db.query(DirectMessage).filter(
                and_(
                    DirectMessage.sender_email == email,
                    DirectMessage.recipient_email == current_user.email,
                    DirectMessage.is_read == False
                )
            ).count()
            

            
            conversations.append({
                "email": email,
                "name": name,
                "last_message": last_msg.message if last_msg else None,
                "last_message_time": last_msg.created_at if last_msg else None,
                "unread_count": unread_count
            })
    
    # Sort by last message time
    conversations.sort(key=lambda x: x["last_message_time"] or datetime.min, reverse=True)
    

    
    return conversations

@router.put("/direct-messages/{message_id}/read")
def mark_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark direct message as read"""
    message = db.query(DirectMessage).filter(
        and_(
            DirectMessage.id == message_id,
            DirectMessage.recipient_email == current_user.email
        )
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.is_read = True
    db.commit()
    return {"message": "Marked as read"}

@router.get("/users/", response_model=List[dict])
def get_available_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of all users for direct messaging - no tenant filtering"""
    users = db.query(User).filter(
        and_(
            User.is_active == True,
            User.email != current_user.email
        )
    ).all()
    
    print(f"DEBUG: Found {len(users)} total active users (no tenant filter)")
    print(f"DEBUG: Current user: {current_user.email}, Tenant: {current_user.tenant_id}")
    for user in users:
        print(f"DEBUG: User: {user.email}, Role: {user.role}, Active: {user.is_active}, Tenant: {user.tenant_id}, Full Name: {user.full_name}")
    
    result = [
        {
            "email": user.email,
            "name": user.full_name or user.email,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
        }
        for user in users
    ]
    print(f"DEBUG: Returning {len(result)} users as contacts")
    return result

@router.get("/rooms/{room_id}/participants", response_model=List[dict])
def get_room_participants(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of users who can be mentioned in this chat room"""
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
    
    if not room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    # For event chat rooms, get event participants
    if room.event_id:
        from app.models.event_participant import EventParticipant
        
        participants = db.query(EventParticipant).filter(
            and_(
                EventParticipant.event_id == room.event_id,
                EventParticipant.status.in_(["selected", "confirmed", "checked_in"]),
                EventParticipant.email != current_user.email
            )
        ).all()
        
        participant_emails = [p.email for p in participants]
        
        # Get user objects for participants
        users = db.query(User).filter(
            and_(
                User.email.in_(participant_emails),
                User.is_active == True
            )
        ).all()
    else:
        # For general chat rooms, get all tenant users
        users = db.query(User).filter(
            and_(
                User.tenant_id == current_user.tenant_id,
                User.email != current_user.email,
                User.is_active == True
            )
        ).all()
    
    result = [
        {
            "email": user.email,
            "name": user.full_name or user.email.split('@')[0],
        }
        for user in users
    ]
    
    print(f"DEBUG: Returning {len(result)} users for room {room_id} mentions")
    return result

@router.get("/unread-count")
def get_total_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get unread direct message count for current user - excludes group chat notifications"""
    try:
        # Count only unread direct messages (group chat notifications are handled by notification system)
        direct_unread = db.query(DirectMessage).filter(
            and_(
                DirectMessage.recipient_email == current_user.email,
                DirectMessage.is_read == False
            )
        ).count()
        
        # Group chat notifications are handled by the notification system, not here
        # This prevents double counting since group chat messages are stored as notifications
        
        print(f"CHAT UNREAD: User {current_user.email} has {direct_unread} direct messages (group chats handled by notifications)")
        
        return {
            "total_unread": direct_unread,  # Only direct messages for chat badge
            "direct_unread": direct_unread,
            "group_unread": 0  # Group chats are in notifications, not chat count
        }
    except Exception as e:
        print(f"ERROR getting unread count: {e}")
        return {
            "total_unread": 0,
            "direct_unread": 0,
            "group_unread": 0
        }

@router.post("/rooms/{room_id}/mark-read")
def mark_room_as_read(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all group chat notifications as read for this room"""
    try:
        from app.models.notification import Notification, NotificationType
        
        # Get the room to get its name for matching notifications
        room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Chat room not found")
        
        # Mark all unread chat notifications for this room as read
        notifications_updated = db.query(Notification).filter(
            and_(
                Notification.user_id == current_user.id,
                Notification.notification_type.in_([
                    NotificationType.CHAT_MESSAGE,
                    NotificationType.CHAT_MENTION
                ]),
                Notification.is_read == False,
                # Match notifications for this specific chat room
                Notification.title.like(f"%{room.name}%")
            )
        ).update({"is_read": True})
        
        db.commit()
        
        return {
            "message": f"Marked {notifications_updated} notifications as read for room {room.name}",
            "notifications_marked": notifications_updated
        }
    except Exception as e:
        print(f"Error marking room as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark room as read")

@router.get("/admins/", response_model=List[dict])
def get_available_admins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of admins for direct messaging"""
    admins = db.query(User).filter(
        and_(
            User.tenant_id == current_user.tenant_id,
            or_(
                User.role.in_(["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]),
                User.role.in_(["mt_admin", "hr_admin", "event_admin", "super_admin"])
            ),
            User.is_active == True
        )
    ).all()
    
    return [
        {
            "email": admin.email,
            "name": admin.full_name or admin.email,
            "role": admin.role.value if hasattr(admin.role, 'value') else str(admin.role)
        }
        for admin in admins
    ]

# WebSocket endpoint for real-time notifications
@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str,
    tenant: str,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time notifications"""
    try:
        # Verify token and get user
        from app.core.security import verify_token
        from app.crud.user import get_by_email
        
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=1008)
            return
        
        user = get_by_email(db, email=payload.get("sub"))
        if not user:
            await websocket.close(code=1008)
            return
        
        await notification_manager.connect_user(websocket, user.email, tenant)
        
        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    
    except WebSocketDisconnect:
        notification_manager.disconnect_user(websocket, user.email if 'user' in locals() else None)
    except Exception as e:
        print(f"WebSocket notification error: {e}")
        await websocket.close(code=1011)

# WebSocket endpoint for real-time chat
@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time chat"""
    try:
        # Verify token and get user (simplified - you may want to use proper JWT verification)
        from app.core.security import verify_token
        from app.crud.user import get_by_email
        
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=1008)
            return
        
        user = get_by_email(db, email=payload.get("sub"))
        if not user:
            await websocket.close(code=1008)
            return
        
        # Verify room exists
        room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
        if not room:
            await websocket.close(code=1008)
            return
        
        user_info = {
            "email": user.email,
            "name": user.full_name or user.email,
            "is_admin": (user.role.value if hasattr(user.role, 'value') else str(user.role)).upper() in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]
        }
        
        await manager.connect(websocket, room_id, user_info)
        
        # Notify room about new user
        await manager.broadcast_to_room({
            "type": "user_joined",
            "user": user_info,
            "timestamp": str(datetime.now())
        }, room_id)
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            print(f"🔌 WebSocket received: {message_data['type']} from {user.email} in room {room_id}")
            
            if message_data["type"] == "message":
                print(f"💬 WebSocket message: '{message_data['message'][:50]}...' from {user.email}")
                
                # Save message to database
                db_message = ChatMessage(
                    chat_room_id=room_id,
                    sender_email=user.email,
                    sender_name=user.full_name or user.email,
                    message=message_data["message"],
                    is_admin_message=user_info["is_admin"]
                )
                db.add(db_message)
                db.commit()
                db.refresh(db_message)
                
                print(f"💾 Saved WebSocket message to DB with ID {db_message.id}")
                
                # Broadcast to room
                broadcast_data = {
                    "type": "message",
                    "id": db_message.id,
                    "sender_email": user.email,
                    "sender_name": user.full_name or user.email,
                    "message": message_data["message"],
                    "is_admin_message": user_info["is_admin"],
                    "timestamp": str(db_message.created_at)
                }
                
                await manager.broadcast_to_room(broadcast_data, room_id)
                print(f"📡 Broadcasted WebSocket message to room {room_id}")
                
            elif message_data["type"] == "ping":
                print(f"🏓 WebSocket ping from {user.email}")
                await websocket.send_text(json.dumps({"type": "pong"}))
                print(f"🏓 WebSocket pong sent to {user.email}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        await manager.broadcast_to_room({
            "type": "user_left",
            "user": user_info,
            "timestamp": str(datetime.now())
        }, room_id)
    except Exception as e:
        await websocket.close(code=1011)