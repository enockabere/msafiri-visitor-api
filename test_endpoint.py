import requests

# Test if the router is working
print("Testing line manager recommendation router...")
response = requests.get("http://41.90.240.229:8000/api/v1/line-manager-recommendation/test")
print("Test endpoint:", response.status_code, response.json() if response.status_code == 200 else response.text)

# Test the delete endpoint
print("\nTesting delete endpoint...")
response = requests.delete("http://41.90.240.229:8000/api/v1/line-manager-recommendation/debug/delete-all-participants")
print("Delete endpoint:", response.status_code, response.json() if response.status_code == 200 else response.text)