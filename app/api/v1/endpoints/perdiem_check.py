from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.perdiem_request import PerdiemRequest

router = APIRouter()

@router.get("/check-approver/{email}")
async def check_perdiem_approver(email: str, db: Session = Depends(get_db)):
    """Check if user email is designated as a per diem approver"""
    
    # Check if the email appears as an approver in any per diem requests
    approver_requests = db.query(PerdiemRequest).filter(
        PerdiemRequest.approver_email == email
    ).first()
    
    return {
        "email": email,
        "is_approver": approver_requests is not None
    }