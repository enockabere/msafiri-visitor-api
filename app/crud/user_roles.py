# File: app/crud/user_roles.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user_roles import UserRole
from app.models.user import UserRole as UserRoleEnum

def get_user_roles(db: Session, user_id: int) -> List[UserRole]:
    """Get all roles for a user"""
    return db.query(UserRole).filter(UserRole.user_id == user_id).all()

def add_user_role(db: Session, user_id: int, role: UserRoleEnum, created_by: Optional[str] = None) -> UserRole:
    """Add a role to a user (if not already exists)"""
    existing = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role == role
    ).first()
    
    if existing:
        return existing
    
    user_role = UserRole(
        user_id=user_id,
        role=role
    )
    db.add(user_role)
    db.commit()
    db.refresh(user_role)
    return user_role

def remove_user_role(db: Session, user_id: int, role: UserRoleEnum) -> bool:
    """Remove a role from a user"""
    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role == role
    ).first()
    
    if user_role:
        db.delete(user_role)
        db.commit()
        return True
    return False

def has_role(db: Session, user_id: int, role: UserRoleEnum) -> bool:
    """Check if user has a specific role"""
    return db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role == role
    ).first() is not None

def get_user_role_names(db: Session, user_id: int) -> List[str]:
    """Get list of role names for a user"""
    roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    return [role.role.value for role in roles]
