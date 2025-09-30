from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.event_speaker import EventSpeaker
from app.schemas.event_speaker import EventSpeakerCreate, EventSpeakerUpdate, EventSpeaker as EventSpeakerSchema
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=EventSpeakerSchema)
def create_speaker(
    speaker: EventSpeakerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_speaker = EventSpeaker(
        **speaker.dict(),
        created_by=current_user.email
    )
    db.add(db_speaker)
    db.commit()
    db.refresh(db_speaker)
    return db_speaker

@router.get("/{event_id}", response_model=List[EventSpeakerSchema])
def get_event_speakers(event_id: int, db: Session = Depends(get_db)):
    return db.query(EventSpeaker).filter(EventSpeaker.event_id == event_id).all()

@router.put("/{speaker_id}", response_model=EventSpeakerSchema)
def update_speaker(
    speaker_id: int,
    speaker_update: EventSpeakerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_speaker = db.query(EventSpeaker).filter(EventSpeaker.id == speaker_id).first()
    if not db_speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")
    
    for field, value in speaker_update.dict(exclude_unset=True).items():
        setattr(db_speaker, field, value)
    
    db.commit()
    db.refresh(db_speaker)
    return db_speaker

@router.delete("/{speaker_id}")
def delete_speaker(
    speaker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["MT_ADMIN", "HR_ADMIN", "EVENT_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_speaker = db.query(EventSpeaker).filter(EventSpeaker.id == speaker_id).first()
    if not db_speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")
    
    db.delete(db_speaker)
    db.commit()
    return {"message": "Speaker deleted"}