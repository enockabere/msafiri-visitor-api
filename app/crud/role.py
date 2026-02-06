# File: app/crud/role.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate

class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    
    def get_by_tenant(self, db: Session, *, tenant_id: str, skip: int = 0, limit: int = 100) -> List[Role]:
        return (
            db.query(Role)
            .filter(Role.tenant_id == tenant_id, Role.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_name_and_tenant(self, db: Session, *, name: str, tenant_id: str) -> Optional[Role]:
        return db.query(Role).filter(
            Role.name == name, 
            Role.tenant_id == tenant_id,
            Role.is_active == True
        ).first()

role = CRUDRole(Role)
