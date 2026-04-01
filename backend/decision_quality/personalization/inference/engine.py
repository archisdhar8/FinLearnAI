"""
Recommendation inference engine.

Provides a single `RecommendationEngine` class that orchestrates:
  1. Loading user features and topic mastery from the event log
  2. Scoring eligible candidate lessons via the ML (or heuristic) model
  3. Generating human-readable explanations from computed features
  4. Computing readiness signals (ready for next module, needs review, etc.)
  5. Returning structured `RecommendationResponse` objects for the API

Explanations are fully deterministic — derived from computed feature
values, never hallucinated by an LLM.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..config import (
    MASTERY_THRESHOLD_PROFICIENT,
    MASTERY_THRESHOLD_WEAK,
    TOP_K_RECOMMENDATIONS,
    TOPICS,
)
from ..content_meta import (
    LESSON_BY_ID,
    MODULE_BY_ID,
    get_eligible_lessons,
    lessons_in_module,
)
from ..feature_engineering import (
    _current_module,
    compute_user_features,
    compute_all_topic_features,
)
from ..mastery import (
    compute_all_topic_mastery,
    weak_topics,
    strong_topics,
)
from ..models.base import CandidateScore
from ..models.heuristic import HeuristicRecommender
from ..models.ml_recommender import MLRecommender
from ..schemas import (
    AlternativeSuggestion,
    ReadinessStatus,
    RecommendationResponse,
    TopicMasteryResponse,
    UserFeaturesResponse,
)


# ---------------------------------------------------------------------------
# Explanation templates (deterministic, no LLM needed)
# ---------------------------------------------------------------------------

_TEMPLATES = {
    "weak_topic": (
        "Recommended because your recent quiz scores in {topic} are below your course average "
        "({mastery:.0%} mastery vs {avg:.0%} course average)."
    ),
    "tutor_confusion": (
        "You asked the AI tutor {n_questions} question(s) about {topic} — this lesson directly "
        "addresses those concepts."
    ),
    "next_in_sequence": (
        "This is the natural next step in the curriculum after completing {prev_lesson}."
    ),
    "prereq_blocker": (
        "Completing this lesson is a prerequisite for {num_blocked} upcoming lesson(s) — "
        "finishing it now will unlock more of the curriculum."
    ),
    "tool_recommendation": (
        "This lesson connects to the {tool} tool. "
        "Hands-on practice with the tool reinforces the concept."
    ),
    "review_prereq": (
        "Consider reviewing '{prereq_title}' first — your mastery in {prereq_topic} "
        "is currently low ({prereq_mastery:.0%}), which may make this lesson harder."
    ),
    "ready_for_next_module": (
        "You have completed all lessons in the current module and show strong mastery "
        "across covered topics. You are ready to advance."
    ),
    "good_progress": (
        "You are making steady progress. This lesson continues building on your "
        "strength in {topic}."
    ),
}


def _explain(
    template_key: str,
    **kwargs: Any,
) -> str:
    tmpl = _TEMPLATES.get(template_key, "Recommended based on your learning history.")
    try:
        return tmpl.format(**kwargs)
    except KeyError:
        return tmpl


# ---------------------------------------------------------------------------
# Readiness computation
# ---------------------------------------------------------------------------

def _compute_readiness(
    user_feats:  Dict[str, Any],
    mastery_map: Dict,
    completed:   set[str],
) -> ReadinessStatus:
    """
    Compute readiness signals:
    - ready_for_next_module: completed all current module lessons + decent mastery
    - should_review_prereq:  any recent lesson's prerequisite topic is still weak
    - suggested_tool:        if a weak topic has a connected tool lesson
    """
    # Module readiness
    current_mod_id = _current_module(completed)
    ready_for_next = False
    if current_mod_id:
        mod = MODULE_BY_ID[current_mod_id]
        mod_lessons_done = all(lid in completed for lid in mod.lesson_ids)
        mod_topics = list(mod.topics)
        if mod_topics:
            avg_mod_mastery = float(np.mean([
                mastery_map[t].mastery_score for t in mod_topics if t in mastery_map
            ]))
        else:
            avg_mod_mastery = 0.0
        ready_for_next = mod_lessons_done and avg_mod_mastery >= MASTERY_THRESHOLD_PROFICIENT

    # Prerequisite review
    from ..content_meta import LESSONS
    should_review_prereq = False
    for lesson in LESSONS:
        if lesson.lesson_id in completed:
            continue
        if not all(p in completed for p in lesson.prereq_ids):
            for p_id in lesson.prereq_ids:
                if p_id not in completed:
                    p_topic = LESSON_BY_ID[p_id].topic
                    if (p_topic in mastery_map
                            and mastery_map[p_topic].mastery_score < MASTERY_THRESHOLD_WEAK):
                        should_review_prereq = True
                        break

    # Suggested tool: find tool connected to weakest topic lesson
    suggested_tool: Optional[str] = None
    weak = [t for t in TOPICS if mastery_map.get(t, None) and
            mastery_map[t].mastery_score < MASTERY_THRESHOLD_WEAK]
    for t in weak:
        for lesson in LESSONS:
            if lesson.topic == t and lesson.tool_id and lesson.lesson_id not in completed:
                suggested_tool = lesson.tool_id
                break
        if suggested_tool:
            break

    # Readiness score
    avg_overall_mastery = float(np.mean([m.mastery_score for m in mastery_map.values()]))
    readiness_score = float(np.clip(
        0.4 * avg_overall_mastery
        + 0.3 * float(user_feats.get("pct_course_complete", 0.0))
        + 0.3 * float(user_feats.get("recent_avg_score", 0.0)),
        0.0, 1.0,
    ))

    notes = ""
    if ready_for_next:
        notes = _explain("ready_for_next_module")
    elif should_review_prereq:
        notes = "Some prerequisite topics need review before advancing."
    else:
        notes = "Continue working through the curriculum at your current pace."

    return ReadinessStatus(
        ready_for_next_module=ready_for_next,
        should_review_prereq=should_review_prereq,
        suggested_tool=suggested_tool,
        readiness_score=readiness_score,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Explanation builder for a single recommendation
# ---------------------------------------------------------------------------

def _build_explanation(
    lesson_id:   str,
    user_feats:  Dict[str, Any],
    mastery_map: Dict,
    score:       CandidateScore,
    completed:   set[str],
) -> str:
    lesson = LESSON_BY_ID.get(lesson_id)
    if not lesson:
        return "Recommended based on your learning profile."

    topic   = lesson.topic
    mastery = mastery_map.get(topic)
    m_score = mastery.mastery_score if mastery else 0.0
    overall = float(user_feats.get("overall_avg_score", 0.5))
    tutor_by_topic: Dict[str, int] = user_feats.get("tutor_questions_per_topic", {})
    tutor_n = tutor_by_topic.get(topic, 0)

    parts: List[str] = []

    # Primary reason
    if m_score < MASTERY_THRESHOLD_WEAK:
        parts.append(_explain("weak_topic", topic=topic, mastery=m_score, avg=overall))
    elif tutor_n >= 2:
        parts.append(_explain("tutor_confusion", topic=topic, n_questions=tutor_n))
    else:
        # Find previous lesson in sequence
        from ..content_meta import LESSON_ORDER
        idx = LESSON_ORDER.index(lesson_id) if lesson_id in LESSON_ORDER else 0
        prev_id = LESSON_ORDER[idx - 1] if idx > 0 else None
        prev_title = LESSON_BY_ID[prev_id].title if prev_id else "the previous lesson"
        parts.append(_explain("next_in_sequence", prev_lesson=prev_title))

    # Secondary reason: tool connection
    if lesson.tool_id:
        parts.append(_explain("tool_recommendation", tool=lesson.tool_id.replace("_", " ")))

    # Prereq review warning
    if lesson.prereq_ids:
        for p_id in lesson.prereq_ids:
            p_topic = LESSON_BY_ID[p_id].topic
            p_mastery = mastery_map.get(p_topic)
            if p_mastery and p_mastery.mastery_score < MASTERY_THRESHOLD_WEAK:
                p_title = LESSON_BY_ID[p_id].title
                parts.append(_explain(
                    "review_prereq",
                    prereq_title=p_title,
                    prereq_topic=p_topic,
                    prereq_mastery=p_mastery.mastery_score,
                ))
                break

    return "  ".join(parts)


def _weak_topic_summary(mastery_map: Dict) -> str:
    weak = [
        t for t in TOPICS
        if t in mastery_map and mastery_map[t].mastery_score < MASTERY_THRESHOLD_WEAK
    ]
    if not weak:
        return "No significantly weak topics detected."
    sorted_weak = sorted(weak, key=lambda t: mastery_map[t].mastery_score)
    entries = [f"{t} ({mastery_map[t].mastery_score:.0%})" for t in sorted_weak[:4]]
    return "Weak areas: " + ", ".join(entries) + "."


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class RecommendationEngine:
    """
    High-level inference engine.  Used by the FastAPI routes and the CLI.
    """

    def __init__(self, prefer_ml: bool = True) -> None:
        self._ml  = MLRecommender()
        self._heuristic = HeuristicRecommender()
        self.prefer_ml = prefer_ml

    def _recommender(self):
        return self._ml if self.prefer_ml else self._heuristic

    # ------------------------------------------------------------------
    # Core recommendation
    # ------------------------------------------------------------------

    def recommend(
        self,
        events:  pd.DataFrame,
        user_id: str,
        k:       int = TOP_K_RECOMMENDATIONS,
    ) -> List[RecommendationResponse]:
        """
        Return top-K recommendations for `user_id`.
        """
        u_events = events[events["user_id"] == user_id]

        completed: set[str] = set(
            u_events[u_events["event_type"] == "lesson_completed"]["lesson_id"].dropna()
        )
        eligible = get_eligible_lessons(completed)

        if not eligible:
            return []

        # Score candidates
        rec = self._recommender()
        scored = rec.score_candidates(u_events, user_id)
        scored_sorted = sorted(scored, key=lambda c: c.score, reverse=True)

        # Compute context for explanations
        user_feats  = compute_user_features(events, user_id)
        mastery_map = compute_all_topic_mastery(u_events, user_id)
        readiness   = _compute_readiness(user_feats, mastery_map, completed)

        now_str = datetime.now(timezone.utc).isoformat()
        results: List[RecommendationResponse] = []

        for i, cand in enumerate(scored_sorted[:k]):
            lesson = LESSON_BY_ID.get(cand.lesson_id)
            if not lesson:
                continue

            explanation    = _build_explanation(
                cand.lesson_id, user_feats, mastery_map, cand, completed
            )
            weak_summary   = _weak_topic_summary(mastery_map)

            # Alternatives = all other scored candidates
            alts: List[AlternativeSuggestion] = []
            for alt_cand in scored_sorted:
                if alt_cand.lesson_id == cand.lesson_id:
                    continue
                alt_lesson = LESSON_BY_ID.get(alt_cand.lesson_id)
                if not alt_lesson:
                    continue
                alt_reason = _build_explanation(
                    alt_cand.lesson_id, user_feats, mastery_map, alt_cand, completed
                )
                alts.append(AlternativeSuggestion(
                    lesson_id=alt_lesson.lesson_id,
                    title=alt_lesson.title,
                    confidence=round(alt_cand.score, 3),
                    reason=alt_reason,
                ))
                if len(alts) >= 2:
                    break

            results.append(RecommendationResponse(
                user_id=user_id,
                lesson_id=lesson.lesson_id,
                title=lesson.title,
                topic=lesson.topic,
                difficulty=lesson.difficulty,
                confidence=round(float(cand.score), 3),
                explanation=explanation,
                weak_topic_summary=weak_summary,
                readiness=readiness,
                alternatives=alts,
                generated_at=now_str,
            ))

        return results

    # ------------------------------------------------------------------
    # Feature summaries (for API endpoints)
    # ------------------------------------------------------------------

    def get_user_features_response(
        self, events: pd.DataFrame, user_id: str
    ) -> UserFeaturesResponse:
        u_events = events[events["user_id"] == user_id]
        feats    = compute_user_features(u_events, user_id)
        mastery_map = compute_all_topic_mastery(u_events, user_id)

        top_weak   = [t for t in TOPICS if mastery_map[t].mastery_score < MASTERY_THRESHOLD_WEAK]
        top_strong = [t for t in TOPICS if mastery_map[t].mastery_score >= MASTERY_THRESHOLD_PROFICIENT]
        top_weak   = sorted(top_weak,   key=lambda t: mastery_map[t].mastery_score)[:4]
        top_strong = sorted(top_strong, key=lambda t: mastery_map[t].mastery_score, reverse=True)[:4]

        return UserFeaturesResponse(
            user_id=user_id,
            overall_avg_score=round(float(feats.get("overall_avg_score", 0.0)), 3),
            recent_avg_score=round(float(feats.get("recent_avg_score", 0.0)), 3),
            lessons_completed=int(feats.get("lessons_completed", 0)),
            pct_course_complete=round(float(feats.get("pct_course_complete", 0.0)), 3),
            engagement_score=round(float(feats.get("engagement_score", 0.0)), 3),
            days_since_last_session=round(float(feats.get("days_since_last_session", 0.0)), 1),
            confusion_indicator=round(float(feats.get("confusion_indicator", 0.0)), 3),
            top_weak_topics=top_weak,
            top_strong_topics=top_strong,
        )

    def get_topic_mastery_response(
        self, events: pd.DataFrame, user_id: str
    ) -> TopicMasteryResponse:
        u_events    = events[events["user_id"] == user_id]
        mastery_map = compute_all_topic_mastery(u_events, user_id)

        mastery_dict = {t: round(m.mastery_score, 3) for t, m in mastery_map.items()}
        weak   = [t for t, v in mastery_dict.items() if v < MASTERY_THRESHOLD_WEAK]
        strong = [t for t, v in mastery_dict.items() if v >= MASTERY_THRESHOLD_PROFICIENT]

        return TopicMasteryResponse(
            user_id=user_id,
            mastery_map=mastery_dict,
            weak_topics=sorted(weak,   key=lambda t: mastery_dict[t]),
            strong_topics=sorted(strong, key=lambda t: mastery_dict[t], reverse=True),
        )

    def get_readiness(
        self, events: pd.DataFrame, user_id: str
    ) -> ReadinessStatus:
        u_events    = events[events["user_id"] == user_id]
        completed   = set(
            u_events[u_events["event_type"] == "lesson_completed"]["lesson_id"].dropna()
        )
        user_feats  = compute_user_features(u_events, user_id)
        mastery_map = compute_all_topic_mastery(u_events, user_id)
        return _compute_readiness(user_feats, mastery_map, completed)
