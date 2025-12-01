from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.participant_cleanup_service import ParticipantCleanupService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/cleanup/participants")
async def manual_participant_cleanup(db: Session = Depends(get_db)):
    """Manually trigger participant cleanup (admin only)"""
    try:
        deleted_count = ParticipantCleanupService.cleanup_expired_participants(db)
        
        return {
            "message": f"Cleanup completed successfully",
            "deleted_participants": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Manual cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@router.get("/cleanup/participants/preview")
async def preview_participant_cleanup(db: Session = Depends(get_db)):
    """Preview participants that would be deleted (admin only)"""
    try:
        from datetime import datetime, timedelta
        from app.models.event_participant import EventParticipant
        
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        participants_to_delete = db.query(EventParticipant).filter(
            EventParticipant.status.in_(["not_selected", "canceled", "declined"]),
            EventParticipant.updated_at <= cutoff_time
        ).all()
        
        preview_data = []
        for p in participants_to_delete:
            preview_data.append({
                "id": p.id,
                "email": p.email,
                "full_name": p.full_name,
                "status": p.status,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "event_id": p.event_id
            })
        
        return {
            "participants_to_delete": len(preview_data),
            "cutoff_time": cutoff_time.isoformat(),
            "participants": preview_data
        }
        
    except Exception as e:
        logger.error(f"Preview cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")