"""
Topic mastery computation.

Mastery is a latent variable (0–1) estimated from observable signals:
quiz scores, lesson completions, tutor usage, and error patterns.
The formula is transparent and explainable.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from .config import (
    MASTERY_THRESHOLD_PROFICIENT,
    MASTERY_THRESHOLD_WEAK,
    TOPICS,
)
from .schemas import TopicMastery


# Weights for each mastery signal (must sum ≈ 1)
_W_SCORE       = 0.45   # quiz score is primary driver
_W_COMPLETION  = 0.20   # lesson completion ratio
_W_CONSISTENCY = 0.15   # first-attempt accuracy
_W_TUTOR_PEN   = 0.10   # tutor-usage penalty (many questions → lower mastery)
_W_RETRY_PEN   = 0.10   # retry penalty


def compute_topic_mastery(
    events: pd.DataFrame,
    user_id: str,
    topic: str,
) -> TopicMastery:
    """
    Compute TopicMastery for a single (user, topic) pair from a DataFrame
    of events (already filtered or full – filtering happens here).

    events columns expected: user_id, event_type, topic, score, attempt_num,
                             duration_mins, lesson_id, concept_tag
    """
    u_events = events[(events["user_id"] == user_id) & (events["topic"] == topic)]

    # --- Quiz signals ---
    quizzes = u_events[u_events["event_type"] == "quiz_submitted"]
    attempts     = len(quizzes)
    scores       = quizzes["score"].dropna().tolist()
    avg_score    = float(np.mean(scores)) if scores else 0.0

    first_attempts = quizzes[quizzes["attempt_num"] == 1]["score"].dropna()
    first_acc = float(first_attempts.mean()) if len(first_attempts) > 0 else 0.0

    # Error rate: fraction of quizzes scoring < pass threshold
    error_rate = float((quizzes["score"].dropna() < MASTERY_THRESHOLD_PROFICIENT).mean()) if attempts > 0 else 0.0

    # Repeated mistakes: quiz attempts beyond 1 in this topic
    retry_attempts = int((quizzes["attempt_num"] > 1).sum())

    # --- Lesson completion ---
    completed_lessons = int(
        (u_events["event_type"] == "lesson_completed").sum()
    )

    # --- Time spent ---
    time_spent = float(u_events["duration_mins"].fillna(0).sum())

    # --- Tutor usage ---
    tutor_q = int(
        (u_events["event_type"] == "tutor_question").sum()
    )

    # --- Mastery score (0–1 composite) ---
    # Base: quiz performance
    score_component = avg_score * _W_SCORE

    # Lesson completion: ratio of completed to total topic lessons
    from .content_meta import topic_to_lessons
    total_topic_lessons = max(len(topic_to_lessons(topic)), 1)
    completion_ratio = min(completed_lessons / total_topic_lessons, 1.0)
    completion_component = completion_ratio * _W_COMPLETION

    # Consistency: first-attempt accuracy
    consistency_component = first_acc * _W_CONSISTENCY

    # Tutor penalty: normalise tutor questions (0 → no penalty, ≥5 → full penalty)
    tutor_norm = min(tutor_q / 5.0, 1.0)
    # Only penalise when quiz scores are also low (confusion, not curiosity)
    tutor_penalty = tutor_norm * (1 - avg_score) * _W_TUTOR_PEN

    # Retry penalty
    retry_norm = min(retry_attempts / 3.0, 1.0)
    retry_penalty = retry_norm * (1 - avg_score) * _W_RETRY_PEN

    mastery_score = float(
        np.clip(score_component + completion_component + consistency_component
                - tutor_penalty - retry_penalty, 0.0, 1.0)
    )

    return TopicMastery(
        user_id=user_id,
        topic=topic,
        avg_score=avg_score,
        attempts=attempts,
        error_rate=error_rate,
        repeated_mistakes=retry_attempts,
        time_spent_mins=time_spent,
        tutor_questions=tutor_q,
        lessons_completed=completed_lessons,
        mastery_score=mastery_score,
    )


def compute_all_topic_mastery(
    events: pd.DataFrame,
    user_id: str,
) -> Dict[str, TopicMastery]:
    """Compute TopicMastery for all topics for a single user."""
    return {
        topic: compute_topic_mastery(events, user_id, topic)
        for topic in TOPICS
    }


def weak_topics(mastery_map: Dict[str, TopicMastery]) -> List[str]:
    """Return topics where mastery_score < MASTERY_THRESHOLD_WEAK, sorted ascending."""
    weak = [
        t for t, m in mastery_map.items()
        if m.mastery_score < MASTERY_THRESHOLD_WEAK
    ]
    return sorted(weak, key=lambda t: mastery_map[t].mastery_score)


def strong_topics(mastery_map: Dict[str, TopicMastery]) -> List[str]:
    """Return topics where mastery_score >= MASTERY_THRESHOLD_PROFICIENT, sorted descending."""
    strong = [
        t for t, m in mastery_map.items()
        if m.mastery_score >= MASTERY_THRESHOLD_PROFICIENT
    ]
    return sorted(strong, key=lambda t: mastery_map[t].mastery_score, reverse=True)
