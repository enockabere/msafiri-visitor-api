from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.transport_provider import TransportProvider
from app.schemas.transport_provider import TransportProviderCreate, TransportProviderUpdate

class CRUDTransportProvider(CRUDBase[TransportProvider, TransportProviderCreate, TransportProviderUpdate]):
    def get_by_tenant_and_provider(
        self, db: Session, *, tenant_id: int, provider_name: str
    ) -> Optional[TransportProvider]:
        return db.query(TransportProvider).filter(
            TransportProvider.tenant_id == tenant_id,
            TransportProvider.provider_name == provider_name
        ).first()
    
    def get_by_tenant(
        self, db: Session, *, tenant_id: int
    ) -> List[TransportProvider]:
        return db.query(TransportProvider).filter(
            TransportProvider.tenant_id == tenant_id
        ).all()
    
    def create_with_tenant(
        self, db: Session, *, obj_in: TransportProviderCreate, tenant_id: int, created_by: str
    ) -> TransportProvider:
        db_obj = TransportProvider(
            tenant_id=tenant_id,
            provider_name=obj_in.provider_name,
            is_enabled=obj_in.is_enabled,
            client_id=obj_in.client_id,
            client_secret=obj_in.client_secret,
            hmac_secret=obj_in.hmac_secret,
            api_base_url=obj_in.api_base_url,
            token_url=obj_in.token_url,
            created_by=created_by
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

transport_provider = CRUDTransportProvider(TransportProvider)
