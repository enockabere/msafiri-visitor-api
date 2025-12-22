-- Delete all participants and related data
-- Run this SQL script in your database

-- Delete in correct order to avoid foreign key constraints
DELETE FROM line_manager_recommendations;
DELETE FROM form_responses;
DELETE FROM accommodation_allocations WHERE participant_id IS NOT NULL;
DELETE FROM participant_qr_codes;
DELETE FROM event_participants;

-- Show counts after deletion
SELECT 'line_manager_recommendations' as table_name, COUNT(*) as remaining_records FROM line_manager_recommendations
UNION ALL
SELECT 'form_responses', COUNT(*) FROM form_responses
UNION ALL
SELECT 'accommodation_allocations', COUNT(*) FROM accommodation_allocations WHERE participant_id IS NOT NULL
UNION ALL
SELECT 'participant_qr_codes', COUNT(*) FROM participant_qr_codes
UNION ALL
SELECT 'event_participants', COUNT(*) FROM event_participants;