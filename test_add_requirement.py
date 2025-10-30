#!/usr/bin/env python3
"""
Simple script to add a travel requirement for testing
"""
import requests
import json

# Configuration
API_BASE_URL = "http://localhost:8000"
TENANT_ID = 1  # Adjust based on your tenant
COUNTRY = "Kenya"  # Adjust based on your event country

def add_travel_requirement():
    """Add a test travel requirement"""
    
    # Login first (you'll need valid credentials)
    login_data = {
        "email": "admin@example.com",  # Replace with valid admin email
        "password": "your_password"    # Replace with valid password
    }
    
    # Login to get token
    login_response = requests.post(f"{API_BASE_URL}/auth/login", json=login_data)
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check if requirement already exists
    existing_response = requests.get(
        f"{API_BASE_URL}/country-travel-requirements/tenant/{TENANT_ID}/country/{COUNTRY}",
        headers=headers
    )
    
    if existing_response.status_code == 200:
        print(f"Travel requirement for {COUNTRY} already exists")
        existing_req = existing_response.json()
        
        # Update to add a new additional requirement
        update_data = {
            "additional_requirements": [
                {
                    "name": "Visa Required",
                    "required": True,
                    "description": "Valid visa document for entry"
                },
                {
                    "name": "Accommodation Booking",
                    "required": True,
                    "description": "Hotel or accommodation confirmation"
                },
                {
                    "name": "Travel Insurance",
                    "required": True,
                    "description": "Valid travel insurance coverage"
                }
            ]
        }
        
        update_response = requests.put(
            f"{API_BASE_URL}/country-travel-requirements/tenant/{TENANT_ID}/country/{COUNTRY}",
            headers=headers,
            json=update_data
        )
        
        if update_response.status_code == 200:
            print("Successfully updated travel requirements!")
            print(json.dumps(update_response.json(), indent=2))
        else:
            print(f"Update failed: {update_response.text}")
    else:
        # Create new requirement
        requirement_data = {
            "country": COUNTRY,
            "visa_required": True,
            "eta_required": False,
            "passport_required": True,
            "flight_ticket_required": True,
            "additional_requirements": [
                {
                    "name": "Visa Required",
                    "required": True,
                    "description": "Valid visa document for entry"
                },
                {
                    "name": "Accommodation Booking",
                    "required": True,
                    "description": "Hotel or accommodation confirmation"
                },
                {
                    "name": "Travel Insurance",
                    "required": True,
                    "description": "Valid travel insurance coverage"
                }
            ]
        }
        
        create_response = requests.post(
            f"{API_BASE_URL}/country-travel-requirements/tenant/{TENANT_ID}",
            headers=headers,
            json=requirement_data
        )
        
        if create_response.status_code == 200:
            print("Successfully created travel requirements!")
            print(json.dumps(create_response.json(), indent=2))
        else:
            print(f"Creation failed: {create_response.text}")

if __name__ == "__main__":
    add_travel_requirement()