@echo off
echo Updating event_allocations table structure...
psql -h localhost -U postgres -d msafiri_visitor_db -f update_allocations_table.sql
echo Database update completed!
pause