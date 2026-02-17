-- Fix alembic version table to remove reference to deleted migration
DELETE FROM alembic_version WHERE version_num = '109_add_perdiem_approval_steps';
