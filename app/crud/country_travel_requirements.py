from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.country_travel_requirements import CountryTravelRequirement
from app.schemas.country_travel_requirements import CountryTravelRequirementCreate, CountryTravelRequirementUpdate

class CRUDCountryTravelRequirement(CRUDBase[CountryTravelRequirement, CountryTravelRequirementCreate, CountryTravelRequirementUpdate]):
    def get_by_tenant_and_country(
        self, db: Session, *, tenant_id: int, country: str
    ) -> Optional[CountryTravelRequirement]:
        return db.query(CountryTravelRequirement).filter(
            CountryTravelRequirement.tenant_id == tenant_id,
            CountryTravelRequirement.country == country
        ).first()
    
    def get_by_tenant(
        self, db: Session, *, tenant_id: int
    ) -> List[CountryTravelRequirement]:
        return db.query(CountryTravelRequirement).filter(
            CountryTravelRequirement.tenant_id == tenant_id
        ).all()
    
    def create_with_tenant(
        self, db: Session, *, obj_in: CountryTravelRequirementCreate, tenant_id: int, created_by: str
    ) -> CountryTravelRequirement:
        # Convert additional_requirements to JSON format
        additional_reqs = None
        if obj_in.additional_requirements:
            additional_reqs = [req.dict() for req in obj_in.additional_requirements]
        
        db_obj = CountryTravelRequirement(
            tenant_id=tenant_id,
            country=obj_in.country,
            visa_required=obj_in.visa_required,
            eta_required=obj_in.eta_required,
            passport_required=obj_in.passport_required,
            flight_ticket_required=obj_in.flight_ticket_required,
            additional_requirements=additional_reqs,
            created_by=created_by
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_with_user(
        self, db: Session, *, db_obj: CountryTravelRequirement, obj_in: CountryTravelRequirementUpdate, updated_by: str
    ) -> CountryTravelRequirement:
        update_data = obj_in.dict(exclude_unset=True)
        
        # Handle additional_requirements conversion
        if "additional_requirements" in update_data and update_data["additional_requirements"] is not None:
            update_data["additional_requirements"] = [req.dict() for req in update_data["additional_requirements"]]
        
        update_data["updated_by"] = updated_by
        return super().update(db, db_obj=db_obj, obj_in=update_data)

country_travel_requirement = CRUDCountryTravelRequirement(CountryTravelRequirement)