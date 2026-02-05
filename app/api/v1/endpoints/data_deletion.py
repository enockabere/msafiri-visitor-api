from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.data_deletion_service import DataDeletionService
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/data-deletion/pending")
async def get_pending_deletions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get participants whose data is pending deletion"""
    
    # Check if user has admin permissions
    if not current_user.role in ['SUPER_ADMIN', 'MT_ADMIN', 'HR_ADMIN']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    immediate_deletions = DataDeletionService.get_participants_for_immediate_deletion(db)
    monthly_deletions = DataDeletionService.get_participants_for_monthly_deletion(db)
    
    return {
        "immediate_deletions": {
            "count": len(immediate_deletions),
            "participants": immediate_deletions,
            "policy": "24 hours after status change to not_selected/canceled/declined"
        },
        "monthly_deletions": {
            "count": len(monthly_deletions),
            "participants": monthly_deletions,
            "policy": "30 days after event completion"
        }
    }

@router.post("/data-deletion/process")
async def process_data_deletions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger data deletion process"""
    
    # Check if user has admin permissions
    if not current_user.role in ['SUPER_ADMIN', 'MT_ADMIN']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    results = DataDeletionService.process_automatic_deletions(db)
    
    return {
        "message": "Data deletion process completed",
        "results": results,
        "processed_at": datetime.utcnow().isoformat()
    }

@router.get("/data-deletion/stats")
async def get_deletion_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get statistics about data deletion"""
    
    # Check if user has admin permissions
    if not current_user.role in ['SUPER_ADMIN', 'MT_ADMIN', 'HR_ADMIN']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    from sqlalchemy import text
    
    # Count already deleted participants
    deleted_count = db.execute(text("""
        SELECT COUNT(*) FROM event_participants 
        WHERE email LIKE 'deleted.%@data-protection.msf'
    """)).scalar()
    
    # Count participants approaching deletion
    approaching_immediate = len(DataDeletionService.get_participants_for_immediate_deletion(db))
    approaching_monthly = len(DataDeletionService.get_participants_for_monthly_deletion(db))
    
    return {
        "already_deleted": deleted_count,
        "pending_immediate_deletion": approaching_immediate,
        "pending_monthly_deletion": approaching_monthly,
        "policies": {
            "immediate": "Personal data deleted 24 hours after status change to not_selected/canceled/declined",
            "monthly": "Personal data deleted 30 days after event completion for all other participants",
            "audit_trail": "Participant records maintained for audit purposes with anonymized data"
        }
    }