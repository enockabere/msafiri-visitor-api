from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
from pydantic import BaseModel

router = APIRouter()

class FoodMenuCreate(BaseModel):
    day_number: int
    meal_type: str  # breakfast, lunch, dinner, snack
    menu_items: str
    dietary_notes: str = None

class FoodMenuUpdate(BaseModel):
    menu_items: str = None
    dietary_notes: str = None

@router.post("/", response_model=dict)
def create_food_menu(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    item_in: FoodMenuCreate
) -> Any:
    """Create food menu item"""
    
    # Create food menu item
    db.execute(
        text("INSERT INTO event_food_menu (event_id, day_number, meal_type, menu_items, dietary_notes, created_by) VALUES (:event_id, :day_number, :meal_type, :menu_items, :dietary_notes, :created_by)"),
        {"event_id": event_id, "day_number": item_in.day_number, "meal_type": item_in.meal_type, "menu_items": item_in.menu_items, "dietary_notes": item_in.dietary_notes, "created_by": "admin"}
    )
    db.commit()
    
    return {"message": "Food menu item created successfully"}

@router.get("/", response_model=List[dict])
def get_food_menu(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get food menu for event"""
    
    result = db.execute(
        text("SELECT id, day_number, meal_type, menu_items, dietary_notes, created_at FROM event_food_menu WHERE event_id = :event_id ORDER BY day_number, meal_type"),
        {"event_id": event_id}
    ).fetchall()
    
    return [
        {
            "id": row[0],
            "day_number": row[1],
            "meal_type": row[2],
            "menu_items": row[3],
            "dietary_notes": row[4],
            "created_at": row[5].isoformat() if row[5] else None
        }
        for row in result
    ]

@router.put("/{item_id}")
def update_food_menu(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    item_id: int,
    item_in: FoodMenuUpdate
) -> Any:
    """Update food menu item"""
    
    # Check if item exists
    existing = db.execute(
        text("SELECT id FROM event_food_menu WHERE id = :item_id AND event_id = :event_id"),
        {"item_id": item_id, "event_id": event_id}
    ).fetchone()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Food menu item not found")
    
    # Update item
    update_fields = []
    params = {"item_id": item_id, "event_id": event_id}
    
    if item_in.menu_items is not None:
        update_fields.append("menu_items = :menu_items")
        params["menu_items"] = item_in.menu_items
    
    if item_in.dietary_notes is not None:
        update_fields.append("dietary_notes = :dietary_notes")
        params["dietary_notes"] = item_in.dietary_notes
    
    if update_fields:
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        sql = f"UPDATE event_food_menu SET {', '.join(update_fields)} WHERE id = :item_id AND event_id = :event_id"
        db.execute(text(sql), params)
        db.commit()
    
    return {"message": "Food menu item updated successfully"}

@router.delete("/{item_id}")
def delete_food_menu(
    *,
    db: Session = Depends(get_db),
    event_id: int,
    item_id: int
) -> Any:
    """Delete food menu item"""
    
    result = db.execute(
        text("DELETE FROM event_food_menu WHERE id = :item_id AND event_id = :event_id"),
        {"item_id": item_id, "event_id": event_id}
    )
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Food menu item not found")
    
    db.commit()
    return {"message": "Food menu item deleted successfully"}

@router.get("/dietary-requirements", response_model=List[dict])
def get_dietary_requirements(
    *,
    db: Session = Depends(get_db),
    event_id: int
) -> Any:
    """Get dietary requirements for selected participants"""
    
    result = db.execute(
        text("""
            SELECT ep.participant_name, ep.participant_email, ep.dietary_requirements, ep.allergies 
            FROM event_participants ep 
            WHERE ep.event_id = :event_id 
            AND ep.status = 'selected' 
            AND (ep.dietary_requirements IS NOT NULL OR ep.allergies IS NOT NULL)
            ORDER BY ep.participant_name
        """),
        {"event_id": event_id}
    ).fetchall()
    
    return [
        {
            "participant_name": row[0],
            "participant_email": row[1],
            "dietary_requirements": row[2],
            "allergies": row[3]
        }
        for row in result
    ]