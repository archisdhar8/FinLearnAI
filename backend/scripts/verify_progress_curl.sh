#!/usr/bin/env bash
# Verify progress and quiz API endpoints with curl.
# Usage: ./verify_progress_curl.sh [BASE_URL] [USER_ID]
# Example: ./verify_progress_curl.sh http://localhost:8000 $(uuidgen)

set -e
BASE="${1:-http://localhost:8000}"
USER_ID="${2:-$(uuidgen 2>/dev/null || echo "test-user-001")}"
DISPLAY_NAME="TestUser"

echo "BASE_URL=$BASE"
echo "USER_ID=$USER_ID"
echo ""

# 1) POST /api/progress
echo "1. POST /api/progress"
curl -s -w "\nHTTP %{http_code}\n" -X POST "$BASE/api/progress" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"module_id\": \"foundations\",
    \"lesson_id\": \"what_is_investing\",
    \"completed\": true,
    \"display_name\": \"$DISPLAY_NAME\"
  }"
echo ""

# 2) GET /api/progress/{user_id}
echo "2. GET /api/progress/$USER_ID"
curl -s -w "\nHTTP %{http_code}\n" "$BASE/api/progress/$USER_ID"
echo ""

# 3) POST /api/quiz/submit (lesson quiz)
echo "3. POST /api/quiz/submit (lesson quiz)"
curl -s -w "\nHTTP %{http_code}\n" -X POST "$BASE/api/quiz/submit" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"module_id\": \"foundations\",
    \"lesson_id\": \"what_is_investing\",
    \"score\": 3,
    \"total_questions\": 5,
    \"is_final_quiz\": false,
    \"display_name\": \"$DISPLAY_NAME\"
  }"
echo ""

# 4) POST /api/quiz/submit (module final quiz)
echo "4. POST /api/quiz/submit (module final quiz)"
curl -s -w "\nHTTP %{http_code}\n" -X POST "$BASE/api/quiz/submit" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"module_id\": \"foundations\",
    \"lesson_id\": null,
    \"score\": 8,
    \"total_questions\": 10,
    \"is_final_quiz\": true,
    \"display_name\": \"$DISPLAY_NAME\"
  }"
echo ""

# 5) GET /api/quiz/scores/{user_id}
echo "5. GET /api/quiz/scores/$USER_ID"
curl -s -w "\nHTTP %{http_code}\n" "$BASE/api/quiz/scores/$USER_ID"
echo ""

echo "Done. Check responses for HTTP 200 and expected JSON."
