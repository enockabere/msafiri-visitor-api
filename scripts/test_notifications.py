"""
Test the notification system
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def get_auth_token(email: str, password: str) -> str:
    """Get authentication token"""
    login_data = {
        "username": email,
        "password": password,
        "grant_type": "password"
    }
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Login failed: {response.text}")

def test_notifications():
    """Test notification endpoints"""
    print("Testing Notification System...")
    print("=" * 50)
    
    try:
        # Get admin token
        admin_token = get_auth_token("admin@msafiri.org", "admin123")
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test 1: Send broadcast notification
        print("1. Testing broadcast notification...")
        broadcast_data = {
            "title": "System Maintenance Notice",
            "message": "The system will be under maintenance on Sunday 2-4 AM.",
            "priority": "high",
            "send_email": True
        }
        response = requests.post(f"{BASE_URL}/notifications/broadcast", 
                               json=broadcast_data, headers=headers)
        print(f"   Broadcast result: {response.status_code}")
        
        # Test 2: Get notifications
        print("2. Testing get notifications...")
        response = requests.get(f"{BASE_URL}/notifications/", headers=headers)
        if response.status_code == 200:
            notifications = response.json()
            print(f"   Found {len(notifications)} notifications")
        
        # Test 3: Get notification stats
        print("3. Testing notification stats...")
        response = requests.get(f"{BASE_URL}/notifications/stats", headers=headers)
        if response.status_code == 200:
            stats = response.json()
            print(f"   Stats: {stats}")
        
        # Test 4: Test user role change (triggers notification)
        print("4. Testing role change notification...")
        # First get a user to change
        response = requests.get(f"{BASE_URL}/users/", headers=headers)
        if response.status_code == 200:
            users = response.json()
            if users:
                test_user = users[0]
                role_change_url = f"{BASE_URL}/users/change-role/{test_user['id']}"
                response = requests.post(f"{role_change_url}?new_role=staff", headers=headers)
                print(f"   Role change result: {response.status_code}")
        
        print("\n✅ Notification tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_notifications()