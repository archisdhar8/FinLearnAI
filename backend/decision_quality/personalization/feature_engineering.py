"""
Feature engineering for the learning-personalization ML model.

Converts raw event DataFrames into flat feature dicts suitable for
training and inference. All feature groups are computed independently
so they can be ablated in experiments.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .config import (
    RECENT_QUIZ_WINDOW,
    RECENT_SESSION_DAYS,
    TOPICS,
    TOOLS,
    MASTERY_THRESHOLD_PROFICIENT,
    MASTERY_THRESHOLD_WEAK,
)
from .content_meta import (
    LESSON_BY_ID,
    TOTAL_LESSONS,
    get_eligible_lessons,
    lessons_in_module,
)
from .mastery import compute_all_topic_mastery
from .schemas import TopicMastery


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _safe_mean(values: List[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _safe_ratio(num: int, den: int) -> float:
    return num / den if den > 0 else 0.0


def _days_since(ts: Optional[datetime], reference: Optional[datetime] = None) -> float:
    if ts is None:
        return 999.0
    ref = reference or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    delta = (ref - ts).total_seconds() / 86400.0
    return max(0.0, float(delta))


# ---------------------------------------------------------------------------
# User-level features
# ---------------------------------------------------------------------------

def compute_user_features(
    events: pd.DataFrame,
    user_id: str,
    as_of: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Compute all user-level features from the events table.

    Parameters
    ----------
    events : DataFrame with all events (will be filtered to user_id + as_of)
    user_id : target user
    as_of : only use events before this timestamp (for point-in-time training)
    """
    u = events[events["user_id"] == user_id].copy()
    if as_of is not None:
        u = u[pd.to_datetime(u["timestamp"], utc=True, format="mixed") <= pd.to_datetime(as_of, utc=True)]

    if u.empty:
        return _empty_user_features(user_id)

    feats: Dict[str, Any] = {"user_id": user_id}

    # --- Quiz performance ---
    quizzes = u[u["event_type"] == "quiz_submitted"]
    scores = quizzes["score"].dropna().tolist()
    feats["overall_avg_score"]      = _safe_mean(scores)
    feats["recent_avg_score"]       = _safe_mean(scores[-RECENT_QUIZ_WINDOW:])
    first_att = quizzes[quizzes["attempt_num"] == 1]["score"].dropna().tolist()
    feats["first_attempt_accuracy"] = _safe_mean(first_att)

    # Best attempt per quiz session: group by lesson_id
    if not quizzes.empty and "lesson_id" in quizzes.columns:
        best_scores = (
            quizzes.groupby("lesson_id")["score"].max().dropna().tolist()
        )
        feats["best_attempt_accuracy"] = _safe_mean(best_scores)
    else:
        feats["best_attempt_accuracy"] = feats["overall_avg_score"]

    total_quizzes   = len(quizzes)
    retry_quizzes   = int((quizzes["attempt_num"] > 1).sum())
    feats["retry_rate"] = _safe_ratio(retry_quizzes, total_quizzes)

    # --- Progress ---
    completed_lessons = set(
        u[u["event_type"] == "lesson_completed"]["lesson_id"].dropna().unique()
    )
    completed_modules = set(
        u[u["event_type"] == "module_completed"]["module_id"].dropna().unique()
    )
    feats["lessons_completed"]    = len(completed_lessons)
    feats["modules_completed"]    = len(completed_modules)
    feats["pct_course_complete"]  = _safe_ratio(len(completed_lessons), TOTAL_LESSONS)

    # Lessons left in current module: find the furthest incomplete module
    current_module_id = _current_module(completed_lessons)
    if current_module_id:
        module_lessons = lessons_in_module(current_module_id)
        remaining = [l for l in module_lessons if l.lesson_id not in completed_lessons]
        feats["lessons_left_module"] = len(remaining)
    else:
        feats["lessons_left_module"] = 0

    # Prerequisite completion ratio: of all lessons whose prereqs are met, what fraction done?
    eligible_if_started = [
        l for l in LESSON_BY_ID.values()
        if all(p in completed_lessons for p in l.prereq_ids)
    ]
    feats["prereq_completion_ratio"] = _safe_ratio(
        sum(1 for l in eligible_if_started if l.lesson_id in completed_lessons),
        len(eligible_if_started),
    )

    # --- Session / engagement ---
    session_events   = u[u["event_type"] == "session_ended"]
    session_durations = session_events["duration_mins"].dropna().tolist()
    feats["avg_session_length_mins"] = _safe_mean(session_durations)

    last_ts = u["timestamp"].dropna()
    if not last_ts.empty:
        last_time = pd.to_datetime(last_ts, utc=True, format="mixed").max()
        if hasattr(last_time, "to_pydatetime"):
            last_time = last_time.to_pydatetime()
        feats["days_since_last_session"] = _days_since(last_time, as_of)
    else:
        feats["days_since_last_session"] = 999.0

    started  = set(u[u["event_type"] == "lesson_started"]["lesson_id"].dropna())
    abandoned = started - completed_lessons
    feats["abandonment_rate"] = _safe_ratio(len(abandoned), len(started))

    # Composite engagement score: high completion, low days-since, low abandonment
    recency_factor = max(0.0, 1.0 - feats["days_since_last_session"] / 30.0)
    feats["engagement_score"] = float(np.clip(
        0.4 * feats["pct_course_complete"]
        + 0.3 * recency_factor
        + 0.3 * (1.0 - feats["abandonment_rate"]),
        0.0, 1.0,
    ))

    # --- Tutor usage ---
    tutor_events = u[u["event_type"] == "tutor_question"]
    feats["total_tutor_questions"] = len(tutor_events)

    # Confusion indicator: high tutor usage correlates with low quiz scores
    if feats["total_tutor_questions"] > 0:
        feats["confusion_indicator"] = float(
            min(feats["total_tutor_questions"] / 10.0, 1.0)
            * (1.0 - feats["overall_avg_score"])
        )
    else:
        feats["confusion_indicator"] = 0.0

    # Tutor questions per topic (will be used in topic features too)
    tutor_by_topic: Dict[str, int] = {}
    if "topic" in tutor_events.columns:
        for topic, grp in tutor_events.groupby("topic"):
            tutor_by_topic[str(topic)] = len(grp)
    feats["tutor_questions_per_topic"] = tutor_by_topic

    # --- Tool usage ---
    tool_events = u[u["event_type"] == "tool_used"]
    tool_counts: Dict[str, int] = {t: 0 for t in TOOLS}
    if not tool_events.empty and "metadata" in tool_events.columns:
        for _, row in tool_events.iterrows():
            meta = row.get("metadata", {})
            if isinstance(meta, dict):
                tool_id = meta.get("tool_id", "")
                if tool_id in tool_counts:
                    tool_counts[tool_id] += 1
    elif "tool_id" in tool_events.columns:
        for _, row in tool_events.iterrows():
            tool_id = str(row.get("tool_id", ""))
            if tool_id in tool_counts:
                tool_counts[tool_id] += 1

    for tool, cnt in tool_counts.items():
        feats[f"tool_{tool}_count"] = cnt

    # Tool-before-mastery: used tool on a lesson whose topic mastery < threshold
    tool_before_mastery = 0
    tool_after_lesson   = 0
    for _, te in tool_events.iterrows():
        topic_of_tool = te.get("topic", None)
        if topic_of_tool:
            topic_quizzes = quizzes[quizzes["topic"] == topic_of_tool]
            avg_t = topic_quizzes["score"].mean() if not topic_quizzes.empty else 0.0
            if avg_t < MASTERY_THRESHOLD_PROFICIENT:
                tool_before_mastery += 1
            else:
                tool_after_lesson += 1

    feats["used_tool_before_mastery"] = tool_before_mastery
    feats["used_tool_after_lesson"]   = tool_after_lesson

    return feats


def _empty_user_features(user_id: str) -> Dict[str, Any]:
    feats: Dict[str, Any] = {"user_id": user_id}
    for k in [
        "overall_avg_score", "recent_avg_score", "first_attempt_accuracy",
        "best_attempt_accuracy", "retry_rate", "pct_course_complete",
        "prereq_completion_ratio", "avg_session_length_mins",
        "abandonment_rate", "engagement_score", "confusion_indicator",
    ]:
        feats[k] = 0.0
    for k in ["lessons_completed", "modules_completed", "lessons_left_module",
              "total_tutor_questions", "used_tool_before_mastery", "used_tool_after_lesson"]:
        feats[k] = 0
    feats["days_since_last_session"] = 999.0
    feats["tutor_questions_per_topic"] = {}
    for t in TOOLS:
        feats[f"tool_{t}_count"] = 0
    return feats


def _current_module(completed: set[str]) -> Optional[str]:
    """Return the module_id of the first module that is not yet fully complete."""
    from .content_meta import MODULES
    for mod in MODULES:
        if not all(lid in completed for lid in mod.lesson_ids):
            return mod.module_id
    return None


# ---------------------------------------------------------------------------
# Topic-level features
# ---------------------------------------------------------------------------

def compute_topic_features(
    events: pd.DataFrame,
    user_id: str,
    topic: str,
    as_of: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Compute features for a specific (user, topic) pair."""
    mastery_map = compute_all_topic_mastery(
        events[(events["user_id"] == user_id)
               if as_of is None
               else events[(events["user_id"] == user_id)
                           & (pd.to_datetime(events["timestamp"]) <= pd.to_datetime(as_of))]],
        user_id,
    )
    m: TopicMastery = mastery_map[topic]
    feats = {f"topic_{k}": v for k, v in m.to_dict().items() if k not in ("user_id", "topic")}
    feats["topic_name"] = topic
    return feats


def compute_all_topic_features(
    events: pd.DataFrame,
    user_id: str,
    as_of: Optional[datetime] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return {topic: feature_dict} for all topics."""
    u = events[events["user_id"] == user_id]
    if as_of is not None:
        u = u[pd.to_datetime(u["timestamp"], utc=True, format="mixed") <= pd.to_datetime(as_of, utc=True)]
    mastery_map = compute_all_topic_mastery(u, user_id)
    return {
        topic: {f"topic_{k}": v for k, v in m.to_dict().items()
                if k not in ("user_id", "topic")}
        for topic, m in mastery_map.items()
    }


# ---------------------------------------------------------------------------
# Candidate lesson features
# ---------------------------------------------------------------------------

def compute_candidate_features(
    lesson_id: str,
    completed: set[str],
) -> Dict[str, Any]:
    """
    Compute features for a candidate lesson (independent of user state).
    """
    lesson = LESSON_BY_ID[lesson_id]
    all_prereqs = lesson.prereq_ids
    prereqs_satisfied = all(p in completed for p in all_prereqs)
    prereqs_done = sum(1 for p in all_prereqs if p in completed)
    prereq_ratio = prereqs_done / len(all_prereqs) if all_prereqs else 1.0

    # Distance: count how many lessons in curriculum order separate user's frontier
    from .content_meta import LESSON_ORDER
    last_completed_idx = -1
    for i, lid in enumerate(LESSON_ORDER):
        if lid in completed:
            last_completed_idx = i
    candidate_idx = LESSON_ORDER.index(lesson_id) if lesson_id in LESSON_ORDER else 99
    distance = candidate_idx - last_completed_idx - 1  # 0 = immediate next

    return {
        "cand_lesson_id":           lesson_id,
        "cand_topic":               lesson.topic,
        "cand_difficulty":          float(lesson.difficulty),
        "cand_duration_mins":       float(lesson.duration_mins),
        "cand_has_quiz":            int(lesson.has_quiz),
        "cand_has_tool":            int(lesson.tool_id is not None),
        "cand_tool_id":             lesson.tool_id or "",
        "cand_prereqs_satisfied":   int(prereqs_satisfied),
        "cand_prereq_ratio":        float(prereq_ratio),
        "cand_distance_from_front": float(max(distance, 0)),
    }


# ---------------------------------------------------------------------------
# Interaction features (user × candidate)
# ---------------------------------------------------------------------------

def compute_interaction_features(
    user_feats: Dict[str, Any],
    topic_feats: Dict[str, Any],    # features for the candidate's topic
    cand_feats: Dict[str, Any],
) -> Dict[str, Any]:
    """Cross features between user state and candidate lesson."""
    topic_mastery = float(topic_feats.get("topic_mastery_score", 0.0))
    cand_difficulty = float(cand_feats.get("cand_difficulty", 2.0))
    user_avg = float(user_feats.get("overall_avg_score", 0.0))

    # Mastery gap: how far below proficiency the user is in this topic
    mastery_gap = max(0.0, MASTERY_THRESHOLD_PROFICIENT - topic_mastery)

    # Difficulty mismatch: candidate difficulty vs user's effective level
    # user_level derived from overall quiz score (0→1 maps to difficulty 1→5)
    user_level = 1.0 + user_avg * 4.0
    difficulty_mismatch = cand_difficulty - user_level

    # Does candidate address the user's weakest concept area?
    cand_topic = cand_feats.get("cand_topic", "")
    user_tutor_by_topic: Dict[str, int] = user_feats.get("tutor_questions_per_topic", {})
    confusion_in_topic = float(user_tutor_by_topic.get(cand_topic, 0)) / 10.0
    addresses_confusion = int(
        topic_mastery < MASTERY_THRESHOLD_WEAK
        and confusion_in_topic > 0.1
    )

    # Tool readiness: lesson has a tool and user has some proficiency
    tool_ready = 0
    if cand_feats.get("cand_has_tool"):
        tool_ready = int(topic_mastery >= 0.40)

    return {
        "inter_mastery_gap":         mastery_gap,
        "inter_difficulty_mismatch": difficulty_mismatch,
        "inter_addresses_confusion": float(addresses_confusion),
        "inter_confusion_in_topic":  confusion_in_topic,
        "inter_topic_mastery":       topic_mastery,
        "inter_tool_ready":          float(tool_ready),
    }


# ---------------------------------------------------------------------------
# Full feature row for one (user, candidate) pair
# ---------------------------------------------------------------------------

def build_feature_row(
    events: pd.DataFrame,
    user_id: str,
    candidate_lesson_id: str,
    as_of: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Build a complete flat feature dict for one (user, candidate) pair.
    Used for both training and inference.
    """
    user_feats = compute_user_features(events, user_id, as_of=as_of)

    completed = set(
        events[
            (events["user_id"] == user_id)
            & (events["event_type"] == "lesson_completed")
        ]["lesson_id"].dropna().unique()
    )
    if as_of is not None:
        completed = set(
            events[
                (events["user_id"] == user_id)
                & (events["event_type"] == "lesson_completed")
                & (pd.to_datetime(events["timestamp"]) <= pd.to_datetime(as_of))
            ]["lesson_id"].dropna().unique()
        )

    cand_feats  = compute_candidate_features(candidate_lesson_id, completed)
    cand_topic  = cand_feats["cand_topic"]

    topic_feats_all = compute_all_topic_features(events, user_id, as_of=as_of)
    topic_feats = topic_feats_all.get(cand_topic, {})

    inter_feats = compute_interaction_features(user_feats, topic_feats, cand_feats)

    # Flatten – exclude non-numeric / id fields
    row: Dict[str, Any] = {}
    exclude_keys = {"user_id", "cand_lesson_id", "cand_topic", "cand_tool_id",
                    "topic_name", "tutor_questions_per_topic"}
    for source in [user_feats, topic_feats, cand_feats, inter_feats]:
        for k, v in source.items():
            if k not in exclude_keys and not isinstance(v, (dict, list)):
                row[k] = v

    # Keep IDs for reference (not in model input)
    row["_user_id"]      = user_id
    row["_lesson_id"]    = candidate_lesson_id
    row["_topic"]        = cand_topic
    row["_cand_tool_id"] = cand_feats.get("cand_tool_id", "")

    return row


# ---------------------------------------------------------------------------
# Feature columns used by the ML model (ordered, no meta columns)
# ---------------------------------------------------------------------------

USER_FEATURE_COLS = [
    "overall_avg_score", "recent_avg_score", "first_attempt_accuracy",
    "best_attempt_accuracy", "retry_rate",
    "lessons_completed", "modules_completed", "pct_course_complete",
    "lessons_left_module", "prereq_completion_ratio",
    "avg_session_length_mins", "days_since_last_session",
    "abandonment_rate", "engagement_score",
    "total_tutor_questions", "confusion_indicator",
    "used_tool_before_mastery", "used_tool_after_lesson",
] + [f"tool_{t}_count" for t in TOOLS]

TOPIC_FEATURE_COLS = [
    "topic_avg_score", "topic_attempts", "topic_error_rate",
    "topic_repeated_mistakes", "topic_time_spent_mins",
    "topic_tutor_questions", "topic_lessons_completed", "topic_mastery_score",
]

CANDIDATE_FEATURE_COLS = [
    "cand_difficulty", "cand_duration_mins",
    "cand_has_quiz", "cand_has_tool",
    "cand_prereqs_satisfied", "cand_prereq_ratio",
    "cand_distance_from_front",
]

INTERACTION_FEATURE_COLS = [
    "inter_mastery_gap", "inter_difficulty_mismatch",
    "inter_addresses_confusion", "inter_confusion_in_topic",
    "inter_topic_mastery", "inter_tool_ready",
]

ALL_FEATURE_COLS: List[str] = (
    USER_FEATURE_COLS
    + TOPIC_FEATURE_COLS
    + CANDIDATE_FEATURE_COLS
    + INTERACTION_FEATURE_COLS
)
