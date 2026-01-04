-- Add VETTING_APPROVER to roletype enum
-- This fixes the error: invalid input value for enum roletype: "VETTING_APPROVER"

ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_APPROVER';