"""
Training set construction for the next-best-lesson ranking model.

Candidate-ranking setup
-----------------------
For each (user, lesson) where the user actually completed a lesson:
  - Build a positive row with features computed at lesson_start time.
  - Sample N_NEGATIVE_SAMPLE eligible lessons the user did NOT take at that
    decision point and build negative rows.

Each row contains:
  - User-level features (as-of lesson start)
  - Topic-level mastery features (for the candidate's topic, as-of lesson start)
  - Candidate lesson features
  - Interaction features (user × candidate)
  - Label (0 or 1)
"""

from __future__ import annotations

import sys
from pathlib import Path

_here    = Path(__file__).resolve().parent
_backend = _here.parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..config import (
    DATA_DIR,
    N_NEGATIVE_SAMPLE,
    RANDOM_SEED,
)
from ..content_meta import (
    LESSON_BY_ID,
    LESSON_ORDER,
    get_eligible_lessons,
)
from ..feature_engineering import ALL_FEATURE_COLS, build_feature_row
from .targets import DEFAULT_TARGET, LabelDefinition


def build_training_dataset(
    events:    pd.DataFrame,
    snapshots: pd.DataFrame,
    target:    Optional[LabelDefinition] = None,
    seed:      int = RANDOM_SEED,
    verbose:   bool = True,
) -> pd.DataFrame:
    """
    Build a flat training DataFrame from event logs and mastery snapshots.

    Parameters
    ----------
    events    : raw events (from generate.py)
    snapshots : mastery snapshots (from generate.py)
    target    : label definition to use (defaults to MasteryGainTarget)
    seed      : random seed for negative sampling

    Returns
    -------
    DataFrame with columns = ALL_FEATURE_COLS + ["label", "_user_id", "_lesson_id", "_topic"]
    """
    if target is None:
        target = DEFAULT_TARGET

    rng = np.random.default_rng(seed)
    rows: List[Dict] = []

    # Unique users
    user_ids = events["user_id"].unique().tolist()
    if verbose:
        print(f"Building training set for {len(user_ids):,} users (target: {target.name})")

    for i, user_id in enumerate(user_ids):
        u_events = events[events["user_id"] == user_id].copy()
        u_events["timestamp"] = pd.to_datetime(u_events["timestamp"], utc=True, format="mixed")
        u_events = u_events.sort_values("timestamp")

        # Get all lesson_started events for this user
        started = u_events[u_events["event_type"] == "lesson_started"].copy()
        if started.empty:
            continue

        for _, start_row in started.iterrows():
            lesson_id  = start_row.get("lesson_id")
            if not lesson_id or lesson_id not in LESSON_BY_ID:
                continue
            as_of_ts   = pd.to_datetime(start_row["timestamp"], utc=True)

            # Compute positive label for the lesson actually taken
            pos_label = target.label(user_id, lesson_id, u_events, snapshots)
            if pos_label is None:
                continue   # No completion → skip this decision point

            # Build feature row for the actual lesson (positive OR negative)
            try:
                row = build_feature_row(u_events, user_id, lesson_id, as_of=as_of_ts)
            except Exception:
                continue
            row["label"] = pos_label
            rows.append(row)

            if pos_label == 0:
                continue   # No need to sample negatives for an already-negative example

            # --- Sample negative candidates ---
            # Get completed set just before this lesson start
            completed_before = set(
                u_events[
                    (u_events["event_type"] == "lesson_completed")
                    & (u_events["timestamp"] < as_of_ts)
                ]["lesson_id"].dropna().unique()
            )
            eligible = get_eligible_lessons(completed_before)
            neg_candidates = [l for l in eligible if l.lesson_id != lesson_id]

            if neg_candidates:
                sample_size = min(N_NEGATIVE_SAMPLE, len(neg_candidates))
                sampled = rng.choice(len(neg_candidates), size=sample_size, replace=False)
                for idx in sampled:
                    cand = neg_candidates[int(idx)]
                    try:
                        neg_row = build_feature_row(
                            u_events, user_id, cand.lesson_id, as_of=as_of_ts
                        )
                    except Exception:
                        continue
                    neg_row["label"] = 0
                    rows.append(neg_row)

        if verbose and (i + 1) % 500 == 0:
            print(f"  Processed {i+1}/{len(user_ids)} users  ({len(rows):,} rows so far)")

    df = pd.DataFrame(rows)
    if verbose:
        print(f"Training set: {len(df):,} rows  |  label dist: {df['label'].value_counts().to_dict()}")
    return df


def save_training_dataset(df: pd.DataFrame, name: str = "training_set") -> Path:
    """Save training DataFrame to data directory."""
    path = DATA_DIR / f"{name}.parquet"
    df.to_parquet(path, index=False)
    print(f"Saved training set → {path}")
    return path


def load_training_dataset(name: str = "training_set") -> pd.DataFrame:
    """Load training DataFrame from data directory."""
    path = DATA_DIR / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"Training set not found at {path}. "
            "Run the generate + build pipeline first."
        )
    return pd.read_parquet(path)
