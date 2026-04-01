"""
FastAPI router for the learning-personalization subsystem.

Mount this router in main.py:
    from decision_quality.personalization.api.routes import personalization_router
    app.include_router(personalization_router, prefix="/api/personalization")

Endpoints
---------
GET  /api/personalization/health
GET  /api/personalization/users/{user_id}/features
GET  /api/personalization/users/{user_id}/mastery
GET  /api/personalization/users/{user_id}/recommend
GET  /api/personalization/users/{user_id}/recommend/top3
GET  /api/personalization/users/{user_id}/readiness
POST /api/personalization/events          (ingest raw events)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import DATA_DIR, TOP_K_RECOMMENDATIONS
from ..inference.engine import RecommendationEngine
from ..schemas import (
    RecommendationResponse,
    ReadinessStatus,
    TopicMasteryResponse,
    UserFeaturesResponse,
)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

personalization_router = APIRouter(tags=["Personalization"])


# ---------------------------------------------------------------------------
# Shared state (lazy-loaded event store and engine)
# ---------------------------------------------------------------------------

# Real user events are persisted here so they survive server restarts.
_REAL_EVENTS_PATH = DATA_DIR / "real_user_events.jsonl"

# Frontend lesson IDs → backend lesson IDs.
# Needed to normalise events ingested before the frontend was updated to send
# backend IDs, and as a safety net for any edge-cases.
_FRONTEND_TO_BACKEND: Dict[str, str] = {
    "what_is_investing":           "L01",
    "what_youre_buying":           "L02",
    "time_and_compounding":        "L03",
    "accounts_and_setup":          "L01",
    "first_time_mindset":          "L02",
    "basics_of_risk":              "L05",
    "reading_market_signals":      "L06",
    "investor_psychology":         "L07",
    "risk_portfolio_thinking":     "L09",
    "types_of_investing":          "L14",
    "hype_vs_fundamentals":        "L13",
    "how_markets_work":            "L19",
    "what_moves_markets":          "L19",
    "setting_long_term_structure": "L11",
    "realistic_expectations":      "L11",
    "asset_allocation":            "L12",
    "what_to_do_in_crash":         "L06",
    "costs_fees_taxes":            "L01",
    "lending_home_ownership":      "L02",
}

_BACKEND_LESSON_IDS = {f"L{i:02d}" for i in range(1, 21)}


def _normalise_lesson_id(lid: Optional[str]) -> Optional[str]:
    """Map a frontend lesson ID to its backend equivalent; leave backend IDs unchanged."""
    if lid is None:
        return None
    if lid in _BACKEND_LESSON_IDS:
        return lid
    return _FRONTEND_TO_BACKEND.get(lid, lid)


def _normalise_events(df: pd.DataFrame) -> pd.DataFrame:
    """Translate frontend lesson IDs → backend IDs in lesson_completed rows."""
    if df.empty or "lesson_id" not in df.columns:
        return df
    mask = df["event_type"] == "lesson_completed"
    df = df.copy()
    df.loc[mask, "lesson_id"] = df.loc[mask, "lesson_id"].apply(_normalise_lesson_id)
    return df


# In-memory cache (synthetic baseline + persisted real-user events merged in).
_events_cache: Optional[pd.DataFrame] = None
_engine_instance: Optional[RecommendationEngine] = None


def _get_engine() -> RecommendationEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RecommendationEngine(prefer_ml=True)
    return _engine_instance


def _load_real_events() -> pd.DataFrame:
    """Load persisted real-user events from the JSONL file."""
    if not _REAL_EVENTS_PATH.exists():
        return pd.DataFrame()
    rows = []
    try:
        with open(_REAL_EVENTS_PATH, "r") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _get_events() -> pd.DataFrame:
    """
    Return the merged event log: synthetic baseline (parquet) + real user events
    (persisted JSONL).  Result is cached in memory for fast serving.
    """
    global _events_cache
    if _events_cache is not None:
        return _events_cache

    _REAL_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    frames: List[pd.DataFrame] = []

    events_path = DATA_DIR / "events.parquet"
    if events_path.exists():
        frames.append(pd.read_parquet(events_path))

    real = _load_real_events()
    if not real.empty:
        frames.append(real)

    if frames:
        merged = pd.concat(frames, ignore_index=True)
    else:
        merged = pd.DataFrame(columns=[
            "user_id", "event_type", "timestamp", "lesson_id", "module_id",
            "topic", "concept_tag", "score", "attempt_num", "duration_mins",
        ])

    _events_cache = _normalise_events(merged)
    return _events_cache


def _get_user_events(user_id: str) -> pd.DataFrame:
    events = _get_events()
    if events.empty:
        return events
    return events[events["user_id"] == user_id]


# ---------------------------------------------------------------------------
# Pydantic request model for event ingestion
# ---------------------------------------------------------------------------

class EventIngestionRequest(BaseModel):
    user_id:      str
    event_type:   str
    timestamp:    Optional[str] = None
    lesson_id:    Optional[str] = None
    module_id:    Optional[str] = None
    topic:        Optional[str] = None
    concept_tag:  Optional[str] = None
    score:        Optional[float] = None
    attempt_num:  int = 1
    duration_mins: Optional[float] = None
    metadata:     Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@personalization_router.get("/health")
async def personalization_health() -> Dict[str, Any]:
    """Health check for the personalization subsystem."""
    events    = _get_events()
    real      = _load_real_events()
    from ..models.ml_recommender import _load_artifact
    has_model = _load_artifact() is not None

    return {
        "status":             "ok",
        "events_loaded":      len(events),
        "real_user_events":   len(real),
        "model_ready":        has_model,
        "timestamp":          datetime.now(timezone.utc).isoformat(),
    }


@personalization_router.get("/users/{user_id}/features", response_model=UserFeaturesResponse)
async def get_user_features(user_id: str) -> UserFeaturesResponse:
    """Return computed user-level learning features."""
    events = _get_events()
    engine = _get_engine()
    try:
        return engine.get_user_features_response(events, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@personalization_router.get("/users/{user_id}/mastery", response_model=TopicMasteryResponse)
async def get_user_mastery(user_id: str) -> TopicMasteryResponse:
    """Return per-topic mastery scores for a user."""
    events = _get_events()
    engine = _get_engine()
    try:
        return engine.get_topic_mastery_response(events, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@personalization_router.get(
    "/users/{user_id}/recommend",
    response_model=RecommendationResponse,
)
async def get_next_recommendation(user_id: str) -> RecommendationResponse:
    """Return the single best next-lesson recommendation for a user."""
    events = _get_events()
    engine = _get_engine()
    try:
        recs = engine.recommend(events, user_id, k=1)
        if not recs:
            raise HTTPException(
                status_code=404,
                detail="No eligible lessons found. The user may have completed all lessons.",
            )
        return recs[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@personalization_router.get(
    "/users/{user_id}/recommend/top3",
    response_model=List[RecommendationResponse],
)
async def get_top3_recommendations(
    user_id: str,
    k: int = TOP_K_RECOMMENDATIONS,
) -> List[RecommendationResponse]:
    """Return the top-K next-lesson recommendations for a user."""
    events = _get_events()
    engine = _get_engine()
    try:
        return engine.recommend(events, user_id, k=k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@personalization_router.get("/users/{user_id}/readiness", response_model=ReadinessStatus)
async def get_readiness_status(user_id: str) -> ReadinessStatus:
    """Return the readiness status (module advancement, prereq review, tool suggestion)."""
    events = _get_events()
    engine = _get_engine()
    try:
        return engine.get_readiness(events, user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@personalization_router.post("/events", status_code=201)
async def ingest_event(req: EventIngestionRequest) -> Dict[str, str]:
    """
    Ingest a single user event.

    Persists the event to disk (JSONL) so it survives server restarts, and
    appends it to the in-memory cache so recommendations update immediately.
    lesson_completed events are normalised to backend lesson IDs on ingestion.
    """
    global _events_cache

    # Normalise lesson_id for lesson_completed events so the eligibility filter
    # always sees backend IDs (L01–L20) regardless of what the frontend sends.
    lesson_id = req.lesson_id
    if req.event_type == "lesson_completed":
        lesson_id = _normalise_lesson_id(lesson_id)

    ts = req.timestamp or datetime.now(timezone.utc).isoformat()

    new_row: Dict[str, Any] = {
        "user_id":       req.user_id,
        "event_type":    req.event_type,
        "timestamp":     ts,
        "lesson_id":     lesson_id,
        "module_id":     req.module_id,
        "topic":         req.topic,
        "concept_tag":   req.concept_tag,
        "score":         req.score,
        "attempt_num":   req.attempt_num,
        "duration_mins": req.duration_mins,
    }
    if req.metadata:
        new_row.update(req.metadata)

    # ── Persist to disk ──────────────────────────────────────────────────────
    try:
        _REAL_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_REAL_EVENTS_PATH, "a") as fh:
            fh.write(json.dumps({k: v for k, v in new_row.items() if v is not None}) + "\n")
    except Exception as write_err:
        # Non-fatal: event still lives in memory for this session
        print(f"[Personalization] Warning: could not persist event: {write_err}")

    # ── Update in-memory cache ────────────────────────────────────────────────
    events = _get_events()
    _events_cache = pd.concat(
        [events, pd.DataFrame([new_row])], ignore_index=True
    )
    return {"status": "ok", "message": f"Event ingested for user {req.user_id}"}


@personalization_router.post("/cache/refresh")
async def refresh_cache() -> Dict[str, str]:
    """Reload the event log from disk (synthetic parquet + real-user JSONL)."""
    global _events_cache
    _events_cache = None
    events = _get_events()
    return {"status": "ok", "message": f"Event cache refreshed ({len(events)} rows)"}
