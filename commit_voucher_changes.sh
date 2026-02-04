#!/bin/bash

# Navigate to the API directory
cd /d/development/msafiri-visitor-api

# Add all changes
git add .

# Commit the changes
git commit -m "Add voucher type support for multiple voucher allocations

- Add voucher_type and vouchers_per_participant fields to EventAllocation model
- Create migration 095_add_voucher_type_to_allocations.py
- Update API endpoints to handle multiple voucher types (drinks, t-shirts, notebooks, etc.)
- Maintain backward compatibility with existing drink_vouchers_per_participant field
- Update schemas to support new voucher type functionality
- Allow multiple voucher allocations per event with different types"

# Push to master
git push origin master

echo "Changes committed and pushed to master branch"
echo "You can now run the migration on the server with: alembic upgrade head"