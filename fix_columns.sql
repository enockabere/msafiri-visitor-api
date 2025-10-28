-- Add missing columns to news_updates table
ALTER TABLE news_updates ADD COLUMN IF NOT EXISTS external_link VARCHAR(500);
ALTER TABLE news_updates ADD COLUMN IF NOT EXISTS content_type VARCHAR(20) DEFAULT 'text';
ALTER TABLE news_updates ADD COLUMN IF NOT EXISTS scheduled_publish_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE news_updates ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;