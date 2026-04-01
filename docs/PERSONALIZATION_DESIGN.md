# Personalization & Decision Feedback — Implementation Design

This doc frames how to add **personalization** (recommended next lesson, weak areas, tool readiness) and **decision-quality feedback** (simulator / ETF / stock builder) **without** mixing them into static content. The ML/rules layer stays separate; the curriculum stays static.

---

## 1. Separation of concerns

| Layer | What it is | Where it lives | Touches static content? |
|-------|------------|----------------|--------------------------|
| **Static content** | Lessons, quiz questions, copy | `moduleContent.ts`, rendered by `LearningModule.tsx` | No — never personalized |
| **Behavior logging** | Progress, quiz submissions, (optional) tool usage | Supabase via existing APIs | No — only writes to DB |
| **Personalization engine** | Reads behavior → computes recommendations | New backend module + 1 API | No — reads DB + curriculum *structure* only |
| **Decision feedback** | Evaluates user choices in tools → returns message | New backend endpoints (or same module) | No — tools stay as-is; only show optional feedback |

**Principle:** Static content is never “personalized.” The same lessons and quizzes are shown to everyone. Only *which* lesson we *recommend next* and *what feedback* we show after a choice are dynamic.

---

## 2. Data you already have

- **`user_progress.progress_data`** (JSONB): `{ module_id: { completed_lessons: [lesson_id, ...], total_completed: N } }`
- **`lesson_quiz_scores`**: `user_id`, `module_id`, `lesson_id`, `score`, `percentage`
- **`module_quiz_scores`**: `user_id`, `module_id`, `score`, `percentage` (and best_score / best_percentage if you use them)

No new tables required for the first version. Optional later: a small `user_preferences` or `tool_usage_events` table if you want to store risk goal / horizon / “user ran simulator with X” for decision feedback.

---

## 3. Curriculum structure (backend only)

The personalization engine needs to know **order** of modules and lessons. That’s **structure**, not content.

- Keep **content** in the frontend (`moduleContent.ts`).
- In the backend, add a **small config** that mirrors only the **ordering** (and maybe titles for “weak area” labels):

```python
# backend/personalization.py or inside main.py

# Ordered curriculum: module_id -> list of lesson_id in order (must match frontend MODULES)
CURRICULUM = [
    {"id": "foundations", "title": "The Foundation", "lessons": ["what_is_investing", "stocks_bonds_funds", ...]},  # copy from moduleContent
    {"id": "investor-insight", "title": "Investor Insight", "lessons": [...]},
    {"id": "applied-investing", "title": "Applied Investing", "lessons": [...]},
]
```

You can derive this once from `moduleContent.ts` (or a shared JSON) and paste into the backend, or add a minimal `GET /api/curriculum` that returns `{ "modules": [ { "id", "title", "lesson_ids" } ] }` from a JSON file the backend reads. Content (markdown, quiz questions) stays in the frontend; backend only needs ids and order.

---

## 4. Personalization engine (recommendations)

**Input:** `user_id`  
**Output:** recommended next lesson, weak areas, readiness flags.

**Logic (all from existing data):**

1. **Recommended next lesson**
   - Load `user_progress.progress_data` for the user.
   - Walk `CURRICULUM` in order; for each module, walk its `lessons` in order.
   - Return the first `(module_id, lesson_id)` that is **not** in `progress_data[module_id].completed_lessons`.
   - If all completed, return `null` or “You’re done! Try the tools.”

2. **Weak areas**
   - From `lesson_quiz_scores` (and optionally `module_quiz_scores`) for this user, group by `module_id`, compute average `percentage` (or use best_percentage per lesson).
   - Sort modules by that average ascending; return the bottom 1–2 (e.g. “Building Your Portfolio: 72% avg”).
   - Thresholds are optional (e.g. only list modules below 80%).

3. **Readiness for tools**
   - Pure rules, no ML needed for v1:
     - **Simulator:** e.g. at least one lesson completed in `foundations`.
     - **ETF Recommender:** e.g. completed `foundations` (all lessons or passed module quiz) + optionally one other module.
     - **Stock Builder:** e.g. completed all three modules or “Applied Investing” + one more.
   - Return e.g. `{ "simulator": true, "etfRecommender": true, "stockBuilder": false }`.

**API:** e.g. `GET /api/personalization/recommendations?user_id=<id>` or `GET /api/me/recommendations` (auth from session). Response shape:

```json
{
  "recommended_next": { "module_id": "foundations", "lesson_id": "what_is_investing" } | null,
  "weak_areas": [ { "module_id": "...", "title": "...", "average_percentage": 72 } ],
  "readiness": { "simulator": true, "etfRecommender": true, "stockBuilder": false }
}
```

**Frontend:** Dashboard (and optionally LearningModule header) calls this once and displays:
- “Recommended next: [Lesson title]” with link to `/learn/{module_id}` and scroll/highlight to that lesson.
- “Weak areas: Building Your Portfolio (72% avg)” with link to that module.
- “You’re ready for: Simulator, ETF Recommender” (and grey out or soft-warn “Complete Applied Investing to unlock Stock Builder”).

Static content is unchanged; only the **recommendation UI** is new.

---

## 5. Decision-quality feedback (tools)

**Idea:** When the user makes a choice in Simulator / ETF Recommender / Stock Builder, the backend can optionally evaluate it and return a short message: “This may be too risky for your stated goals,” “This ETF better matches your horizon,” “Consider learning diversification before building a stock portfolio.”

**Separation:**
- **Tools stay as they are:** same inputs, same core logic (optimization, Monte Carlo, etc.).
- **New piece:** before or after showing the result, the frontend can send a **summary of the choice** (+ optional user context) to the backend; backend returns `{ "feedback": "..." }` or `{ "feedback": null }`.

**Implementation options:**

1. **Rule-based (recommended for v1)**  
   - **Simulator:** e.g. if `years < 3` and `monthly > 50% of income` → “Short horizon with high commitment; consider a longer timeline or smaller amount.”  
   - **ETF Recommender:** you already have risk score / profile. When user saves an allocation, compare to profile (e.g. 90% equity for “conservative”) → “This allocation is more aggressive than your profile; consider adding bonds.”  
   - **Stock Builder:** e.g. if single sector > 50% or only 1–2 stocks → “High concentration; diversification could reduce risk.”  
   - No ML; just a small “adviser” function per tool.

2. **Where to get “stated goals”**  
   - Dashboard already has `selectedGoal` (sessionStorage). You can send it with the feedback request (e.g. “retirement in 30 years”).  
   - ETF flow has risk score; store it in user_preferences or send it when asking for feedback.  
   - So: “decision quality” = backend compares **user’s choice** to **user’s stated goal/risk** and returns a string.

**APIs (optional, one per tool or one generic):**

- `POST /api/feedback/simulator` body: `{ user_id, goal?, monthly, years, expected_return? }` → `{ feedback?: string }`
- `POST /api/feedback/etf-allocation` body: `{ user_id, risk_score, allocation: { VTI: 50, ... } }` → `{ feedback?: string }`
- `POST /api/feedback/stock-portfolio` body: `{ user_id, tickers, weights, sector_breakdown? }` → `{ feedback?: string }`

Frontend: after computing the result, call the feedback endpoint; if `feedback` is non-null, show an Alert or inline message. Tools themselves don’t change; only this extra step is added.

---

## 6. Optional: tool usage events

If you want “readiness” or feedback to improve over time, you can log **anonymized or per-user** tool usage:

- Event: “user_id, tool=simulator, params_summary, timestamp.”
- Store in a small `tool_usage_events` table or append to a JSONB in `user_profiles`.  
Then:
- Readiness could depend on “has completed foundations **and** has run simulator at least once.”
- Decision feedback could later use history (e.g. “Last time you chose 90% equity”) without changing the current “one-shot” rule design.

Not required for the first version.

---

## 7. Summary: what lives where

- **Static content:** Frontend only (`moduleContent.ts`). Never split or duplicated for “personalized” lessons.
- **Behavior:** Already in Supabase (progress, quiz scores). Optional: tool usage events.
- **Curriculum structure:** Backend only (ordered list of module_id + lesson_ids; titles optional). Used only for “next lesson” and “weak areas.”
- **Personalization engine:** Backend. Reads DB + curriculum structure; returns recommendations. No ML needed for v1.
- **Decision feedback:** Backend. Receives choice + optional user context; returns a short message. Rule-based for v1.
- **UI:** Dashboard (and optionally tool result screens). Calls new APIs and displays recommendations / feedback. Learning modules and tool UIs stay the same; only these **add-ons** are new.

This keeps the ML/rules layer integrated where it matters (recommendations and feedback) but **separate from static content**, so you can iterate on personalization without touching lesson or quiz content.
