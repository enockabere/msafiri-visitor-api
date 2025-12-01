# Chat Messages Deletion Fix

## Problem
When trying to delete an event from the web portal, the following error occurred:

```
Failed to delete event: (psycopg2.errors.NotNullViolation) null value in column "chat_room_id" violates not-null constraint 
DETAIL: Failing row contains (21, null, leonard.kiprop@oca.msf.org, Leonard Kiprop, Test, null, t, 2025-11-19 11:57:24.461848+03). 
[SQL: UPDATE chat_messages SET chat_room_id=%(chat_room_id)s WHERE chat_messages.id = %(chat_messages_id)s] 
[parameters: [{'chat_room_id': None, 'chat_messages_id': 21}, {'chat_room_id': None, 'chat_messages_id': 22}]]
```

## Root Cause
The issue was caused by improper foreign key constraint handling in the chat system:

1. **Chat Messages Table**: The `chat_room_id` column was defined as `NOT NULL` but without proper CASCADE DELETE
2. **Event Deletion Process**: When deleting an event, the system tried to delete associated chat rooms
3. **SQLAlchemy Behavior**: SQLAlchemy attempted to set `chat_room_id` to NULL in chat messages before deleting the chat room
4. **Constraint Violation**: This violated the NOT NULL constraint on `chat_room_id`

## Solution

### 1. Database Schema Fix
Created migration `fix_chat_messages_cascade_delete.py` to:
- Add `CASCADE DELETE` constraint on `chat_messages.chat_room_id` → `chat_rooms.id`
- Add `SET NULL` constraint on `chat_messages.reply_to_message_id` → `chat_messages.id` (self-referential)

### 2. Model Relationship Fix
Updated SQLAlchemy models:
- **ChatRoom**: Added `cascade="all, delete-orphan"` to messages relationship
- **Event**: Added chat_rooms relationship with cascade delete
- **ChatRoom**: Updated event relationship with proper back_populates

### 3. API Deletion Logic Fix
Simplified event deletion logic to rely on cascade relationships:
- Removed manual chat message deletion (now handled by CASCADE DELETE)
- Kept manual deletion only for records without proper cascade relationships
- Added better error logging and exception handling

## Files Changed

### API Files
- `app/models/chat.py` - Updated relationships with cascade delete
- `app/models/event.py` - Added chat_rooms relationship
- `app/api/v1/endpoints/events.py` - Simplified deletion logic
- `alembic/versions/fix_chat_messages_cascade_delete.py` - New migration

### Migration Files
- `run_chat_fix_migration.py` - Script to run the migration

## How to Apply the Fix

1. **Run the Migration**:
   ```bash
   cd /path/to/msafiri-visitor-api
   python run_chat_fix_migration.py
   ```

2. **Restart the API Server**:
   ```bash
   # Stop current server
   # Start server with updated models
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Test Event Deletion**:
   - Create a draft event in the web portal
   - Try to delete it
   - Should work without foreign key constraint errors

## Prevention
- All future foreign key relationships should specify appropriate CASCADE behavior
- Use `CASCADE DELETE` when child records should be deleted with parent
- Use `SET NULL` for optional references that should be cleared
- Always test deletion operations in development before deploying

## Verification
After applying the fix, event deletion should work properly:
1. Chat messages are automatically deleted when their chat room is deleted
2. Chat rooms are automatically deleted when their event is deleted
3. No foreign key constraint violations occur during event deletion