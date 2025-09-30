from typing import Dict, List
from fastapi import WebSocket
import json

class ConnectionManager:
    def __init__(self):
        # Store connections by chat room ID
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Store user info for each connection
        self.connection_users: Dict[WebSocket, dict] = {}
    
    async def connect(self, websocket: WebSocket, chat_room_id: int, user_info: dict):
        await websocket.accept()
        
        if chat_room_id not in self.active_connections:
            self.active_connections[chat_room_id] = []
        
        self.active_connections[chat_room_id].append(websocket)
        self.connection_users[websocket] = user_info
    
    def disconnect(self, websocket: WebSocket, chat_room_id: int):
        if chat_room_id in self.active_connections:
            if websocket in self.active_connections[chat_room_id]:
                self.active_connections[chat_room_id].remove(websocket)
        
        if websocket in self.connection_users:
            del self.connection_users[websocket]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast_to_room(self, message: dict, chat_room_id: int):
        if chat_room_id in self.active_connections:
            connection_count = len(self.active_connections[chat_room_id])
            print(f"📡 Broadcasting to {connection_count} connections in room {chat_room_id}")
            
            for connection in self.active_connections[chat_room_id]:
                try:
                    await connection.send_text(json.dumps(message))
                    print(f"✅ Message sent to WebSocket connection")
                except Exception as e:
                    print(f"❌ Failed to send to WebSocket connection: {e}")
                    # Remove broken connections
                    self.active_connections[chat_room_id].remove(connection)
        else:
            print(f"⚠️ No active connections found for room {chat_room_id}")
    
    def get_room_users(self, chat_room_id: int) -> List[dict]:
        if chat_room_id not in self.active_connections:
            return []
        
        users = []
        for connection in self.active_connections[chat_room_id]:
            if connection in self.connection_users:
                users.append(self.connection_users[connection])
        return users

class NotificationManager:
    def __init__(self):
        # Store notification connections by user email
        self.user_connections: Dict[str, WebSocket] = {}
        # Store tenant info for each user
        self.user_tenants: Dict[str, str] = {}
    
    async def connect_user(self, websocket: WebSocket, user_email: str, tenant_id: str):
        await websocket.accept()
        self.user_connections[user_email] = websocket
        self.user_tenants[user_email] = tenant_id
        print(f"User {user_email} connected for notifications")
    
    def disconnect_user(self, websocket: WebSocket, user_email: str = None):
        if user_email and user_email in self.user_connections:
            del self.user_connections[user_email]
            if user_email in self.user_tenants:
                del self.user_tenants[user_email]
            print(f"User {user_email} disconnected from notifications")
    
    async def send_user_notification(self, notification: dict, user_email: str):
        if user_email in self.user_connections:
            try:
                await self.user_connections[user_email].send_text(json.dumps(notification))
            except:
                # Remove broken connection
                self.disconnect_user(None, user_email)
    
    async def broadcast_chat_notification(self, notification: dict, tenant_id: str, exclude_user: str = None):
        """Broadcast chat notification to all users in tenant except sender"""
        for user_email, websocket in list(self.user_connections.items()):
            if (user_email != exclude_user and 
                self.user_tenants.get(user_email) == tenant_id):
                try:
                    await websocket.send_text(json.dumps(notification))
                except:
                    # Remove broken connection
                    self.disconnect_user(websocket, user_email)
    
    async def broadcast_system_notification(self, notification: dict, tenant_id: str = None):
        """Broadcast system notification to all users or specific tenant"""
        for user_email, websocket in list(self.user_connections.items()):
            if tenant_id is None or self.user_tenants.get(user_email) == tenant_id:
                try:
                    await websocket.send_text(json.dumps(notification))
                except:
                    # Remove broken connection
                    self.disconnect_user(websocket, user_email)

# Global connection manager instances
manager = ConnectionManager()
notification_manager = NotificationManager()