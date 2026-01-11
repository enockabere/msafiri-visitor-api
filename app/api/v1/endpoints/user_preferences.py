from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.user_preferences import UserPreferences
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()

class PreferenceUpdate(BaseModel):
    key: str
    value: Any

class SetupWizardDismissed(BaseModel):
    dismissed: bool

@router.get("/my-preferences")
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's preferences"""
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not preferences:
        return {"preferences": {}}
    
    return {"preferences": preferences.preferences}

@router.post("/my-preferences")
async def update_user_preference(
    preference: PreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific user preference"""
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not preferences:
        preferences = UserPreferences(
            user_id=current_user.id,
            preferences={preference.key: preference.value}
        )
        db.add(preferences)
    else:
        if preferences.preferences is None:
            preferences.preferences = {}
        preferences.preferences[preference.key] = preference.value
    
    db.commit()
    db.refresh(preferences)
    
    return {"message": "Preference updated successfully", "preferences": preferences.preferences}

@router.get("/setup-wizard-dismissed")
async def get_setup_wizard_dismissed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get setup wizard dismissed status for current user"""
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not preferences or not preferences.preferences:
        return {"dismissed": False}
    
    return {"dismissed": preferences.preferences.get("setup_wizard_dismissed", False)}

@router.post("/setup-wizard-dismissed")
async def set_setup_wizard_dismissed(
    data: SetupWizardDismissed,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set setup wizard dismissed status for current user"""
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not preferences:
        preferences = UserPreferences(
            user_id=current_user.id,
            preferences={"setup_wizard_dismissed": data.dismissed}
        )
        db.add(preferences)
    else:
        if preferences.preferences is None:
            preferences.preferences = {}
        preferences.preferences["setup_wizard_dismissed"] = data.dismissed
    
    db.commit()
    db.refresh(preferences)
    
    return {"message": "Setup wizard preference updated successfully", "dismissed": data.dismissed}