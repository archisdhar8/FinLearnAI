from __future__ import annotations

"""
Rule-based oracle for ETF decision-quality labels.

This is the \"ground truth\" used for:
- direct rule-based feedback, and
- generating labels for the ML model.
"""

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

try:
    from backend.ga_etf_optimizer import _risk_profile_label, _target_equity_weight
except ModuleNotFoundError:
    from ga_etf_optimizer import _risk_profile_label, _target_equity_weight
from decision_quality.etf_features import IS_EQUITY_VEC, TICKERS, EtfContext, normalise_allocation


@dataclass(frozen=True)
class OracleResult:
    label: str
    reason: str


def _equity_pct(weights: np.ndarray) -> float:
    return float(weights @ IS_EQUITY_VEC)


def _concentration_hhi(weights: np.ndarray) -> float:
    return float(np.sum(weights ** 2))


def etf_oracle(ctx: EtfContext, allocation: Dict[str, float]) -> OracleResult:
    """
    Classify an ETF allocation given a user's context into one of a few
    coarse decision-quality classes.

    Labels:
    - \"good_fit\": broadly aligned with risk score and reasonably diversified
    - \"too_risky\": equity far above risk-based target
    - \"too_conservative\": equity far below target for aggressive profile
    - \"concentrated\": over-concentrated in a single ETF
    - \"mismatch_goals\": extreme mismatch vs. time horizon
    """
    w = normalise_allocation(allocation)
    equity = _equity_pct(w)
    hhi = _concentration_hhi(w)
    max_weight = float(w.max())
    num_etfs = int((w > 0.01).sum())

    target_equity = float(_target_equity_weight(ctx.risk_score))
    equity_gap = equity - target_equity

    profile = _risk_profile_label(ctx.risk_score)

    # --- Heuristics --------------------------------------------------------

    # 1) Goal / horizon mismatch
    if ctx.time_horizon_years is not None:
        horizon = ctx.time_horizon_years
        if horizon < 3 and equity > 0.7:
            return OracleResult(
                label="mismatch_goals",
                reason="Very short time horizon with high equity exposure.",
            )
        if horizon > 20 and equity < 0.3:
            return OracleResult(
                label="too_conservative",
                reason="Long time horizon with very low equity exposure.",
            )

    # 2) Concentration
    if num_etfs <= 2 or max_weight > 0.6 or hhi > 0.35:
        return OracleResult(
            label="concentrated",
            reason="Portfolio is highly concentrated in a small number of ETFs.",
        )

    # 3) Risk score mismatch – aggressive vs conservative
    # equity_gap positive => portfolio more aggressive than target
    if equity_gap > 0.25:
        return OracleResult(
            label="too_risky",
            reason="Equity allocation is much higher than suggested by your risk score.",
        )
    if equity_gap < -0.25:
        return OracleResult(
            label="too_conservative",
            reason="Equity allocation is much lower than suggested by your risk score.",
        )

    # 4) Fine-tune around moderate profiles
    if profile in {"Conservative", "Moderate"} and equity > 0.75:
        return OracleResult(
            label="too_risky",
            reason=f"Profile {profile} with very high equity allocation.",
        )

    if profile in {"Growth", "Aggressive"} and equity < 0.4:
        return OracleResult(
            label="too_conservative",
            reason=f"Profile {profile} with relatively low equity allocation.",
        )

    return OracleResult(
        label="good_fit",
        reason="Allocation is broadly aligned with risk score and reasonably diversified.",
    )


__all__ = ["OracleResult", "etf_oracle"]

