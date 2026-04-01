from __future__ import annotations

"""
Feature construction for ETF decision-quality modelling.

This module converts a (risk_score, optional horizon, allocation dict) into
numeric features suitable for ML models or rule-based oracles.

Allocations are expressed as a mapping from ETF ticker -> weight in [0, 1].
Weights do not need to sum exactly to 1; we renormalise inside
`normalise_allocation`.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

# Import from ga_etf_optimizer in parent dir (backend)
try:
    from backend.ga_etf_optimizer import ETF_UNIVERSE, _target_equity_weight
except ModuleNotFoundError:
    from ga_etf_optimizer import ETF_UNIVERSE, _target_equity_weight


# Build lookup tables from ETF_UNIVERSE defined in ga_etf_optimizer
TICKERS: List[str] = [etf["ticker"] for etf in ETF_UNIVERSE]
ASSET_CLASS: List[str] = [etf["asset_class"] for etf in ETF_UNIVERSE]
IS_EQUITY_VEC = np.array([1.0 if a == "equity" else 0.0 for a in ASSET_CLASS], dtype=float)


@dataclass
class EtfContext:
    """User context relevant for ETF decisions."""

    risk_score: float  # 0–1 from questionnaire
    time_horizon_years: float | None = None  # optional explicit horizon


def normalise_allocation(allocation: Dict[str, float]) -> np.ndarray:
    """
    Convert arbitrary ticker->weight mapping into a dense vector over TICKERS.

    - Unknown tickers are ignored.
    - Negative weights are clipped to 0.
    - If all weights are 0, we return equal weights.
    - Otherwise we renormalise to sum=1.
    """
    w = np.zeros(len(TICKERS), dtype=float)
    for i, ticker in enumerate(TICKERS):
        raw = float(allocation.get(ticker, 0.0))
        if raw > 0:
            w[i] = raw
    s = float(w.sum())
    if s <= 0:
        # Default to equal-weight portfolio if nothing was allocated
        return np.ones_like(w) / len(w)
    return w / s


def portfolio_summary_features(
    ctx: EtfContext, allocation: Dict[str, float]
) -> Tuple[np.ndarray, List[str]]:
    """
    Build a compact feature vector capturing how the allocation relates to the
    user's risk profile.

    Features (all floats unless stated otherwise):
    - risk_score
    - time_horizon_years (or -1 if None)
    - equity_pct  (sum of weights where asset_class == equity)
    - bond_pct    (1 - equity_pct, treating everything non-equity as defensive)
    - max_single_etf_weight
    - num_etfs (count of positions with weight > 1%)
    - target_equity_weight (from GA risk model)
    - equity_gap = equity_pct - target_equity_weight
    - concentration_hhi (Herfindahl index)
    """
    w = normalise_allocation(allocation)

    equity_pct = float(w @ IS_EQUITY_VEC)
    bond_pct = 1.0 - equity_pct

    max_single = float(w.max())
    num_etfs = float((w > 0.01).sum())

    target_equity = float(_target_equity_weight(ctx.risk_score))
    equity_gap = equity_pct - target_equity

    hhi = float(np.sum(w ** 2))

    horizon = float(ctx.time_horizon_years) if ctx.time_horizon_years is not None else -1.0

    features = np.array(
        [
            float(ctx.risk_score),
            horizon,
            equity_pct,
            bond_pct,
            max_single,
            num_etfs,
            target_equity,
            equity_gap,
            hhi,
        ],
        dtype=float,
    )

    names = [
        "risk_score",
        "time_horizon_years",
        "equity_pct",
        "bond_pct",
        "max_single_etf_weight",
        "num_etfs",
        "target_equity_weight",
        "equity_gap",
        "concentration_hhi",
    ]
    return features, names

