"""
Base recommender interface.  All recommenders implement this protocol.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pandas as pd


class CandidateScore:
    """Scored candidate lesson returned by a recommender."""

    __slots__ = ("lesson_id", "score", "source")

    def __init__(self, lesson_id: str, score: float, source: str = "unknown") -> None:
        self.lesson_id = lesson_id
        self.score     = float(score)
        self.source    = source   # "heuristic" | "ml_<model_name>"

    def __repr__(self) -> str:
        return f"CandidateScore({self.lesson_id!r}, score={self.score:.3f}, source={self.source!r})"


class BaseRecommender(ABC):
    """
    Abstract recommender.  Subclasses must implement `score_candidates`.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging / evaluation."""
        ...

    @abstractmethod
    def score_candidates(
        self,
        events:    pd.DataFrame,
        user_id:   str,
        candidates: Optional[List[str]] = None,
    ) -> List[CandidateScore]:
        """
        Score all eligible candidates for a user.

        Parameters
        ----------
        events     : raw event log (may include events for many users)
        user_id    : the target learner
        candidates : optional explicit list of lesson_ids to score;
                     if None, derive eligible candidates from events

        Returns
        -------
        List[CandidateScore] sorted descending by score.
        """
        ...

    def top_k(
        self,
        events:    pd.DataFrame,
        user_id:   str,
        k:         int = 3,
        candidates: Optional[List[str]] = None,
    ) -> List[CandidateScore]:
        """Convenience wrapper: score and return top-k."""
        scored = self.score_candidates(events, user_id, candidates=candidates)
        return sorted(scored, key=lambda c: c.score, reverse=True)[:k]
