-- Fix Certificate Visibility
-- Run this on the production server to hide certificates until their scheduled date

-- 1. Set all existing certificates to unpublished
UPDATE event_certificates 
SET is_published = false 
WHERE is_published = true OR is_published IS NULL;

-- 2. Verify the changes
SELECT 
    id, 
    event_id, 
    certificate_date,
    is_published,
    created_at
FROM event_certificates
ORDER BY created_at DESC;

-- 3. Check participant certificates (these should exist but won't be visible until published)
SELECT 
    pc.id,
    pc.participant_id,
    pc.event_certificate_id,
    ec.certificate_date,
    ec.is_published,
    pc.email_sent
FROM participant_certificates pc
JOIN event_certificates ec ON pc.event_certificate_id = ec.id
ORDER BY pc.id DESC
LIMIT 10;

-- NOTES:
-- - Certificates will remain hidden on mobile app until certificate_date is reached
-- - The scheduled task (certificate_publisher.py) will auto-publish them on the date
-- - Emails will be sent automatically when published
-- - To manually publish a certificate before the date, run:
--   UPDATE event_certificates SET is_published = true WHERE id = <certificate_id>;
