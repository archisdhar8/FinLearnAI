from __future__ import annotations

"""
Synthetic dataset generation for ETF decision-quality.

Run from the backend directory (so backend/ is on PYTHONPATH):

    cd /path/to/FinLearnAI/backend
    python -m decision_quality.etf_dataset_generate

Or from repo root:

    cd /path/to/FinLearnAI
    PYTHONPATH=. python -m backend.decision_quality.etf_dataset_generate
"""

import sys
from pathlib import Path

# When run as __main__ from backend/, project root may not be on path
_here = Path(__file__).resolve().parent
_backend = _here.parent
_root = _backend.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from decision_quality.etf_features import EtfContext, TICKERS, portfolio_summary_features
from decision_quality.etf_rules_oracle import etf_oracle


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _random_context(rng: np.random.Generator) -> EtfContext:
    # Risk scores skewed slightly toward middle
    risk = float(np.clip(rng.beta(2.0, 2.0), 0.0, 1.0))
    # Horizon loosely correlated with risk (more risk often with longer view)
    base_years = 1 + rng.exponential(8.0)
    horizon = float(np.clip(base_years + 20.0 * risk, 1.0, 40.0))
    return EtfContext(risk_score=risk, time_horizon_years=horizon)


def _random_allocation(rng: np.random.Generator) -> Dict[str, float]:
    # Dirichlet over ETFs for a realistic random portfolio
    alpha = np.ones(len(TICKERS), dtype=float)
    # Bias toward a subset of tickers for concentration variety
    chosen = rng.choice(len(TICKERS), size=rng.integers(3, min(10, len(TICKERS))), replace=False)
    alpha[:] = 0.2
    alpha[chosen] = 1.5
    w = rng.dirichlet(alpha)
    return {ticker: float(weight) for ticker, weight in zip(TICKERS, w)}


def generate_dataset(n_samples: int = 20_000, seed: int = 42) -> Path:
    rng = np.random.default_rng(seed)
    rows: List[Dict] = []

    for _ in range(n_samples):
        ctx = _random_context(rng)
        alloc = _random_allocation(rng)
        feats, names = portfolio_summary_features(ctx, alloc)
        oracle_res = etf_oracle(ctx, alloc)

        row = {name: feats[i] for i, name in enumerate(names)}
        row.update(
            {
                "risk_score": ctx.risk_score,
                "time_horizon_years": ctx.time_horizon_years,
                "label": oracle_res.label,
            }
        )
        rows.append(row)

    df = pd.DataFrame(rows)
    out_path = DATA_DIR / "etf_decision_quality.csv"
    df.to_csv(out_path, index=False)
    return out_path


if __name__ == "__main__":
    path = generate_dataset(n_samples=20_000)
    print(f"Wrote synthetic dataset to {path}")

