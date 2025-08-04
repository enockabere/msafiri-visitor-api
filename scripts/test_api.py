"""
Simple script to test the API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    response = requests.get("http://localhost:8000/health")
    print("Health check:", response.json())

def test_login(email, password, tenant_slug=None):
    if tenant_slug:
        # Use tenant-specific login
        login_data = {
            "email": email,
            "password": password,
            "tenant_slug": tenant_slug
        }
        response = requests.post(f"{BASE_URL}/auth/login/tenant", json=login_data)
    else:
        # Use OAuth2 login (for super admin)
        login_data = {
            "username": email,
            "password": password,
            "grant_type": "password"
        }
        response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"Login successful for {email}")
        return token
    else:
        print(f"Login failed for {email}: {response.text}")
        return None

def test_protected_endpoint(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/auth/test-token", headers=headers)
    if response.status_code == 200:
        user_data = response.json()
        print(f"Token test successful: {user_data['full_name']} ({user_data['role']})")
        return user_data
    else:
        print(f"Token test failed: {response.text}")
        return None

def test_get_users(token, tenant_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    
    response = requests.get(f"{BASE_URL}/users/", headers=headers)
    if response.status_code == 200:
        users = response.json()
        print(f"Found {len(users)} users")
        for user in users:
            print(f"  - {user['full_name']} ({user['email']}) - {user['role']}")
    else:
        print(f"Get users failed: {response.text}")

def main():
    print("Testing Msafiri API...")
    print("=" * 50)
    
    # Test health
    test_health()
    print()
    
    # Test super admin login
    super_admin_token = test_login("superadmin@msafiri.org", "admin123")
    if super_admin_token:
        test_protected_endpoint(super_admin_token)
        print("Testing super admin access to tenant users...")
        test_get_users(super_admin_token, "msf-kenya")
    print()
    
    # Test MT admin login
    mt_admin_token = test_login("mtadmin@msf-kenya.org", "admin123", "msf-kenya")
    if mt_admin_token:
        test_protected_endpoint(mt_admin_token)
        print("Testing MT admin access to users...")
        test_get_users(mt_admin_token)
    print()
    
    # Test visitor login
    visitor_token = test_login("visitor@example.com", "visitor123", "msf-kenya")
    if visitor_token:
        test_protected_endpoint(visitor_token)
    
    print("\nAPI testing completed!")

if __name__ == "__main__":
    main()