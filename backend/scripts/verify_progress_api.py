#!/usr/bin/env python3
"""
Verify progress and quiz Supabase-backed API endpoints.
Run from backend/ with: python scripts/verify_progress_api.py
Requires: API_BASE_URL (default http://localhost:8000) and optional TEST_USER_ID (UUID).
"""
import os
import sys
import uuid

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
TEST_USER_ID = os.environ.get("TEST_USER_ID", str(uuid.uuid4()))
DISPLAY_NAME = "TestUser"


def main():
    print(f"Using API_BASE_URL={API_BASE}, TEST_USER_ID={TEST_USER_ID}\n")

    # 1) POST /api/progress
    print("1. POST /api/progress ...")
    r = requests.post(
        f"{API_BASE}/api/progress",
        json={
            "user_id": TEST_USER_ID,
            "module_id": "foundations",
            "lesson_id": "what_is_investing",
            "completed": True,
            "display_name": DISPLAY_NAME,
        },
        timeout=10,
    )
    if r.status_code != 200:
        print(f"   FAILED: {r.status_code} {r.text}")
        return
    print("   OK")

    # 2) GET /api/progress/{user_id}
    print("2. GET /api/progress/{user_id} ...")
    r = requests.get(f"{API_BASE}/api/progress/{TEST_USER_ID}", timeout=10)
    if r.status_code != 200:
        print(f"   FAILED: {r.status_code} {r.text}")
        return
    data = r.json()
    progress = data.get("progress", {})
    foundations = progress.get("foundations", {})
    if "what_is_investing" not in foundations.get("completed_lessons", []):
        print(f"   FAILED: progress not persisted correctly: {data}")
        return
    print("   OK (progress persisted)")

    # 3) POST /api/quiz/submit (lesson quiz)
    print("3. POST /api/quiz/submit (lesson quiz) ...")
    r = requests.post(
        f"{API_BASE}/api/quiz/submit",
        json={
            "user_id": TEST_USER_ID,
            "module_id": "foundations",
            "lesson_id": "what_is_investing",
            "score": 3,
            "total_questions": 5,
            "is_final_quiz": False,
            "display_name": DISPLAY_NAME,
        },
        timeout=10,
    )
    if r.status_code != 200:
        print(f"   FAILED: {r.status_code} {r.text}")
        return
    print("   OK")

    # 4) POST /api/quiz/submit (module final quiz)
    print("4. POST /api/quiz/submit (module final quiz) ...")
    r = requests.post(
        f"{API_BASE}/api/quiz/submit",
        json={
            "user_id": TEST_USER_ID,
            "module_id": "foundations",
            "lesson_id": None,
            "score": 8,
            "total_questions": 10,
            "is_final_quiz": True,
            "display_name": DISPLAY_NAME,
        },
        timeout=10,
    )
    if r.status_code != 200:
        print(f"   FAILED: {r.status_code} {r.text}")
        return
    print("   OK")

    # 5) GET /api/quiz/scores/{user_id}
    print("5. GET /api/quiz/scores/{user_id} ...")
    r = requests.get(f"{API_BASE}/api/quiz/scores/{TEST_USER_ID}", timeout=10)
    if r.status_code != 200:
        print(f"   FAILED: {r.status_code} {r.text}")
        return
    data = r.json()
    lesson_scores = data.get("lesson_scores") or []
    module_scores = data.get("module_scores") or []
    if not any(s.get("lesson_id") == "what_is_investing" for s in lesson_scores):
        print(f"   FAILED: lesson score not found: {data}")
        return
    if not any(s.get("module_id") == "foundations" and s.get("best_score") is not None for s in module_scores):
        print(f"   FAILED: module score not found: {data}")
        return
    print("   OK (lesson + module scores persisted)")

    print("\nAll progress and quiz checks passed. Supabase data is updating correctly.")


if __name__ == "__main__":
    main()
