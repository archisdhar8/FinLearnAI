"""
Offline evaluation pipeline.

Compares heuristic vs ML recommender across held-out user sequences.

Metrics
-------
- Precision@K   : fraction of top-K recommendations that are "good" (label=1)
- Recall@K      : fraction of all "good" lessons covered in top-K
- nDCG@K        : normalised discounted cumulative gain for ranking
- Mastery gain  : average mastery gain for users who followed the recommendation
- Completion rate: fraction of recommended lessons that were completed
"""

from __future__ import annotations

import sys
from pathlib import Path

_here    = Path(__file__).resolve().parent
_backend = _here.parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..config import DATA_DIR, RANDOM_SEED, TOP_K_RECOMMENDATIONS
from ..content_meta import LESSON_BY_ID
from ..models.base import BaseRecommender
from ..models.heuristic import HeuristicRecommender
from ..models.ml_recommender import MLRecommender
from ..training.targets import DEFAULT_TARGET, LabelDefinition


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def precision_at_k(ranked: List[str], relevant: set[str], k: int) -> float:
    top_k = ranked[:k]
    hits = sum(1 for lid in top_k if lid in relevant)
    return hits / k if k > 0 else 0.0


def recall_at_k(ranked: List[str], relevant: set[str], k: int) -> float:
    top_k = ranked[:k]
    hits = sum(1 for lid in top_k if lid in relevant)
    return hits / len(relevant) if relevant else 0.0


def ndcg_at_k(ranked: List[str], relevant: set[str], k: int) -> float:
    """Normalised DCG@K with binary relevance."""
    dcg = 0.0
    for i, lid in enumerate(ranked[:k]):
        if lid in relevant:
            dcg += 1.0 / np.log2(i + 2)

    ideal_hits = min(k, len(relevant))
    idcg = sum(1.0 / np.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------

def evaluate_recommender(
    recommender: BaseRecommender,
    events:      pd.DataFrame,
    snapshots:   pd.DataFrame,
    target:      Optional[LabelDefinition] = None,
    k:           int = TOP_K_RECOMMENDATIONS,
    sample_users: Optional[int] = None,
    seed:        int = RANDOM_SEED,
) -> Dict[str, float]:
    """
    Replay offline evaluation.

    For each user in the holdout set, at each lesson-start decision point:
    - Ask the recommender for its top-K
    - Compare against ground-truth label for each candidate

    Returns averaged metric dict.
    """
    if target is None:
        target = DEFAULT_TARGET

    rng = np.random.default_rng(seed)

    user_ids = events["user_id"].unique().tolist()
    if sample_users and sample_users < len(user_ids):
        user_ids = rng.choice(user_ids, size=sample_users, replace=False).tolist()

    results: List[Dict[str, float]] = []

    for user_id in user_ids:
        u_events = events[events["user_id"] == user_id].copy()
        u_events["timestamp"] = pd.to_datetime(u_events["timestamp"], utc=True, format="mixed")
        u_events = u_events.sort_values("timestamp")

        started = u_events[u_events["event_type"] == "lesson_started"].copy()
        if started.empty:
            continue

        for _, start_row in started.iterrows():
            lesson_id = start_row.get("lesson_id")
            if not lesson_id or lesson_id not in LESSON_BY_ID:
                continue

            as_of_ts = pd.to_datetime(start_row["timestamp"], utc=True)

            # Ground-truth: which eligible lessons were "good" at this point?
            completed_before = set(
                u_events[
                    (u_events["event_type"] == "lesson_completed")
                    & (u_events["timestamp"] < as_of_ts)
                ]["lesson_id"].dropna().unique()
            )
            from ..content_meta import get_eligible_lessons
            eligible = get_eligible_lessons(completed_before)
            eligible_ids = [l.lesson_id for l in eligible]

            if not eligible_ids:
                continue

            # Label each eligible lesson
            relevant: set[str] = set()
            for cand_id in eligible_ids:
                lbl = target.label(user_id, cand_id, u_events, snapshots)
                if lbl == 1:
                    relevant.add(cand_id)

            if not relevant:
                continue

            # Get recommender's ranked list (score on history UP TO as_of_ts)
            history = u_events[u_events["timestamp"] <= as_of_ts]
            try:
                scored = recommender.score_candidates(
                    history, user_id, candidates=eligible_ids
                )
            except Exception:
                continue

            ranked = [c.lesson_id for c in sorted(scored, key=lambda c: c.score, reverse=True)]

            results.append({
                "precision_at_k": precision_at_k(ranked, relevant, k),
                "recall_at_k":    recall_at_k(ranked, relevant, k),
                "ndcg_at_k":      ndcg_at_k(ranked, relevant, k),
                "top1_correct":   float(bool(ranked and ranked[0] in relevant)),
            })

    if not results:
        return {
            "precision_at_k": 0.0, "recall_at_k": 0.0,
            "ndcg_at_k": 0.0, "top1_correct": 0.0, "n_decisions": 0,
        }

    df_res = pd.DataFrame(results)
    summary = {col: float(df_res[col].mean()) for col in df_res.columns}
    summary["n_decisions"] = len(results)
    return summary


def compare_recommenders(
    events:    pd.DataFrame,
    snapshots: pd.DataFrame,
    k:         int = TOP_K_RECOMMENDATIONS,
    sample_users: Optional[int] = 300,
    verbose:   bool = True,
) -> pd.DataFrame:
    """
    Compare heuristic vs ML recommender and return a metrics DataFrame.
    """
    recommenders: List[BaseRecommender] = [
        HeuristicRecommender(),
        MLRecommender(),
    ]

    rows: List[Dict] = []
    for rec in recommenders:
        if verbose:
            print(f"Evaluating {rec.name} …")
        metrics = evaluate_recommender(
            rec, events, snapshots,
            k=k, sample_users=sample_users
        )
        metrics["recommender"] = rec.name
        rows.append(metrics)
        if verbose:
            print(f"  P@{k}={metrics['precision_at_k']:.3f}  "
                  f"R@{k}={metrics['recall_at_k']:.3f}  "
                  f"nDCG@{k}={metrics['ndcg_at_k']:.3f}  "
                  f"Top-1={metrics['top1_correct']:.3f}  "
                  f"n={metrics['n_decisions']}")

    return pd.DataFrame(rows).set_index("recommender")


def educational_outcome_metrics(
    events:    pd.DataFrame,
    snapshots: pd.DataFrame,
    verbose:   bool = True,
) -> Dict[str, Any]:
    """
    Educational outcome metrics derived from mastery snapshots:
      - avg_mastery_gain_per_lesson
      - pct_lessons_above_gain_threshold
      - topic_mastery_distribution
    """
    from ..config import TARGET_MASTERY_GAIN_THRESHOLD

    if snapshots.empty:
        return {}

    avg_gain = float(snapshots["mastery_gain"].mean())
    pct_above = float((snapshots["mastery_gain"] >= TARGET_MASTERY_GAIN_THRESHOLD).mean())

    topic_avg = snapshots.groupby("topic")["mastery_after"].mean().to_dict()

    # Completion rate: fraction of started lessons that were completed
    started   = int((events["event_type"] == "lesson_started").sum())
    completed = int((events["event_type"] == "lesson_completed").sum())
    completion_rate = completed / started if started > 0 else 0.0

    metrics = {
        "avg_mastery_gain_per_lesson":    avg_gain,
        "pct_lessons_above_gain_threshold": pct_above,
        "overall_completion_rate":        completion_rate,
        "topic_final_mastery":            topic_avg,
    }
    if verbose:
        print("\n=== Educational Outcome Metrics ===")
        for k, v in metrics.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.3f}")
            elif isinstance(v, dict):
                print(f"  {k}:")
                for t, mv in sorted(v.items()):
                    print(f"    {t:30s}: {mv:.3f}")
    return metrics


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate personalization recommenders")
    parser.add_argument("--sample-users", type=int, default=300)
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()

    events_path    = DATA_DIR / "events.parquet"
    snapshots_path = DATA_DIR / "mastery_snapshots.parquet"

    if not events_path.exists():
        print("No event data found. Run the synthetic generator first.")
        sys.exit(1)

    events    = pd.read_parquet(events_path)
    snapshots = pd.read_parquet(snapshots_path)

    print(f"Events: {len(events):,}  Snapshots: {len(snapshots):,}\n")

    comparison = compare_recommenders(
        events, snapshots, k=args.k, sample_users=args.sample_users
    )
    print("\n=== Recommender Comparison ===")
    print(comparison.to_string())

    educational_outcome_metrics(events, snapshots)
