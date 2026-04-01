from __future__ import annotations

"""
Runtime helper for ETF decision-quality evaluation.

This is intentionally NOT wired into FastAPI yet. It can be imported by future
API endpoints to provide ML-backed (or rule-backed) feedback for ETF
allocations.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import joblib
import numpy as np

try:
    from backend.decision_quality.etf_features import EtfContext, portfolio_summary_features
    from backend.decision_quality.etf_rules_oracle import OracleResult, etf_oracle
except ModuleNotFoundError:
    from decision_quality.etf_features import EtfContext, portfolio_summary_features
    from decision_quality.etf_rules_oracle import OracleResult, etf_oracle


ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "etf_decision_quality.pkl"

_artifact_cache: Optional[dict] = None


@dataclass
class DecisionQualityOutput:
    label: str
    reason: str
    score: Optional[float] = None  # optional confidence score
    source: str = "rule"  # \"ml\" or \"rule\"


def _load_artifact() -> Optional[dict]:
    global _artifact_cache
    if _artifact_cache is None and MODEL_PATH.exists():
        _artifact_cache = joblib.load(MODEL_PATH)
    return _artifact_cache


def evaluate_etf_allocation(ctx: EtfContext, allocation: Dict[str, float]) -> DecisionQualityOutput:
    """
    Evaluate an ETF allocation. If an ML model artifact is available, use it;
    otherwise fall back to the rule-based oracle.
    """
    artifact = _load_artifact()
    if artifact is None:
        oracle = etf_oracle(ctx, allocation)
        return DecisionQualityOutput(
            label=oracle.label,
            reason=oracle.reason,
            score=None,
            source="rule",
        )

    features, names = portfolio_summary_features(ctx, allocation)
    scaler = artifact["scaler"]
    model = artifact["model"]
    feature_cols = artifact.get("features", names)

    # Ensure ordering / subset is consistent; here we assume same ordering
    X = features.reshape(1, -1)
    X_scaled = scaler.transform(X)

    proba = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_scaled)[0]
        classes = list(model.classes_)
        idx = int(np.argmax(proba))
        label = str(classes[idx])
        score = float(proba[idx])
    else:
        label = str(model.predict(X_scaled)[0])
        score = None

    # For now the \"reason\" comes from the oracle even when ML chooses the class.
    # This keeps explanations consistent and simple.
    oracle = etf_oracle(ctx, allocation)
    return DecisionQualityOutput(
        label=label,
        reason=oracle.reason,
        score=score,
        source="ml" if artifact is not None else "rule",
    )


__all__ = ["DecisionQualityOutput", "evaluate_etf_allocation"]

