-- Check certificate status for event 11, certificate 6
SELECT 
    ec.id,
    ec.event_id,
    ec.is_published,
    ec.certificate_date,
    ec.created_at,
    COUNT(pc.id) as assigned_participants
FROM event_certificates ec
LEFT JOIN participant_certificates pc ON pc.event_certificate_id = ec.id
WHERE ec.event_id = 11 AND ec.id = 6
GROUP BY ec.id, ec.event_id, ec.is_published, ec.certificate_date, ec.created_at;
