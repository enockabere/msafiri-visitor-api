from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/")
async def get_guest_houses():
    """Stub endpoint for guest houses - returns empty list"""
    return []

@router.post("/")
async def create_guest_house():
    """Stub endpoint for creating guest houses - not implemented"""
    raise HTTPException(status_code=501, detail="Guest house functionality is not available")

@router.put("/{guest_house_id}")
async def update_guest_house(guest_house_id: int):
    """Stub endpoint for updating guest houses - not implemented"""
    raise HTTPException(status_code=501, detail="Guest house functionality is not available")

@router.delete("/{guest_house_id}")
async def delete_guest_house(guest_house_id: int):
    """Stub endpoint for deleting guest houses - not implemented"""
    raise HTTPException(status_code=501, detail="Guest house functionality is not available")