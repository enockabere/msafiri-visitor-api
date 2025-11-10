# Absolute Cabs Integration Implementation

## Overview
This implementation provides complete integration with Absolute Cabs API for transport booking management in the MSF admin portal. It includes vehicle type selection, request pooling, and automated booking creation.

## Key Features

### 1. Absolute Cabs API Service (`app/services/absolute_cabs_service.py`)
- OAuth2 authentication with automatic token refresh
- HMAC-SHA256 request signing for security
- Vehicle types fetching
- Booking creation and management
- Error handling and logging

### 2. Enhanced Transport Request Endpoints
- **Vehicle Types**: `/transport-requests/tenant/{tenant_id}/vehicle-types`
- **Pooling Suggestions**: `/transport-requests/tenant/{tenant_id}/pooling-suggestions`
- **Pooled Booking**: `/transport-requests/pool-booking`
- **Enhanced Booking**: `/transport-requests/{request_id}/book-with-absolute-cabs`

### 3. Frontend Enhancements (`msf-admin-portal`)
- Vehicle type selection modal
- Request pooling interface with suggestions
- Bulk selection and actions
- Real-time pooling suggestions based on time and location proximity

## API Integration Details

### Authentication Flow
1. Client credentials OAuth2 flow
2. HMAC signature generation for each request
3. Automatic token refresh before expiry

### Booking Process
1. Admin selects transport request(s)
2. System shows available vehicle types from Absolute Cabs
3. Admin selects appropriate vehicle type
4. System creates booking via Absolute Cabs API
5. Booking reference is stored and status updated

### Pooling Algorithm
- Groups requests within 30-minute time windows
- Considers location proximity (2km pickup, 5km dropoff radius)
- Suggests appropriate vehicle types based on passenger count
- Fallback to address similarity matching

## Configuration

### Environment Variables
```env
# Add to .env file
FRONTEND_BASE_URL=http://localhost:3000
```

### Transport Provider Setup
1. Navigate to `/tenant/{slug}/transport-setup`
2. Enable Absolute Cabs integration
3. Configure API credentials:
   - Client ID
   - Client Secret
   - HMAC Secret
   - API Base URL
   - Token URL

## Usage Workflow

### Admin Portal
1. **View Requests**: Navigate to `/tenant/{slug}/transport`
2. **Individual Booking**:
   - Click "Book" on any pending request
   - Select vehicle type from modal
   - Confirm booking
3. **Pooled Booking**:
   - Select multiple requests using checkboxes
   - Click "Pool Selected" for automatic pooling
   - Or use "Pool Requests" button for suggestions
4. **Manual Confirmation**:
   - Click "Confirm" for manual driver assignment
   - Enter driver and vehicle details

### API Endpoints
```bash
# Get vehicle types
GET /api/v1/transport-requests/tenant/{tenant_id}/vehicle-types

# Get pooling suggestions
GET /api/v1/transport-requests/tenant/{tenant_id}/pooling-suggestions

# Create pooled booking
POST /api/v1/transport-requests/pool-booking
{
  "request_ids": [1, 2, 3],
  "vehicle_type": "Van",
  "notes": "Pooled booking"
}

# Book with Absolute Cabs
POST /api/v1/transport-requests/{request_id}/book-with-absolute-cabs
```

## Database Schema Updates

### Transport Request Model
- Added `booking_reference` field
- Enhanced status tracking
- Vehicle and driver details storage

### Transport Provider Model
- Secure credential storage
- Multi-tenant configuration
- Provider-specific settings

## Security Features
- HMAC request signing
- Encrypted credential storage
- Tenant isolation
- Permission-based access control

## Error Handling
- Graceful API failure handling
- Fallback to manual booking
- Comprehensive logging
- User-friendly error messages

## Testing
Run the test script to verify integration:
```bash
python test_absolute_integration.py
```

## Dependencies Added
- `geopy==2.4.1` - For distance calculations in pooling

## Future Enhancements
1. Real-time booking status updates
2. Driver tracking integration
3. Automated vehicle assignment optimization
4. Cost calculation and reporting
5. Integration with additional transport providers

## Troubleshooting

### Common Issues
1. **Authentication Failures**: Check API credentials in transport setup
2. **Booking Failures**: Verify Absolute Cabs API availability
3. **Pooling Not Working**: Ensure requests have location coordinates
4. **Vehicle Types Not Loading**: Check transport provider configuration

### Debug Mode
Enable debug logging in the service for detailed API interaction logs.