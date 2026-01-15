-- Check the current schema of participant_certificates table
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 'participant_certificates'
ORDER BY ordinal_position;
