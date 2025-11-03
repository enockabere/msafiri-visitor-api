from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import requests
import os
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.tenant import Tenant
from app.models.event import Event

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
    event_id: Optional[int] = Query(None, description="Event ID for country filtering"),
    country: Optional[str] = Query(None, description="Country code override"),
    types: Optional[str] = Query("establishment", description="Place types"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[PlaceAutocompleteResponse]:
    """
    Google Places Autocomplete API proxy for mobile app.
    Use 'country' parameter to filter results by country code.
    """
    print(f"🔍 [Google Maps API] Autocomplete request - input: '{input}', user: {current_user.email}")
    
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    print(f"🔑 [Google Maps API] API key exists: {api_key is not None}")
    if api_key:
        print(f"🔑 [Google Maps API] API key preview: {api_key[:20]}...")
    
    if not api_key:
        print("❌ [Google Maps API] No API key found in environment")
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    # Get country from event if event_id provided
    filter_country = country
    if event_id and not country:
        event = db.query(Event).filter(Event.id == event_id).first()
        if event and event.country:
            filter_country = _get_country_code(event.country)
    
    print(f"🌍 [Google Maps API] Filter country: {filter_country}")
    
    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": input,
        "key": api_key,
        "types": types
    }
    
    if filter_country:
        params["components"] = f"country:{filter_country}"
        print(f"🌍 [Google Maps API] Filtering places by country: {filter_country}")
    
    try:
        print(f"🌐 [Google Maps API] Making request to: {url}")
        print(f"🌐 [Google Maps API] Request params: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        print(f"📊 [Google Maps API] Response status: {response.status_code}")
        
        response.raise_for_status()
        data = response.json()
        
        print(f"📊 [Google Maps API] Google API status: {data.get('status')}")
        print(f"📊 [Google Maps API] Predictions count: {len(data.get('predictions', []))}")
        
        if data.get("status") != "OK":
            print(f"❌ [Google Maps API] Google API error: {data.get('status')} - {data.get('error_message', 'No error message')}")
            raise HTTPException(status_code=400, detail=f"Google API error: {data.get('status')}")
        
        results = []
        for prediction in data.get("predictions", []):
            results.append(PlaceAutocompleteResponse(
                place_id=prediction["place_id"],
                description=prediction["description"],
                structured_formatting=prediction.get("structured_formatting", {})
            ))
        
        print(f"✅ [Google Maps API] Returning {len(results)} results")
        return results
        
    except requests.RequestException as e:
        print(f"❌ [Google Maps API] Request exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch places: {str(e)}")
    except Exception as e:
        print(f"❌ [Google Maps API] Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

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
    event_id: Optional[int] = Query(None, description="Event ID for country filtering"),
    country: Optional[str] = Query(None, description="Country code override"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> GeocodingResponse:
    """
    Google Forward Geocoding API proxy for mobile app.
    Use 'country' parameter to filter results by country code.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    # Get country from event if event_id provided
    filter_country = country
    if event_id and not country:
        event = db.query(Event).filter(Event.id == event_id).first()
        if event and event.country:
            filter_country = _get_country_code(event.country)
    
    print(f"🌍 [Google Maps API] Forward geocoding - Filter country: {filter_country}")
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": api_key
    }
    
    if filter_country:
        params["components"] = f"country:{filter_country}"
        print(f"🌍 [Google Maps API] Filtering geocoding by country: {filter_country}")
    
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

def _get_country_code(country_name: str) -> str:
    """Convert country name to ISO country code for Google Maps API"""
    print(f"🗺️ [Google Maps API] Converting country name: '{country_name}'")
    country_map = {
        "Kenya": "ke",
        "Uganda": "ug",
        "Tanzania": "tz",
        "Rwanda": "rw",
        "Burundi": "bi",
        "Ethiopia": "et",
        "Somalia": "so",
        "South Sudan": "ss",
        "Sudan": "sd",
        "Democratic Republic of the Congo": "cd",
        "Central African Republic": "cf",
        "Chad": "td",
        "Cameroon": "cm",
        "Nigeria": "ng",
        "Niger": "ne",
        "Mali": "ml",
        "Burkina Faso": "bf",
        "Ghana": "gh",
        "Ivory Coast": "ci",
        "Liberia": "lr",
        "Sierra Leone": "sl",
        "Guinea": "gn",
        "Senegal": "sn",
        "Mauritania": "mr",
        "Morocco": "ma",
        "Algeria": "dz",
        "Tunisia": "tn",
        "Libya": "ly",
        "Egypt": "eg",
        "South Africa": "za",
        "Mozambique": "mz",
        "Zimbabwe": "zw",
        "Zambia": "zm",
        "Malawi": "mw",
        "Botswana": "bw",
        "Namibia": "na",
        "Angola": "ao",
        "Madagascar": "mg",
        "Mauritius": "mu",
        "Seychelles": "sc",
        "Comoros": "km",
        "Djibouti": "dj",
        "Eritrea": "er",
        "Gabon": "ga",
        "Equatorial Guinea": "gq",
        "São Tomé and Príncipe": "st",
        "Republic of the Congo": "cg",
        "Lesotho": "ls",
        "Eswatini": "sz",
        "Afghanistan": "af",
        "Pakistan": "pk",
        "India": "in",
        "Bangladesh": "bd",
        "Sri Lanka": "lk",
        "Nepal": "np",
        "Bhutan": "bt",
        "Maldives": "mv",
        "Myanmar": "mm",
        "Thailand": "th",
        "Vietnam": "vn",
        "Cambodia": "kh",
        "Laos": "la",
        "Malaysia": "my",
        "Singapore": "sg",
        "Indonesia": "id",
        "Philippines": "ph",
        "Brunei": "bn",
        "East Timor": "tl",
        "Papua New Guinea": "pg",
        "Australia": "au",
        "New Zealand": "nz",
        "United States": "us",
        "Canada": "ca",
        "Mexico": "mx",
        "Brazil": "br",
        "Argentina": "ar",
        "Chile": "cl",
        "Colombia": "co",
        "Peru": "pe",
        "Venezuela": "ve",
        "Ecuador": "ec",
        "Bolivia": "bo",
        "Paraguay": "py",
        "Uruguay": "uy",
        "Guyana": "gy",
        "Suriname": "sr",
        "French Guiana": "gf",
        "United Kingdom": "gb",
        "Ireland": "ie",
        "France": "fr",
        "Germany": "de",
        "Italy": "it",
        "Spain": "es",
        "Portugal": "pt",
        "Netherlands": "nl",
        "Belgium": "be",
        "Luxembourg": "lu",
        "Switzerland": "ch",
        "Austria": "at",
        "Poland": "pl",
        "Czech Republic": "cz",
        "Slovakia": "sk",
        "Hungary": "hu",
        "Slovenia": "si",
        "Croatia": "hr",
        "Bosnia and Herzegovina": "ba",
        "Serbia": "rs",
        "Montenegro": "me",
        "North Macedonia": "mk",
        "Albania": "al",
        "Greece": "gr",
        "Bulgaria": "bg",
        "Romania": "ro",
        "Moldova": "md",
        "Ukraine": "ua",
        "Belarus": "by",
        "Lithuania": "lt",
        "Latvia": "lv",
        "Estonia": "ee",
        "Finland": "fi",
        "Sweden": "se",
        "Norway": "no",
        "Denmark": "dk",
        "Iceland": "is",
        "Russia": "ru",
        "Turkey": "tr",
        "Cyprus": "cy",
        "Malta": "mt",
        "China": "cn",
        "Japan": "jp",
        "South Korea": "kr",
        "North Korea": "kp",
        "Mongolia": "mn",
        "Kazakhstan": "kz",
        "Uzbekistan": "uz",
        "Turkmenistan": "tm",
        "Kyrgyzstan": "kg",
        "Tajikistan": "tj",
        "Armenia": "am",
        "Azerbaijan": "az",
        "Georgia": "ge",
        "Iran": "ir",
        "Iraq": "iq",
        "Syria": "sy",
        "Lebanon": "lb",
        "Jordan": "jo",
        "Israel": "il",
        "Palestine": "ps",
        "Saudi Arabia": "sa",
        "Yemen": "ye",
        "Oman": "om",
        "United Arab Emirates": "ae",
        "Qatar": "qa",
        "Bahrain": "bh",
        "Kuwait": "kw"
    }
    result = country_map.get(country_name, country_name.lower()[:2])
    print(f"🗺️ [Google Maps API] Country code result: '{result}'")
    return result