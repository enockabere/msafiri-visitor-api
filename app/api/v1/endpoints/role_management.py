from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from datetime import datetime
from app.db.database import get_db
from app.models.user_roles import UserRole, RoleChangeLog, RoleType
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

def has_role(user: User, role: RoleType, db: Session) -> bool:
    """Check if user has specific role"""
    return db.query(UserRole).filter(
        and_(
            UserRole.user_id == user.id,
            UserRole.role == role
        )
    ).first() is not None

def get_user_roles(user: User, db: Session) -> List[RoleType]:
    """Get all roles for user"""
    roles = db.query(UserRole).filter(
        UserRole.user_id == user.id
    ).all()
    return [role.role for role in roles]

def is_super_admin(user: User, db: Session) -> bool:
    """Check if user is super admin"""
    return has_role(user, RoleType.SUPER_ADMIN, db)

@router.post("/grant-role")
def grant_role(
    user_email: str,
    role: str,
    reason: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Super admin grants role to user"""
    if not is_super_admin(current_user, db):
        raise HTTPException(status_code=403, detail="Only super admins can grant roles")
    
    # Get target user
    target_user = db.query(User).filter(User.email == user_email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate role
    try:
        role_enum = RoleType(role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Check if user already has this role
    existing_role = db.query(UserRole).filter(
        and_(
            UserRole.user_id == target_user.id,
            UserRole.role == role_enum
        )
    ).first()
    
    if existing_role:
        raise HTTPException(status_code=400, detail="User already has this role")
    
    # Grant role
    user_role = UserRole(
        user_id=target_user.id,
        role=role_enum,
        granted_by=current_user.email,
        granted_at=datetime.now()
    )
    db.add(user_role)
    
    # Log the change
    change_log = RoleChangeLog(
        user_id=target_user.id,
        user_email=target_user.email,
        role=role_enum,
        action="granted",
        performed_by=current_user.email,
        reason=reason
    )
    db.add(change_log)
    
    # Update primary role if this is their first role or if it's SUPER_ADMIN
    if role_enum == RoleType.SUPER_ADMIN or target_user.role == RoleType.USER:
        target_user.role = role_enum
    
    db.commit()
    
    return {
        "message": f"Role {role} granted to {user_email}",
        "user_email": user_email,
        "role_granted": role,
        "granted_by": current_user.email,
        "granted_at": user_role.granted_at
    }

@router.post("/revoke-role")
def revoke_role(
    user_email: str,
    role: str,
    reason: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Super admin revokes role from user"""
    if not is_super_admin(current_user, db):
        raise HTTPException(status_code=403, detail="Only super admins can revoke roles")
    
    # Get target user
    target_user = db.query(User).filter(User.email == user_email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate role
    try:
        role_enum = RoleType(role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Prevent self-revocation of SUPER_ADMIN
    if (target_user.id == current_user.id and role_enum == RoleType.SUPER_ADMIN):
        raise HTTPException(status_code=400, detail="Cannot revoke your own SUPER_ADMIN role")
    
    # Find role
    user_role = db.query(UserRole).filter(
        and_(
            UserRole.user_id == target_user.id,
            UserRole.role == role_enum
        )
    ).first()
    
    if not user_role:
        raise HTTPException(status_code=400, detail="User does not have this role")
    
    # Revoke role
    user_role.is_active = False
    user_role.revoked_at = datetime.now()
    user_role.revoked_by = current_user.email
    
    # Log the change
    change_log = RoleChangeLog(
        user_id=target_user.id,
        user_email=target_user.email,
        role=role_enum,
        action="revoked",
        performed_by=current_user.email,
        reason=reason
    )
    db.add(change_log)
    
    # Update primary role if this was their primary role
    if target_user.role == role_enum:
        # Get remaining active roles
        remaining_roles = get_user_roles(target_user, db)
        if remaining_roles:
            # Set highest priority remaining role as primary
            priority_order = [RoleType.SUPER_ADMIN, RoleType.MT_ADMIN, RoleType.HR_ADMIN, RoleType.EVENT_ADMIN, RoleType.USER]
            for priority_role in priority_order:
                if priority_role in remaining_roles:
                    target_user.role = priority_role
                    break
        else:
            target_user.role = RoleType.USER
    
    db.commit()
    
    return {
        "message": f"Role {role} revoked from {user_email}",
        "user_email": user_email,
        "role_revoked": role,
        "revoked_by": current_user.email,
        "revoked_at": user_role.revoked_at
    }

@router.get("/user-roles/{user_email}")
def get_user_roles_endpoint(
    user_email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all roles for a user"""
    if not is_super_admin(current_user, db):
        # Users can only view their own roles
        if user_email != current_user.email:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    target_user = db.query(User).filter(User.email == user_email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get roles
    active_roles = db.query(UserRole).filter(
        UserRole.user_id == target_user.id
    ).all()
    
    roles_data = []
    for role in active_roles:
        roles_data.append({
            "role": role.role.value,
            "granted_by": role.granted_by,
            "granted_at": role.granted_at,
            "is_primary": target_user.role == role.role
        })
    
    return {
        "user_email": user_email,
        "primary_role": target_user.role.value,
        "all_roles": roles_data,
        "total_roles": len(roles_data)
    }

@router.get("/my-roles")
def get_my_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's roles"""
    return get_user_roles_endpoint(current_user.email, db, current_user)

@router.get("/role-changes/{user_email}")
def get_role_change_history(
    user_email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get role change history for user"""
    if not is_super_admin(current_user, db):
        raise HTTPException(status_code=403, detail="Only super admins can view role history")
    
    target_user = db.query(User).filter(User.email == user_email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    changes = db.query(RoleChangeLog).filter(
        RoleChangeLog.user_id == target_user.id
    ).order_by(RoleChangeLog.created_at.desc()).all()
    
    history = []
    for change in changes:
        history.append({
            "role": change.role.value,
            "action": change.action,
            "performed_by": change.performed_by,
            "reason": change.reason,
            "timestamp": change.created_at
        })
    
    return {
        "user_email": user_email,
        "role_changes": history
    }

@router.get("/all-users-roles")
def get_all_users_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get roles for all users in tenant"""
    if not is_super_admin(current_user, db):
        raise HTTPException(status_code=403, detail="Only super admins can view all user roles")
    
    # Get all users in tenant
    users = db.query(User).filter(
        and_(
            User.tenant_id == current_user.tenant_id,
            User.is_active == True
        )
    ).all()
    
    result = []
    for user in users:
        # Get user's roles
        user_roles = db.query(UserRole).filter(
            UserRole.user_id == user.id
        ).all()
        
        roles_list = [role.role.value for role in user_roles]
        
        result.append({
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "primary_role": user.role.value,
            "all_roles": roles_list,
            "total_roles": len(roles_list),
            "is_super_admin": RoleType.SUPER_ADMIN.value in roles_list
        })
    
    return result
