-- ========================================
-- Update line_manager_recommendations table structure
-- Adds missing is_recommended column for compatibility
-- ========================================

-- Add is_recommended column (boolean field for simple yes/no recommendation)
ALTER TABLE line_manager_recommendations
ADD COLUMN IF NOT EXISTS is_recommended BOOLEAN DEFAULT NULL;

-- Add submitted_at column if it doesn't exist
ALTER TABLE line_manager_recommendations
ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_line_manager_recommendations_is_recommended
ON line_manager_recommendations(is_recommended);

-- Verify the columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'line_manager_recommendations'
ORDER BY ordinal_position;
