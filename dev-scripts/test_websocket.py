#!/usr/bin/env python3
"""
Simple WebSocket test script for chat notifications
"""
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/api/v1/chat/ws/notifications?token=test&tenant=test"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")
            
            # Send a test message
            await websocket.send(json.dumps({
                "type": "test",
                "message": "Hello WebSocket!"
            }))
            
            # Listen for messages
            async for message in websocket:
                data = json.loads(message)
                print(f"Received: {data}")
                
    except Exception as e:
        print(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())