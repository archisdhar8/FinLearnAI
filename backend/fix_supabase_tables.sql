-- =====================================================
-- Run this in Supabase SQL Editor (https://supabase.com/dashboard)
-- Go to: SQL Editor → New Query → Paste this → Run
-- =====================================================

-- Step 1: Fix user_progress table
-- Drop the old FK that points to public.users and recreate pointing to auth.users
ALTER TABLE user_progress DROP CONSTRAINT IF EXISTS user_progress_user_id_fkey;
ALTER TABLE user_progress 
  ADD CONSTRAINT user_progress_user_id_fkey 
  FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- Step 2: Backfill public.users from auth.users (for any existing users)
INSERT INTO public.users (id, email, name, password_hash, password_salt, created_at)
SELECT 
  id, 
  email, 
  SPLIT_PART(email, '@', 1),
  'supabase_managed',
  'supabase_managed',
  NOW()
FROM auth.users
WHERE id NOT IN (SELECT id FROM public.users)
ON CONFLICT (id) DO NOTHING;

-- Step 3: Ensure user_profiles exist for all auth users
INSERT INTO user_profiles (user_id, display_name)
SELECT id, SPLIT_PART(email, '@', 1)
FROM auth.users
WHERE id NOT IN (SELECT user_id FROM user_profiles)
ON CONFLICT (user_id) DO NOTHING;

-- Step 4: Add open RLS policies so backend with anon key can write
-- (If you later add the service_role key, these become unnecessary 
-- because service_role bypasses RLS entirely)

-- user_progress
DROP POLICY IF EXISTS "Allow all access to user_progress" ON user_progress;
CREATE POLICY "Allow all access to user_progress" ON user_progress
  FOR ALL USING (true) WITH CHECK (true);

-- lesson_quiz_scores  
DROP POLICY IF EXISTS "Allow all access to lesson_quiz_scores" ON lesson_quiz_scores;
CREATE POLICY "Allow all access to lesson_quiz_scores" ON lesson_quiz_scores
  FOR ALL USING (true) WITH CHECK (true);

-- module_quiz_scores
DROP POLICY IF EXISTS "Allow all access to module_quiz_scores" ON module_quiz_scores;
CREATE POLICY "Allow all access to module_quiz_scores" ON module_quiz_scores
  FOR ALL USING (true) WITH CHECK (true);

-- user_profiles
DROP POLICY IF EXISTS "Allow all access to user_profiles" ON user_profiles;
CREATE POLICY "Allow all access to user_profiles" ON user_profiles
  FOR ALL USING (true) WITH CHECK (true);

-- public.users (needed for FK + trigger)
DROP POLICY IF EXISTS "Allow all access to public users" ON public.users;
CREATE POLICY "Allow all access to public users" ON public.users
  FOR ALL USING (true) WITH CHECK (true);

-- Step 5: Ensure trigger syncs new auth users to public.users
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email, name, password_hash, password_salt, created_at)
  VALUES (NEW.id, NEW.email, SPLIT_PART(NEW.email, '@', 1), 'supabase_managed', 'supabase_managed', NOW())
  ON CONFLICT (id) DO NOTHING;
  
  INSERT INTO user_profiles (user_id, display_name)
  VALUES (NEW.id, SPLIT_PART(NEW.email, '@', 1))
  ON CONFLICT (user_id) DO NOTHING;
  
  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'handle_new_user trigger failed for %: %', NEW.id, SQLERRM;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION handle_new_user();

-- Step 6: Auto-update user_profiles stats when quiz scores change
CREATE OR REPLACE FUNCTION update_quiz_stats()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE user_profiles
  SET
    total_quiz_points = (
      SELECT COALESCE(SUM(best_score), 0) FROM module_quiz_scores
      WHERE user_id = NEW.user_id
    ),
    total_modules_completed = (
      SELECT COUNT(DISTINCT module_id) FROM module_quiz_scores
      WHERE user_id = NEW.user_id
    ),
    updated_at = NOW()
  WHERE user_id = NEW.user_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_quiz_score_change ON module_quiz_scores;
CREATE TRIGGER on_quiz_score_change
  AFTER INSERT OR UPDATE ON module_quiz_scores
  FOR EACH ROW
  EXECUTE FUNCTION update_quiz_stats();
