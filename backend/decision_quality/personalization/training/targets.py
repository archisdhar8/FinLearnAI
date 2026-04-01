"""
Target (label) definitions for the next-best-lesson ranking model.

Two definitions are provided:
  1. MasteryGainTarget   – positive if taking the lesson led to mastery gain
                           above a threshold (academically grounded).
  2. CompletionScoreTarget – positive if lesson was completed AND quiz score
                             exceeded a threshold (simpler, easier to audit).

Both implement the same interface so they are drop-in swappable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import pandas as pd

from ..config import (
    SIMPLE_TARGET_SCORE_THRESHOLD,
    TARGET_MASTERY_GAIN_THRESHOLD,
)


class LabelDefinition(ABC):
    """Interface for all target definitions."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def label(
        self,
        user_id:   str,
        lesson_id: str,
        events:    pd.DataFrame,
        snapshots: pd.DataFrame,
    ) -> Optional[int]:
        """
        Return 1 (positive), 0 (negative), or None (skip this example).

        Parameters
        ----------
        user_id   : target user
        lesson_id : the lesson to label
        events    : full raw event DataFrame
        snapshots : mastery snapshot DataFrame (from synthetic generator)
        """
        ...


class MasteryGainTarget(LabelDefinition):
    """
    Positive label when taking the lesson produced a mastery gain
    of at least `threshold` for the lesson's topic.

    This is the primary, academically defensible target.
    """

    def __init__(self, threshold: float = TARGET_MASTERY_GAIN_THRESHOLD) -> None:
        self.threshold = threshold

    @property
    def name(self) -> str:
        return f"mastery_gain_ge_{self.threshold:.2f}"

    def label(
        self,
        user_id:   str,
        lesson_id: str,
        events:    pd.DataFrame,
        snapshots: pd.DataFrame,
    ) -> Optional[int]:
        # Find snapshot for this (user, lesson)
        snap_rows = snapshots[
            (snapshots["user_id"]   == user_id)
            & (snapshots["lesson_id"] == lesson_id)
        ]
        if snap_rows.empty:
            return None   # No completion recorded → skip

        gain = float(snap_rows["mastery_gain"].max())
        return int(gain >= self.threshold)


class CompletionScoreTarget(LabelDefinition):
    """
    Positive label when the lesson was completed AND the quiz score
    on the best attempt was at or above `score_threshold`.

    Simple, fast to compute from events alone (no snapshots needed).
    """

    def __init__(self, score_threshold: float = SIMPLE_TARGET_SCORE_THRESHOLD) -> None:
        self.score_threshold = score_threshold

    @property
    def name(self) -> str:
        return f"completion_score_ge_{self.score_threshold:.2f}"

    def label(
        self,
        user_id:   str,
        lesson_id: str,
        events:    pd.DataFrame,
        snapshots: pd.DataFrame,
    ) -> Optional[int]:
        u = events[(events["user_id"] == user_id) & (events["lesson_id"] == lesson_id)]

        # Must have a completion event
        completed = (u["event_type"] == "lesson_completed").any()
        if not completed:
            return None

        # Check best quiz score for this lesson
        quizzes = u[u["event_type"] == "quiz_submitted"]
        if quizzes.empty:
            # No quiz → label as positive if lesson was completed
            return 1

        best_score = float(quizzes["score"].max())
        return int(best_score >= self.score_threshold)


# Default label definition used by training pipeline
DEFAULT_TARGET: LabelDefinition = MasteryGainTarget()

# Alternative swappable
SIMPLE_TARGET: LabelDefinition = CompletionScoreTarget()
