@router.put("/vendor-event-setup/{setup_id}", response_model=schemas.VendorEventAccommodation)
def update_vendor_event_setup(
    setup_id: int,
    setup_data: schemas.VendorEventAccommodationUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Update event-specific accommodation setup for vendor hotel"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    from app.models.guesthouse import VendorEventAccommodation
    setup = db.query(VendorEventAccommodation).filter(
        VendorEventAccommodation.id == setup_id,
        VendorEventAccommodation.tenant_id == tenant_id
    ).first()
    
    if not setup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event setup not found"
        )
    
    # Check if reducing capacity below current occupants
    if setup_data.single_rooms is not None and setup_data.double_rooms is not None:
        new_capacity = setup_data.single_rooms + (setup_data.double_rooms * 2)
        if new_capacity < setup.current_occupants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reduce capacity below current occupants ({setup.current_occupants})"
            )
        setup.total_capacity = new_capacity
    
    # Update fields
    if setup_data.single_rooms is not None:
        setup.single_rooms = setup_data.single_rooms
    if setup_data.double_rooms is not None:
        setup.double_rooms = setup_data.double_rooms
    if setup_data.is_active is not None:
        setup.is_active = setup_data.is_active
    
    db.commit()
    db.refresh(setup)
    
    return setup

@router.delete("/vendor-event-setup/{setup_id}")
def delete_vendor_event_setup(
    setup_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(deps.get_current_user),
    tenant_context: str = Depends(deps.get_tenant_context),
) -> Any:
    """Delete event-specific accommodation setup for vendor hotel"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.MT_ADMIN, UserRole.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    tenant_id = get_tenant_id_from_context(db, tenant_context, current_user)
    
    from app.models.guesthouse import VendorEventAccommodation
    setup = db.query(VendorEventAccommodation).filter(
        VendorEventAccommodation.id == setup_id,
        VendorEventAccommodation.tenant_id == tenant_id
    ).first()
    
    if not setup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event setup not found"
        )
    
    # Check if setup has current occupants
    if setup.current_occupants > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete setup with current occupants ({setup.current_occupants})"
        )
    
    db.delete(setup)
    db.commit()
    
    return {"message": "Event setup deleted successfully"}