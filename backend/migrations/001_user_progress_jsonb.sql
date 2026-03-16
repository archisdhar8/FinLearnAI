-- =====================================================
-- Migration: user_progress table for backend (one row per user, JSONB progress)
-- Run in Supabase SQL Editor if your schema has the OLD per-lesson user_progress.
-- Backend expects: user_id (unique), progress_data (JSONB), updated_at.
-- =====================================================

-- Option A: If user_progress does NOT exist yet, create it
CREATE TABLE IF NOT EXISTS user_progress (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  progress_data JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id)
);

-- Option B: If you already have the OLD schema (one row per lesson), you can:
-- 1. Rename: ALTER TABLE user_progress RENAME TO user_progress_old;
-- 2. Run the CREATE TABLE above
-- 3. (Optional) Migrate data from user_progress_old into progress_data JSONB, then DROP user_progress_old

-- Ensure RLS and policy
ALTER TABLE user_progress ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all access to user_progress" ON user_progress;
CREATE POLICY "Allow all access to user_progress" ON user_progress
  FOR ALL USING (true) WITH CHECK (true);

-- Backend updates user_profiles.total_lessons_completed manually when saving progress,
-- so we do NOT need a trigger on user_progress for that.
