#!/usr/bin/env python3
"""
MSF Passport Data Extraction API Test
Sends JSON payload with base64-encoded passport image
"""

import requests
import base64


def extract_passport_data(image_path):
    """Extract passport data from image file"""
    
    API_URL = "https://ko-hr.kenya.msf.org/api/v1/extract-passport-data"
    API_KEY = "n5BOC1ZH*o64Ux^%!etd4$rfUoj7iQrXSXOgk6uW"
    
    print(f"Loading image: {image_path}")
    
    # Read and encode the image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    print(f"Image encoded: {len(image_base64)} characters")
    print(f"Sending request to: {API_URL}")
    
    # Headers (matching screenshot)
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }
    
    # JSON payload (raw data)
    payload = {
        "image_data": image_base64
    }
    
    # Send JSON request
    response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{response.text}")
    
    return response.json() if response.status_code == 200 else None


if __name__ == "__main__":
    image_path = "passport.png"
    
    result = extract_passport_data(image_path)
    
    if result:
        print("\n✓ SUCCESS!")
        print("Extracted data:", result)
    else:
        print("\n✗ FAILED")