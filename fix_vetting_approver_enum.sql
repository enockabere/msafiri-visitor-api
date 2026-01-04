-- Add missing vetting roles to roletype enum
-- This fixes the error: invalid input value for enum roletype: "VETTING_APPROVER" and "VETTING_COMMITTEE"

ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_APPROVER';
ALTER TYPE roletype ADD VALUE IF NOT EXISTS 'VETTING_COMMITTEE';