# File: app/api/v1/endpoints/inventory.py
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.inventory import Inventory
from app.schemas.inventory import InventoryCreate, InventoryUpdate, Inventory as InventorySchema

router = APIRouter()

@router.post("/", response_model=InventorySchema, operation_id="create_inventory_item")
def create_inventory_item(
    *,
    db: Session = Depends(get_db),
    item_in: InventoryCreate
) -> Any:
    """Create new inventory item"""
    
    # Handle tenant_id - could be int or string slug
    tenant_id = item_in.tenant_id
    if isinstance(tenant_id, str):
        if tenant_id.isdigit():
            tenant_id = int(tenant_id)
        else:
            from app.models.tenant import Tenant
            tenant = db.query(Tenant).filter(Tenant.slug == tenant_id).first()
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant not found")
            tenant_id = tenant.id
    
    item = Inventory(
        tenant_id=int(tenant_id),
        name=item_in.name,
        category=item_in.category,
        quantity=item_in.quantity,
        condition=item_in.condition,
        created_by="admin"
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return item

@router.get("/", response_model=List[InventorySchema], operation_id="get_inventory_items")
def get_inventory_items(
    *,
    db: Session = Depends(get_db),
    tenant: str = None,
    category: str = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get inventory items"""
    
    print(f"DEBUG INVENTORY: tenant={tenant}, category={category}")
    
    try:
        query = db.query(Inventory)
        print(f"DEBUG INVENTORY: Base query created")
        
        if tenant:
            print(f"DEBUG INVENTORY: Processing tenant: {tenant}")
            # Convert tenant slug to tenant ID if needed
            tenant_id = tenant
            if not tenant.isdigit():
                from app.models.tenant import Tenant
                tenant_obj = db.query(Tenant).filter(Tenant.slug == tenant).first()
                print(f"DEBUG INVENTORY: Found tenant object: {tenant_obj}")
                if tenant_obj:
                    tenant_id = tenant_obj.id
                    print(f"DEBUG INVENTORY: Using tenant_id: {tenant_id}")
            query = query.filter(Inventory.tenant_id == str(tenant_id))
        
        if category:
            print(f"DEBUG INVENTORY: Filtering by category: {category}")
            query = query.filter(Inventory.category == category)
        
        items = query.offset(skip).limit(limit).all()
        print(f"DEBUG INVENTORY: Found {len(items)} items")
        for item in items:
            print(f"DEBUG INVENTORY: Item - ID: {item.id}, Name: {item.name}, Category: {item.category}, Tenant: {item.tenant_id}")
        
        return items
    except Exception as e:
        print(f"DEBUG INVENTORY ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching inventory: {str(e)}")

@router.put("/{item_id}", response_model=InventorySchema, operation_id="update_inventory_item")
def update_inventory_item(
    *,
    db: Session = Depends(get_db),
    item_id: int,
    item_update: InventoryUpdate
) -> Any:
    """Update inventory item"""
    
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Update fields
    update_data = item_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    db.commit()
    db.refresh(item)
    
    return item

@router.delete("/{item_id}", operation_id="delete_inventory_item")
def delete_inventory_item(
    *,
    db: Session = Depends(get_db),
    item_id: int
) -> Any:
    """Delete inventory item"""
    
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.is_active = False
    db.commit()
    
    return {"message": "Item deleted successfully"}