# Progress & Quiz Storage (Supabase)

## How progress is stored

- **Lesson completion**: One row per **user** in `user_progress` with a JSONB column `progress_data`:
  - Shape: `{ "module_id": { "completed_lessons": ["lesson_id", ...], "total_completed": N } }`
- **Quiz scores**: 
  - Per-lesson: `lesson_quiz_scores` (user_id, module_id, lesson_id, score, best_score, ...)
  - Module final: `module_quiz_scores` (user_id, module_id, score, best_score, best_percentage, ...)
- **Profiles**: `user_profiles` (total_lessons_completed, total_modules_completed, total_quiz_points) — updated by the backend when saving progress/quiz, and by DB triggers when using `module_quiz_scores`.

## Schema alignment

The backend expects `user_progress` to have:

- `user_id` (UUID, unique, FK to auth.users)
- `progress_data` (JSONB, default `'{}'`)
- `created_at`, `updated_at`

If your Supabase project has the older per-lesson layout (module_id, lesson_id, completed), run:

- **backend/migrations/001_user_progress_jsonb.sql** — creates the correct table. If the old table already exists, rename it first and then run the migration.

## Verify that data is updated

1. **Manual**: Complete a lesson and submit a quiz in the app, then check Supabase Dashboard → Table Editor → `user_progress`, `lesson_quiz_scores`, `module_quiz_scores`, `user_profiles`.

2. **curl (one-off)**: With the backend running, set `BASE=http://localhost:8000` and `USER_ID` to any UUID (e.g. `USER_ID=$(uuidgen)` or `USER_ID=test-user-001`), then run:

   ```bash
   # 1. Save lesson progress
   curl -X POST "$BASE/api/progress" -H "Content-Type: application/json" \
     -d '{"user_id":"'$USER_ID'","module_id":"foundations","lesson_id":"what_is_investing","completed":true,"display_name":"TestUser"}'

   # 2. Get progress
   curl "$BASE/api/progress/$USER_ID"

   # 3. Submit lesson quiz score
   curl -X POST "$BASE/api/quiz/submit" -H "Content-Type: application/json" \
     -d '{"user_id":"'$USER_ID'","module_id":"foundations","lesson_id":"what_is_investing","score":3,"total_questions":5,"is_final_quiz":false,"display_name":"TestUser"}'

   # 4. Submit module final quiz score
   curl -X POST "$BASE/api/quiz/submit" -H "Content-Type: application/json" \
     -d '{"user_id":"'$USER_ID'","module_id":"foundations","lesson_id":null,"score":8,"total_questions":10,"is_final_quiz":true,"display_name":"TestUser"}'

   # 5. Get quiz scores
   curl "$BASE/api/quiz/scores/$USER_ID"
   ```

3. **Shell script**: From the backend directory:
   ```bash
   chmod +x scripts/verify_progress_curl.sh
   ./scripts/verify_progress_curl.sh http://localhost:8000 "$(uuidgen)"
   ```

4. **Python script**: From the backend directory:
   ```bash
   export API_BASE_URL=http://localhost:8000   # or your backend URL
   python scripts/verify_progress_api.py
   ```
   Use a real `user_id` from Supabase Auth if you want to see data in the dashboard.
