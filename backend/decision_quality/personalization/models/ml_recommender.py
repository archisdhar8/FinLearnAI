"""
ML-based recommender.

Loads a trained sklearn model artifact and uses it to predict P(beneficial)
for each eligible candidate lesson.  Falls back to the heuristic recommender
if no artifact is found.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..config import ARTIFACTS_DIR
from ..content_meta import LESSON_BY_ID, get_eligible_lessons
from ..feature_engineering import ALL_FEATURE_COLS, build_feature_row
from .base import BaseRecommender, CandidateScore
from .heuristic import HeuristicRecommender


# Prefer gradient boosting; fall back to other saved models
_MODEL_PRIORITY = [
    "personalization_gradient_boosting.pkl",
    "personalization_random_forest.pkl",
    "personalization_logistic_regression.pkl",
]

_artifact_cache: Optional[dict] = None


def _load_artifact() -> Optional[dict]:
    global _artifact_cache
    if _artifact_cache is not None:
        return _artifact_cache

    import joblib
    for fname in _MODEL_PRIORITY:
        path = ARTIFACTS_DIR / fname
        if path.exists():
            _artifact_cache = joblib.load(path)
            return _artifact_cache
    return None


class MLRecommender(BaseRecommender):
    """
    ML-backed recommender using a trained GBM / RF / LR model.

    If no model artifact exists, delegates to HeuristicRecommender with a
    warning so inference always works.
    """

    def __init__(self, model_name: Optional[str] = None) -> None:
        """
        Parameters
        ----------
        model_name : explicit pkl stem, e.g. "personalization_random_forest".
                     If None, uses the first available model in priority order.
        """
        self._explicit_model_name = model_name
        self._fallback = HeuristicRecommender()

    @property
    def name(self) -> str:
        art = self._get_artifact()
        if art:
            return f"ml_{art.get('model_name', 'unknown')}"
        return "heuristic_fallback"

    def _get_artifact(self) -> Optional[dict]:
        global _artifact_cache
        if self._explicit_model_name:
            import joblib
            path = ARTIFACTS_DIR / f"{self._explicit_model_name}.pkl"
            if path.exists():
                return joblib.load(path)
            return None
        return _load_artifact()

    def score_candidates(
        self,
        events:    pd.DataFrame,
        user_id:   str,
        candidates: Optional[List[str]] = None,
    ) -> List[CandidateScore]:
        artifact = self._get_artifact()

        if artifact is None:
            warnings.warn(
                "No ML model artifact found. Falling back to heuristic recommender. "
                "Run:  python -m backend.decision_quality.personalization.training.train",
                RuntimeWarning,
                stacklevel=2,
            )
            return self._fallback.score_candidates(events, user_id, candidates=candidates)

        model        = artifact["model"]
        scaler       = artifact["scaler"]
        feature_cols = artifact.get("feature_cols", ALL_FEATURE_COLS)

        u_events = events[events["user_id"] == user_id]
        completed: set[str] = set(
            u_events[u_events["event_type"] == "lesson_completed"]["lesson_id"].dropna()
        )

        if candidates is not None:
            eligible_ids = [
                lid for lid in candidates
                if lid in LESSON_BY_ID and lid not in completed
            ]
        else:
            eligible_ids = [l.lesson_id for l in get_eligible_lessons(completed)]

        if not eligible_ids:
            return []

        # Build feature matrix for all candidates
        rows: List[Dict] = []
        valid_ids: List[str] = []
        for lid in eligible_ids:
            try:
                row = build_feature_row(events, user_id, lid)
                rows.append(row)
                valid_ids.append(lid)
            except Exception:
                continue

        if not rows:
            return self._fallback.score_candidates(events, user_id, candidates=candidates)

        df_cands = pd.DataFrame(rows)
        # Ensure all feature columns exist
        for col in feature_cols:
            if col not in df_cands.columns:
                df_cands[col] = 0.0

        X = df_cands[feature_cols].fillna(0.0).values.astype(float)
        X_scaled = scaler.transform(X)

        if hasattr(model, "predict_proba"):
            probas = model.predict_proba(X_scaled)
            # Column index for class=1
            classes = list(model.classes_)
            pos_idx = classes.index(1) if 1 in classes else 1
            scores_arr = probas[:, pos_idx]
        else:
            raw = model.predict(X_scaled).astype(float)
            scores_arr = raw

        model_tag = f"ml_{artifact.get('model_name', 'unknown')}"
        return [
            CandidateScore(lesson_id=lid, score=float(s), source=model_tag)
            for lid, s in zip(valid_ids, scores_arr)
        ]
