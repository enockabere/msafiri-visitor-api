from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import requests
import os
from pydantic import BaseModel

router = APIRouter()

class PlaceAutocompleteResponse(BaseModel):
    place_id: str
    description: str
    structured_formatting: dict

class PlaceDetailsResponse(BaseModel):
    place_id: str
    name: str
    formatted_address: str
    latitude: float
    longitude: float
    types: List[str]

class GeocodingResponse(BaseModel):
    formatted_address: str
    latitude: float
    longitude: float
    place_id: str

@router.get("/places/autocomplete")
async def places_autocomplete(
    input: str = Query(..., description="Search query"),
    country: Optional[str] = Query(None, description="Country code (e.g., 'ke' for Kenya)"),
    types: Optional[str] = Query("establishment", description="Place types")
) -> List[PlaceAutocompleteResponse]:
    """
    Google Places Autocomplete API proxy for mobile app
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": input,
        "key": api_key,
        "types": types
    }
    
    if country:
        params["components"] = f"country:{country}"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            raise HTTPException(status_code=400, detail=f"Google API error: {data.get('status')}")
        
        results = []
        for prediction in data.get("predictions", []):
            results.append(PlaceAutocompleteResponse(
                place_id=prediction["place_id"],
                description=prediction["description"],
                structured_formatting=prediction.get("structured_formatting", {})
            ))
        
        return results
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch places: {str(e)}")

@router.get("/places/details/{place_id}")
async def place_details(place_id: str) -> PlaceDetailsResponse:
    """
    Google Places Details API proxy for mobile app
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "key": api_key,
        "fields": "place_id,name,formatted_address,geometry,types"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            raise HTTPException(status_code=400, detail=f"Google API error: {data.get('status')}")
        
        result = data.get("result", {})
        geometry = result.get("geometry", {}).get("location", {})
        
        return PlaceDetailsResponse(
            place_id=result["place_id"],
            name=result.get("name", ""),
            formatted_address=result.get("formatted_address", ""),
            latitude=geometry.get("lat", 0.0),
            longitude=geometry.get("lng", 0.0),
            types=result.get("types", [])
        )
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch place details: {str(e)}")

@router.get("/geocoding/reverse")
async def reverse_geocoding(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude")
) -> GeocodingResponse:
    """
    Google Reverse Geocoding API proxy for mobile app
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lng}",
        "key": api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            raise HTTPException(status_code=400, detail=f"Google API error: {data.get('status')}")
        
        results = data.get("results", [])
        if not results:
            raise HTTPException(status_code=404, detail="No address found for coordinates")
        
        result = results[0]
        geometry = result.get("geometry", {}).get("location", {})
        
        return GeocodingResponse(
            formatted_address=result.get("formatted_address", ""),
            latitude=geometry.get("lat", lat),
            longitude=geometry.get("lng", lng),
            place_id=result.get("place_id", "")
        )
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to reverse geocode: {str(e)}")

@router.get("/geocoding/forward")
async def forward_geocoding(
    address: str = Query(..., description="Address to geocode"),
    country: Optional[str] = Query(None, description="Country code (e.g., 'ke' for Kenya)")
) -> GeocodingResponse:
    """
    Google Forward Geocoding API proxy for mobile app
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": api_key
    }
    
    if country:
        params["components"] = f"country:{country}"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            raise HTTPException(status_code=400, detail=f"Google API error: {data.get('status')}")
        
        results = data.get("results", [])
        if not results:
            raise HTTPException(status_code=404, detail="Address not found")
        
        result = results[0]
        geometry = result.get("geometry", {}).get("location", {})
        
        return GeocodingResponse(
            formatted_address=result.get("formatted_address", ""),
            latitude=geometry.get("lat", 0.0),
            longitude=geometry.get("lng", 0.0),
            place_id=result.get("place_id", "")
        )
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to geocode address: {str(e)}")