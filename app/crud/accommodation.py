from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import date

from app.crud.base import CRUDBase
from app.models.guesthouse import GuestHouse, Room, VendorAccommodation, AccommodationAllocation
from app.schemas.accommodation import (
    GuestHouseCreate, GuestHouseUpdate,
    RoomCreate, RoomUpdate,
    VendorAccommodationCreate, VendorAccommodationUpdate,
    AccommodationAllocationCreate, AccommodationAllocationUpdate
)

class CRUDGuestHouse(CRUDBase[GuestHouse, GuestHouseCreate, GuestHouseUpdate]):
    def get_by_tenant(self, db: Session, *, tenant_id: int) -> List[GuestHouse]:
        return db.query(self.model).filter(self.model.tenant_id == tenant_id).all()

    def create_with_tenant(self, db: Session, *, obj_in: GuestHouseCreate, tenant_id: int, created_by: str = None) -> GuestHouse:
        obj_data = obj_in.dict()
        obj_data["tenant_id"] = tenant_id
        # Copy location to address for backward compatibility
        if obj_data.get("location"):
            obj_data["address"] = obj_data["location"]
        if created_by:
            obj_data["created_by"] = created_by
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

class CRUDRoom(CRUDBase[Room, RoomCreate, RoomUpdate]):
    def get_by_guesthouse(self, db: Session, *, guesthouse_id: int) -> List[Room]:
        return db.query(self.model).filter(self.model.guesthouse_id == guesthouse_id).all()

    def get_by_tenant(self, db: Session, *, tenant_id: int) -> List[Room]:
        return db.query(self.model).filter(self.model.tenant_id == tenant_id).all()

    def create_with_tenant(self, db: Session, *, obj_in: RoomCreate, tenant_id: int) -> Room:
        obj_data = obj_in.dict()
        obj_data["tenant_id"] = tenant_id
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_available_rooms(self, db: Session, *, guesthouse_id: int, check_in: date, check_out: date) -> List[Room]:
        # Get rooms that are not allocated during the specified period
        occupied_room_ids = db.query(AccommodationAllocation.room_id).filter(
            and_(
                AccommodationAllocation.room_id.isnot(None),
                AccommodationAllocation.status.in_(["booked", "checked_in"]),
                AccommodationAllocation.check_in_date <= check_out,
                AccommodationAllocation.check_out_date >= check_in
            )
        ).subquery()
        
        return db.query(self.model).filter(
            and_(
                self.model.guesthouse_id == guesthouse_id,
                self.model.is_active == True,
                ~self.model.id.in_(occupied_room_ids)
            )
        ).all()

class CRUDVendorAccommodation(CRUDBase[VendorAccommodation, VendorAccommodationCreate, VendorAccommodationUpdate]):
    def get_by_tenant(self, db: Session, *, tenant_id: int) -> List[VendorAccommodation]:
        return db.query(self.model).filter(self.model.tenant_id == tenant_id).all()

    def create_with_tenant(self, db: Session, *, obj_in: VendorAccommodationCreate, tenant_id: int) -> VendorAccommodation:
        obj_data = obj_in.dict()
        obj_data["tenant_id"] = tenant_id
        
        # Calculate capacity from room counts if not provided
        if "capacity" not in obj_data or obj_data["capacity"] == 0:
            single_rooms = obj_data.get("single_rooms", 0)
            double_rooms = obj_data.get("double_rooms", 0)
            obj_data["capacity"] = single_rooms + (double_rooms * 2)
        
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

class CRUDAccommodationAllocation(CRUDBase[AccommodationAllocation, AccommodationAllocationCreate, AccommodationAllocationUpdate]):
    def get_by_tenant(self, db: Session, *, tenant_id: int) -> List[AccommodationAllocation]:
        return db.query(self.model).filter(self.model.tenant_id == tenant_id).all()

    def get_by_tenant_and_event(self, db: Session, *, tenant_id: int, event_id: int) -> List[AccommodationAllocation]:
        return db.query(self.model).filter(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.event_id == event_id
            )
        ).all()

    def create_with_tenant(self, db: Session, *, obj_in: AccommodationAllocationCreate, tenant_id: int, user_id: int) -> AccommodationAllocation:
        obj_data = obj_in.dict()
        obj_data["tenant_id"] = tenant_id
        obj_data["created_by"] = user_id
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        # Update occupancy counts
        self._update_occupancy_counts(db, db_obj)
        
        return db_obj

    def update_allocation(self, db: Session, *, db_obj: AccommodationAllocation, obj_in: AccommodationAllocationUpdate) -> AccommodationAllocation:
        old_room_id = db_obj.room_id
        old_vendor_id = db_obj.vendor_accommodation_id
        old_guests = db_obj.number_of_guests
        
        # Update the allocation
        updated_obj = super().update(db_obj=db_obj, obj_in=obj_in)
        db.commit()
        db.refresh(updated_obj)
        
        # Update occupancy counts for old and new accommodations
        if old_room_id != updated_obj.room_id or old_vendor_id != updated_obj.vendor_accommodation_id or old_guests != updated_obj.number_of_guests:
            self._update_occupancy_counts(db, updated_obj, old_room_id, old_vendor_id, old_guests)
        
        return updated_obj

    def _update_occupancy_counts(self, db: Session, allocation: AccommodationAllocation, old_room_id: Optional[int] = None, old_vendor_id: Optional[int] = None, old_guests: Optional[int] = None):
        # Update room occupancy
        if allocation.room_id:
            room = db.query(Room).filter(Room.id == allocation.room_id).first()
            if room:
                active_allocations = db.query(func.sum(AccommodationAllocation.number_of_guests)).filter(
                    and_(
                        AccommodationAllocation.room_id == room.id,
                        AccommodationAllocation.status.in_(["booked", "checked_in"])
                    )
                ).scalar() or 0
                room.current_occupants = active_allocations
                room.is_occupied = active_allocations > 0
                
        # Update vendor accommodation occupancy
        if allocation.vendor_accommodation_id:
            vendor = db.query(VendorAccommodation).filter(VendorAccommodation.id == allocation.vendor_accommodation_id).first()
            if vendor:
                active_allocations = db.query(func.sum(AccommodationAllocation.number_of_guests)).filter(
                    and_(
                        AccommodationAllocation.vendor_accommodation_id == vendor.id,
                        AccommodationAllocation.status.in_(["booked", "checked_in"])
                    )
                ).scalar() or 0
                vendor.current_occupants = active_allocations
                
        # Update old room/vendor if changed
        if old_room_id and old_room_id != allocation.room_id:
            old_room = db.query(Room).filter(Room.id == old_room_id).first()
            if old_room:
                active_allocations = db.query(func.sum(AccommodationAllocation.number_of_guests)).filter(
                    and_(
                        AccommodationAllocation.room_id == old_room.id,
                        AccommodationAllocation.status.in_(["booked", "checked_in"])
                    )
                ).scalar() or 0
                old_room.current_occupants = active_allocations
                old_room.is_occupied = active_allocations > 0
                
        if old_vendor_id and old_vendor_id != allocation.vendor_accommodation_id:
            old_vendor = db.query(VendorAccommodation).filter(VendorAccommodation.id == old_vendor_id).first()
            if old_vendor:
                active_allocations = db.query(func.sum(AccommodationAllocation.number_of_guests)).filter(
                    and_(
                        AccommodationAllocation.vendor_accommodation_id == old_vendor.id,
                        AccommodationAllocation.status.in_(["booked", "checked_in"])
                    )
                ).scalar() or 0
                old_vendor.current_occupants = active_allocations
                
        db.commit()

    def get_active_allocations(self, db: Session, *, tenant_id: int) -> List[AccommodationAllocation]:
        return db.query(self.model).filter(
            and_(
                self.model.tenant_id == tenant_id,
                self.model.status.in_(["booked", "checked_in"])
            )
        ).all()

    def remove(self, db: Session, *, id: int) -> AccommodationAllocation:
        # Get the allocation before deleting to update occupancy counts
        allocation = db.query(self.model).get(id)
        if allocation:
            old_room_id = allocation.room_id
            old_vendor_id = allocation.vendor_accommodation_id
            old_guests = allocation.number_of_guests
            
            # Delete the allocation
            db.delete(allocation)
            db.commit()
            
            # Update occupancy counts after deletion
            if old_room_id:
                room = db.query(Room).filter(Room.id == old_room_id).first()
                if room:
                    active_allocations = db.query(func.sum(AccommodationAllocation.number_of_guests)).filter(
                        and_(
                            AccommodationAllocation.room_id == room.id,
                            AccommodationAllocation.status.in_(["booked", "checked_in"])
                        )
                    ).scalar() or 0
                    room.current_occupants = active_allocations
                    room.is_occupied = active_allocations > 0
                    
            if old_vendor_id:
                vendor = db.query(VendorAccommodation).filter(VendorAccommodation.id == old_vendor_id).first()
                if vendor:
                    active_allocations = db.query(func.sum(AccommodationAllocation.number_of_guests)).filter(
                        and_(
                            AccommodationAllocation.vendor_accommodation_id == vendor.id,
                            AccommodationAllocation.status.in_(["booked", "checked_in"])
                        )
                    ).scalar() or 0
                    vendor.current_occupants = active_allocations
                    
            db.commit()
            
        return allocation

# Create instances
guesthouse = CRUDGuestHouse(GuestHouse)
room = CRUDRoom(Room)
vendor_accommodation = CRUDVendorAccommodation(VendorAccommodation)
accommodation_allocation = CRUDAccommodationAllocation(AccommodationAllocation)