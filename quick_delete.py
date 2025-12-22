import requests
response = requests.delete("http://41.90.240.229:8000/api/v1/line-manager-recommendation/debug/delete-all-participants")
print(response.json())