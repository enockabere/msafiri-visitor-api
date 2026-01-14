# Certificate Scheduling and Distribution System

## Overview
This document describes the new certificate scheduling and distribution system that provides granular control over when and to whom certificates are distributed.

## Key Features

### 1. **Manual Participant Selection**
- Certificates are NO LONGER automatically assigned to all participants
- Admins must explicitly select which participants receive certificates
- Only confirmed participants can be assigned certificates
- Supports bulk selection or individual selection

### 2. **Scheduled Distribution**
- Certificates have a `certificate_date` field that controls when they become visible
- Certificates remain hidden on the mobile app until the certificate date is reached
- Automatic publishing happens via scheduled task

### 3. **Email Notifications**
- Participants receive email notifications when certificates become available
- Emails are sent automatically on the certificate date
- Email tracking prevents duplicate notifications

### 4. **Publication Control**
- Certificates have an `is_published` flag
- Admins can manually publish certificates or let them auto-publish on certificate_date
- Unpublished certificates are never visible on mobile app

## Database Schema Changes

### EventCertificate Table
```sql
- certificate_date: DateTime (nullable) - When certificate becomes available
- is_published: Boolean (default: false) - Controls visibility
```

### ParticipantCertificate Table
```sql
- email_sent: Boolean (default: false) - Tracks if notification was sent
- email_sent_at: DateTime (nullable) - When notification was sent
```

## API Endpoints

### 1. Create Certificate (Modified)
```
POST /api/v1/events/{event_id}/certificates
```
**Changes:**
- No longer auto-assigns to all participants
- Accepts `certificate_date` in request body
- Sets `is_published = false` by default

**Request Body:**
```json
{
  "certificate_template_id": 1,
  "template_variables": {
    "organizerName": "John Doe",
    "organizerTitle": "Director",
    "facilitatorName": "Jane Smith",
    "facilitatorTitle": "Trainer",
    "coordinatorName": "Bob Wilson",
    "coordinatorTitle": "Coordinator",
    "certificateDate": "December 15, 2024",
    "courseDescription": "...",
    "courseObjectives": "...",
    "courseContents": "..."
  },
  "certificate_date": "2024-12-15T10:00:00Z"
}
```

### 2. Assign Participants (Modified)
```
POST /api/v1/events/{event_id}/certificates/{certificate_id}/assign-participants
```
**Changes:**
- Now accepts list of participant IDs
- Only assigns to confirmed participants
- Does NOT publish immediately

**Request Body:**
```json
{
  "participant_ids": [1, 2, 3, 4, 5]
}
```

**Response:**
```json
{
  "message": "Successfully assigned certificate to 5 confirmed participants",
  "participants_assigned": 5,
  "note": "Certificates will be visible on certificate_date and emails will be sent automatically"
}
```

### 3. Publish Certificate (New)
```
POST /api/v1/events/{event_id}/certificates/{certificate_id}/publish
```
**Purpose:** Manually publish certificate before certificate_date

**Response:**
```json
{
  "message": "Certificate published successfully",
  "participants_count": 5,
  "certificate_date": "2024-12-15T10:00:00Z",
  "note": "Certificate will be visible to participants on 2024-12-15 10:00"
}
```

### 4. Get Participant Certificate (Modified)
```
GET /api/v1/events/{event_id}/certificates/participant/{participant_id}
```
**Changes:**
- Only returns certificates where `is_published = true`
- Checks if `certificate_date` has been reached
- Returns 404 if certificate not yet available

## Scheduled Task

### Certificate Publisher
**File:** `app/tasks/certificate_publisher.py`

**Purpose:**
- Runs every hour (configure via cron/scheduler)
- Finds certificates where `certificate_date` has been reached
- Publishes certificates (`is_published = true`)
- Sends email notifications to participants
- Tracks email delivery status

**Setup (Linux/Mac):**
```bash
# Add to crontab
0 * * * * cd /path/to/api && /path/to/venv/bin/python -m app.tasks.certificate_publisher
```

**Setup (Windows):**
```powershell
# Create scheduled task
schtasks /create /tn "CertificatePublisher" /tr "python app\tasks\certificate_publisher.py" /sc hourly
```

## Admin Portal Workflow

### Step 1: Design Certificate Template
1. Navigate to: `/portal/tenant/{slug}/setups/certificates/`
2. Create certificate template with placeholders
3. Save template

### Step 2: Create Event Certificate
1. Navigate to: `/portal/tenant/{slug}/events/`
2. Open event details modal
3. Go to "Certs & Badges" tab
4. Click "Add Certificate"
5. Select template
6. Fill in certificate details:
   - Organizer Name/Title (optional)
   - Facilitator Name/Title (optional)
   - Coordinator Name/Title (optional)
   - Certificate Date (when it becomes available)
   - Course Description
   - Course Objectives
   - Course Contents
7. Save certificate (NOT yet assigned to participants)

### Step 3: Assign Participants
1. Go to "Participants" tab in event details
2. Select participants who should receive certificate:
   - Select All Confirmed
   - Bulk Select
   - Individual Selection
3. Click "Assign Certificate"
4. Choose which certificate to assign
5. Confirm assignment

### Step 4: Publish (Optional)
- Certificates auto-publish on `certificate_date`
- OR manually publish immediately via "Publish Now" button

## Mobile App Behavior

### Before Certificate Date
- Certificate is NOT visible in Event Files screen
- API returns 404 for certificate requests

### On/After Certificate Date
- Certificate appears in Event Files screen
- Participant receives email notification
- Certificate can be viewed/downloaded
- QR code links to certificate verification

## Email Notification

Participants receive an email with:
- Congratulations message
- Event title
- Link to view certificate
- Instructions to access via mobile app

## Validation Rules

1. **Only Confirmed Participants:**
   - Only participants with `status = 'confirmed'` can be assigned certificates

2. **Certificate Date Validation:**
   - Certificate date must be in the future (optional)
   - If no date provided, certificate can be published immediately

3. **Publication Requirements:**
   - At least one participant must be assigned before publishing
   - Cannot unpublish once published

4. **Email Tracking:**
   - Each participant receives only ONE email notification
   - `email_sent` flag prevents duplicates

## Migration Steps

### 1. Run Database Migration
```bash
cd /path/to/msafiri-visitor-api
alembic upgrade head
```

### 2. Update Existing Certificates (Optional)
```sql
-- Set certificate_date for existing certificates
UPDATE event_certificates 
SET certificate_date = NOW() + INTERVAL '7 days',
    is_published = false
WHERE certificate_date IS NULL;

-- Or publish all existing certificates immediately
UPDATE event_certificates 
SET is_published = true
WHERE is_published = false;
```

### 3. Setup Scheduled Task
Configure cron job or Windows Task Scheduler to run certificate publisher hourly

### 4. Update Admin Portal UI
- Add participant selection UI in Participants tab
- Add "Assign Certificate" button
- Add certificate date picker in certificate form
- Add "Publish Now" button (optional)

## Testing Checklist

- [ ] Create certificate without auto-assigning participants
- [ ] Assign certificate to selected participants only
- [ ] Verify certificate NOT visible before certificate_date
- [ ] Verify certificate becomes visible on certificate_date
- [ ] Verify email notifications are sent
- [ ] Verify email tracking prevents duplicates
- [ ] Test manual publish functionality
- [ ] Test with empty signatory fields (optional fields)
- [ ] Verify mobile app shows/hides certificates correctly

## Troubleshooting

### Certificates Not Appearing on Mobile App
1. Check `is_published` flag in database
2. Verify `certificate_date` has been reached
3. Check participant has been assigned certificate
4. Verify participant status is 'confirmed'

### Emails Not Being Sent
1. Check scheduled task is running
2. Verify SMTP settings in `.env`
3. Check `email_sent` flag in database
4. Review logs in `certificate_publisher.py`

### Scheduled Task Not Running
1. Verify cron job configuration
2. Check Python path in cron command
3. Review system logs
4. Test manual execution: `python -m app.tasks.certificate_publisher`

## Future Enhancements

1. **Batch Email Sending:** Queue emails for better performance
2. **Certificate Revocation:** Allow admins to revoke certificates
3. **Certificate Expiry:** Add expiration dates to certificates
4. **Certificate Analytics:** Track views and downloads
5. **Custom Email Templates:** Allow customization of notification emails
6. **SMS Notifications:** Send SMS in addition to email
7. **Certificate Versioning:** Track certificate updates
