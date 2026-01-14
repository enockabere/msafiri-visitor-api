# Certificate Scheduling Implementation Summary

## What Was Changed

### 1. Database Changes
**File:** `alembic/versions/026_add_certificate_scheduling.py`
- Added `certificate_date` to `event_certificates` table
- Added `is_published` flag to `event_certificates` table
- Added `email_sent` and `email_sent_at` to `participant_certificates` table

### 2. Model Updates
**File:** `app/models/event_certificate.py`
- Added `certificate_date`, `is_published` fields to EventCertificate model
- Added `email_sent`, `email_sent_at` fields to ParticipantCertificate model

### 3. Schema Updates
**File:** `app/schemas/event_certificate.py`
- Added `certificate_date` to EventCertificateBase
- Added `is_published` to EventCertificateResponse
- Added `email_sent`, `email_sent_at` to ParticipantCertificateResponse
- Created new `AssignCertificatesRequest` schema for participant selection

### 4. API Endpoint Changes
**File:** `app/api/v1/endpoints/event_certificates.py`

**Modified:**
- `create_event_certificate()` - Removed auto-assignment to all participants
- `assign_participants_to_certificate()` - Now accepts list of participant IDs
- `get_event_participant_certificate()` - Checks publication status and certificate date

**Added:**
- `publish_certificate()` - Manually publish certificates

### 5. Email Service
**File:** `app/core/email_service.py`
- Added `send_certificate_notification_email()` function

### 6. Scheduled Task
**File:** `app/tasks/certificate_publisher.py`
- New scheduled task to auto-publish certificates and send emails

### 7. Documentation
**File:** `docs/CERTIFICATE_SCHEDULING.md`
- Complete documentation of the new system

## How It Works Now

### Old Flow (Before Changes)
```
1. Admin creates certificate
2. Certificate automatically assigned to ALL participants
3. Certificate immediately visible on mobile app
4. No email notifications
5. No control over distribution
```

### New Flow (After Changes)
```
1. Admin creates certificate with certificate_date
2. Admin selects specific participants (Participants tab)
3. Admin assigns certificate to selected participants
4. Certificate remains hidden until certificate_date
5. On certificate_date:
   - Scheduled task publishes certificate
   - Emails sent to all assigned participants
   - Certificate becomes visible on mobile app
6. Participants can view/download certificate
```

## What Needs to Be Done Next

### Backend (API) - COMPLETED ✅
- [x] Database migration
- [x] Model updates
- [x] Schema updates
- [x] API endpoint modifications
- [x] Email service
- [x] Scheduled task
- [x] Documentation

### Backend (Deployment) - TODO
- [ ] Run migration: `alembic upgrade head`
- [ ] Setup cron job for certificate publisher
- [ ] Test scheduled task execution
- [ ] Verify email sending works

### Frontend (Admin Portal) - TODO
- [ ] Update EventDetailsModal certificate form:
  - [ ] Add certificate_date DateTimePicker
  - [ ] Make Organizer/Facilitator/Coordinator optional
  - [ ] Remove auto-assignment logic
- [ ] Add participant selection UI in Participants tab:
  - [ ] Add checkboxes for participant selection
  - [ ] Add "Select All Confirmed" button
  - [ ] Add "Assign Certificate" button
  - [ ] Add certificate selection dropdown
- [ ] Add "Publish Now" button (optional)
- [ ] Update certificate list to show publication status

### Mobile App (Flutter) - NO CHANGES NEEDED ✅
- Current implementation already works correctly
- API changes are backward compatible
- Certificates will simply not appear until published

## Testing Steps

### 1. Test Certificate Creation
```bash
# Create certificate without participants
POST /api/v1/events/1/certificates
{
  "certificate_template_id": 1,
  "template_variables": {...},
  "certificate_date": "2024-12-20T10:00:00Z"
}

# Verify: is_published should be false
# Verify: No participant_certificates created
```

### 2. Test Participant Assignment
```bash
# Assign to specific participants
POST /api/v1/events/1/certificates/1/assign-participants
{
  "participant_ids": [1, 2, 3]
}

# Verify: Only 3 participant_certificates created
# Verify: Only for confirmed participants
```

### 3. Test Mobile App Access (Before Date)
```bash
# Try to get certificate before certificate_date
GET /api/v1/events/1/certificates/participant/1

# Expected: 404 Not Found
```

### 4. Test Manual Publishing
```bash
# Manually publish certificate
POST /api/v1/events/1/certificates/1/publish

# Verify: is_published = true
# Verify: Certificate now visible on mobile app
```

### 5. Test Scheduled Publishing
```bash
# Set certificate_date to past
UPDATE event_certificates SET certificate_date = NOW() - INTERVAL '1 hour' WHERE id = 1;

# Run scheduled task
python -m app.tasks.certificate_publisher

# Verify: is_published = true
# Verify: email_sent = true for all participants
# Verify: Emails received
```

## Cron Job Setup

### Linux/Mac
```bash
# Edit crontab
crontab -e

# Add this line (runs every hour)
0 * * * * cd /path/to/msafiri-visitor-api && /path/to/venv/bin/python -m app.tasks.certificate_publisher >> /var/log/certificate_publisher.log 2>&1
```

### Windows
```powershell
# Create scheduled task (runs every hour)
schtasks /create /tn "MSafiri Certificate Publisher" /tr "C:\path\to\python.exe C:\path\to\msafiri-visitor-api\app\tasks\certificate_publisher.py" /sc hourly /st 00:00
```

## Environment Variables

Make sure these are set in `.env`:
```env
# Email settings (required for notifications)
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your-email@msf.org
SMTP_PASSWORD=your-password
FROM_EMAIL=noreply@msf.org
FROM_NAME=MSF Msafiri
SEND_EMAILS=true

# Frontend URL (for email links)
FRONTEND_URL=http://41.90.17.25:3000/portal
NEXT_PUBLIC_API_URL=http://41.90.17.25:8000
```

## Database Migration

```bash
# Navigate to API directory
cd /path/to/msafiri-visitor-api

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Run migration
alembic upgrade head

# Verify migration
alembic current
# Should show: 026_certificate_scheduling
```

## Rollback Plan

If something goes wrong:

```bash
# Rollback database
alembic downgrade -1

# Revert code changes
git revert <commit-hash>

# Or manually set all certificates to published
UPDATE event_certificates SET is_published = true;
```

## Key Benefits

1. **Granular Control:** Admins choose exactly who gets certificates
2. **Scheduled Distribution:** Certificates appear at the right time
3. **Email Notifications:** Participants are notified automatically
4. **No Spam:** Participants only receive certificates they earned
5. **Professional:** Certificates distributed on official date
6. **Tracking:** Know when emails were sent
7. **Flexibility:** Can publish early if needed

## Important Notes

- **Backward Compatibility:** Existing certificates will need `is_published` set to `true` manually
- **Email Dependency:** Requires working SMTP configuration
- **Cron Job:** Must be set up for automatic publishing
- **Time Zones:** All dates are stored in UTC
- **Confirmed Only:** Only confirmed participants can receive certificates

## Next Steps

1. **Run Migration:** `alembic upgrade head`
2. **Setup Cron Job:** Configure scheduled task
3. **Update Frontend:** Add participant selection UI
4. **Test Thoroughly:** Follow testing steps above
5. **Deploy:** Push changes to production
6. **Monitor:** Check logs for scheduled task execution

## Questions?

Refer to `docs/CERTIFICATE_SCHEDULING.md` for detailed documentation.
