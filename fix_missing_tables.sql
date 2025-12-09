-- Fix missing chat_messages table and other missing tables
-- Run this on the production server if alembic upgrade fails

-- Create chat_messages table if it doesn't exist
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    chat_room_id INTEGER NOT NULL,
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_admin_message BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    reply_to_message_id INTEGER,
    CONSTRAINT chat_messages_chat_room_id_fkey FOREIGN KEY (chat_room_id)
        REFERENCES chat_rooms(id) ON DELETE CASCADE,
    CONSTRAINT fk_chat_messages_reply_to_message_id FOREIGN KEY (reply_to_message_id)
        REFERENCES chat_messages(id) ON DELETE SET NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_chat_messages_chat_room_id ON chat_messages(chat_room_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);

-- Verify tables exist
SELECT 'chat_messages table exists' as status WHERE EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'chat_messages'
);

SELECT 'chat_rooms table exists' as status WHERE EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'chat_rooms'
);
