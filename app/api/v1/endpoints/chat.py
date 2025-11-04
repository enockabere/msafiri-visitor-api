from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, select
from typing import List
import json
from datetime import datetime, timedelta
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
        
        # Count unread messages (for now, we'll set to 0 since we don't track read status for group chats)
        unread_count = 0
        
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
            "last_message": last_message.message if last_message else None,
            "last_message_time": last_message.created_at if last_message else None
        }
        
        result.append(room_data)
        print(f"DEBUG: Room {room.name} - last_message: {room_data['last_message']}, last_message_time: {room_data['last_message_time']}")
    
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

@router.post("/messages/", response_model=MessageSchema)
async def send_message(
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send message to chat room - allow cross-tenant messaging"""
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
    
    db_message = ChatMessage(
        chat_room_id=message.chat_room_id,
        sender_email=current_user.email,
        sender_name=sender_name,
        message=message.message,
        reply_to_message_id=getattr(message, 'reply_to_message_id', None),
        is_admin_message=(current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)).upper() in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN", "SUPER_ADMIN"]
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
    
    # Send push notifications to group participants only
    try:
        from app.services.firebase_service import firebase_service
        from app.models.event_participant import EventParticipant
        
        print(f"CHAT: Sending push notifications for message in room {room.name}")
        
        # Get users who are participants in this event (for event chat rooms)
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
        
        print(f"CHAT: Sending push notifications to {len(target_users)} users")
        
        notification_title = f"💬 {room.name}"
        notification_body = f"{sender_name}: {message.message[:100]}{'...' if len(message.message) > 100 else ''}"
        
        notifications_sent = 0
        for user in target_users:
            try:
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
                    print(f"CHAT: Skipping {user.email} (no FCM token)")
            except Exception as user_error:
                print(f"CHAT ERROR: Failed to send push notification to {user.email}: {user_error}")
        
        print(f"CHAT: Successfully sent {notifications_sent} push notifications")
        
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
        tenant_id=tenant_context
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
    
    # Send push notification to recipient only
    try:
        from app.services.firebase_service import firebase_service
        
        print(f"CHAT: Sending direct message push notification to {recipient.email}")
        
        if recipient.fcm_token:
            notification_title = f"💬 {current_user.full_name or current_user.email}"
            notification_body = dm.message[:100] + "..." if len(dm.message) > 100 else dm.message
            
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
    print(f"DEBUG CONV: Getting conversations for user {current_user.email}")
    
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
            
            print(f"DEBUG CONV: Sent to {email}, unread_count: {unread_count}, last_msg: {last_msg.message if last_msg else None}")
            
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
            
            print(f"DEBUG CONV: Received from {email}, unread_count: {unread_count}, last_msg: {last_msg.message if last_msg else None}")
            
            conversations.append({
                "email": email,
                "name": name,
                "last_message": last_msg.message if last_msg else None,
                "last_message_time": last_msg.created_at if last_msg else None,
                "unread_count": unread_count
            })
    
    # Sort by last message time
    conversations.sort(key=lambda x: x["last_message_time"] or datetime.min, reverse=True)
    
    print(f"DEBUG CONV: Returning {len(conversations)} conversations")
    for conv in conversations:
        print(f"DEBUG CONV: {conv['email']} - unread: {conv['unread_count']}, last: {conv['last_message']}")
    
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