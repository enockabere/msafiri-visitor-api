-- Fix NULL current_approval_step values
UPDATE travel_requests 
SET current_approval_step = 0 
WHERE current_approval_step IS NULL;
