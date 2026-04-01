"""
Rule-based (heuristic) recommender.

Strategy
--------
1. Find all eligible lessons (prerequisites satisfied, not yet completed).
2. Score each candidate by a combination of:
   - User's mastery gap in the candidate's topic (higher gap → higher priority)
   - Proximity to current curriculum position (next-in-sequence gets a bonus)
   - Whether the candidate directly addresses a confused concept
   - Prerequisite readiness (prefer lessons with all prereqs comfortably met)
3. Return the sorted list of CandidateScores.

This recommender is fully explainable and requires no training.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..config import MASTERY_THRESHOLD_PROFICIENT, MASTERY_THRESHOLD_WEAK, TOPICS
from ..content_meta import (
    LESSON_BY_ID,
    LESSON_ORDER,
    get_eligible_lessons,
)
from ..mastery import compute_all_topic_mastery
from .base import BaseRecommender, CandidateScore


class HeuristicRecommender(BaseRecommender):
    """
    Deterministic rule-based recommender.

    Scoring formula (all components ∈ [0,1], summed with weights):
      - mastery_gap_score   : normalised distance from proficiency in topic
      - sequence_score      : curriculum-order proximity bonus
      - confusion_score     : topic has high tutor usage + low mastery
      - prereq_safety_score : all direct prerequisites comfortably above threshold
    """

    WEIGHTS = {
        "mastery_gap":    0.40,
        "sequence":       0.30,
        "confusion":      0.20,
        "prereq_safety":  0.10,
    }

    @property
    def name(self) -> str:
        return "heuristic"

    def score_candidates(
        self,
        events:    pd.DataFrame,
        user_id:   str,
        candidates: Optional[List[str]] = None,
    ) -> List[CandidateScore]:
        u_events = events[events["user_id"] == user_id]

        # Completed lessons
        completed: set[str] = set(
            u_events[u_events["event_type"] == "lesson_completed"]["lesson_id"].dropna()
        )

        # Eligible candidates
        if candidates is not None:
            eligible_lessons = [
                LESSON_BY_ID[lid] for lid in candidates
                if lid in LESSON_BY_ID and lid not in completed
            ]
        else:
            eligible_lessons = get_eligible_lessons(completed)

        if not eligible_lessons:
            return []

        # Compute topic mastery
        mastery_map = compute_all_topic_mastery(u_events, user_id)

        # Tutor questions per topic (confusion signal)
        tutor_events = u_events[u_events["event_type"] == "tutor_question"]
        tutor_by_topic: Dict[str, int] = {}
        if not tutor_events.empty and "topic" in tutor_events.columns:
            for topic, grp in tutor_events.groupby("topic"):
                tutor_by_topic[str(topic)] = len(grp)
        max_tutor = max(tutor_by_topic.values()) if tutor_by_topic else 1

        # Current curriculum position (last completed lesson index)
        last_idx = -1
        for i, lid in enumerate(LESSON_ORDER):
            if lid in completed:
                last_idx = i

        scores: List[CandidateScore] = []
        for lesson in eligible_lessons:
            topic   = lesson.topic
            mastery = mastery_map[topic].mastery_score if topic in mastery_map else 0.0

            # --- Mastery gap: how far below proficiency in this topic ---
            mastery_gap_score = max(0.0, MASTERY_THRESHOLD_PROFICIENT - mastery) / MASTERY_THRESHOLD_PROFICIENT

            # --- Sequence score: prefer next-in-order ---
            cand_idx = LESSON_ORDER.index(lesson.lesson_id) if lesson.lesson_id in LESSON_ORDER else 99
            dist = max(0, cand_idx - last_idx - 1)
            sequence_score = 1.0 / (1.0 + dist)

            # --- Confusion score: tutor questions + low mastery ---
            tutor_norm = tutor_by_topic.get(topic, 0) / max_tutor
            confusion_score = tutor_norm * max(0.0, 1.0 - mastery)

            # --- Prerequisite safety score ---
            prereq_masteries = [
                mastery_map.get(LESSON_BY_ID[p].topic, None)
                for p in lesson.prereq_ids
                if p in LESSON_BY_ID
            ]
            if prereq_masteries:
                avg_prereq_mastery = float(np.mean([
                    m.mastery_score if m else 0.0 for m in prereq_masteries
                ]))
            else:
                avg_prereq_mastery = 1.0
            prereq_safety_score = float(np.clip(avg_prereq_mastery, 0.0, 1.0))

            # --- Weighted sum ---
            w = self.WEIGHTS
            final_score = (
                w["mastery_gap"]   * mastery_gap_score
                + w["sequence"]    * sequence_score
                + w["confusion"]   * confusion_score
                + w["prereq_safety"] * prereq_safety_score
            )

            scores.append(CandidateScore(
                lesson_id=lesson.lesson_id,
                score=float(final_score),
                source="heuristic",
            ))

        return sorted(scores, key=lambda c: c.score, reverse=True)
