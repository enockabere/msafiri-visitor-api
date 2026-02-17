-- Delete all existing bank accounts (they were encrypted with wrong key format)
-- Users will need to re-add their bank accounts
DELETE FROM user_bank_accounts;
