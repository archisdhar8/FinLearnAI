"""
Synthetic data generation entry point.

Produces:
  data/events.parquet           – raw interaction event log
  data/user_profiles.parquet    – user profiles
  data/mastery_snapshots.parquet – point-in-time mastery per (user, lesson)
  data/user_summaries.csv       – one-row-per-user aggregated summary

Run from repo root:
    python -m backend.decision_quality.personalization.synthetic.generate

Or from backend/:
    python -m decision_quality.personalization.synthetic.generate
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend/ is on sys.path when run directly
_here    = Path(__file__).resolve().parent
_backend = _here.parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import time
from typing import List

import pandas as pd

from ..config import DATA_DIR, N_SYNTHETIC_USERS, RANDOM_SEED
from ..schemas import Event
from .simulator import LearnerSimulator


def generate_all(
    n_users:  int = N_SYNTHETIC_USERS,
    seed:     int = RANDOM_SEED,
    verbose:  bool = True,
) -> None:
    """
    Generate synthetic data for `n_users` learners and write parquet/CSV files.
    """
    sim = LearnerSimulator(seed=seed)

    all_events:    List[dict] = []
    all_profiles:  List[dict] = []
    all_snapshots: List[dict] = []

    t0 = time.time()
    for i in range(n_users):
        user, events = sim.simulate_user()

        all_profiles.append(user.profile.to_dict())

        for ev in events:
            d = ev.to_dict()
            all_events.append(d)

        for snap in user.snapshots:
            all_snapshots.append({
                "user_id":       user.user_id,
                "timestamp":     snap.timestamp.isoformat(),
                "lesson_id":     snap.lesson_id,
                "topic":         snap.topic,
                "mastery_before":snap.mastery_before,
                "mastery_after": snap.mastery_after,
                "mastery_gain":  snap.mastery_after - snap.mastery_before,
            })

        if verbose and (i + 1) % 500 == 0:
            elapsed = time.time() - t0
            print(f"  Simulated {i+1}/{n_users} users  ({elapsed:.1f}s)")

    if verbose:
        print(f"Simulation complete. Total events: {len(all_events):,}")

    # ---------------------------------------------------------------
    # Save raw tables
    # ---------------------------------------------------------------
    events_df    = pd.DataFrame(all_events)
    profiles_df  = pd.DataFrame(all_profiles)
    snapshots_df = pd.DataFrame(all_snapshots)

    events_path    = DATA_DIR / "events.parquet"
    profiles_path  = DATA_DIR / "user_profiles.parquet"
    snapshots_path = DATA_DIR / "mastery_snapshots.parquet"

    events_df.to_parquet(events_path,    index=False)
    profiles_df.to_parquet(profiles_path, index=False)
    snapshots_df.to_parquet(snapshots_path, index=False)

    if verbose:
        print(f"Saved events    → {events_path}")
        print(f"Saved profiles  → {profiles_path}")
        print(f"Saved snapshots → {snapshots_path}")

    # ---------------------------------------------------------------
    # User summaries (one row per user)
    # ---------------------------------------------------------------
    if not events_df.empty:
        completed = (
            events_df[events_df["event_type"] == "lesson_completed"]
            .groupby("user_id")["lesson_id"]
            .nunique()
            .rename("lessons_completed")
        )
        quiz_avg = (
            events_df[events_df["event_type"] == "quiz_submitted"]
            .groupby("user_id")["score"]
            .mean()
            .rename("avg_quiz_score")
        )
        tutor_cnt = (
            events_df[events_df["event_type"] == "tutor_question"]
            .groupby("user_id")
            .size()
            .rename("total_tutor_questions")
        )
        summary_df = (
            profiles_df.set_index("user_id")
            .join(completed)
            .join(quiz_avg)
            .join(tutor_cnt)
            .fillna(0)
            .reset_index()
        )
        summary_path = DATA_DIR / "user_summaries.csv"
        summary_df.to_csv(summary_path, index=False)
        if verbose:
            print(f"Saved summaries → {summary_path}")

    if verbose:
        print("\n=== Summary ===")
        print(f"  Users:    {len(profiles_df):,}")
        print(f"  Events:   {len(events_df):,}")
        print(f"  Snapshots:{len(snapshots_df):,}")
        if not events_df.empty:
            print(f"  Event types:\n{events_df['event_type'].value_counts().to_string()}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate synthetic FinLearn AI learner data")
    parser.add_argument("--users",   type=int, default=N_SYNTHETIC_USERS, help="Number of users")
    parser.add_argument("--seed",    type=int, default=RANDOM_SEED,       help="Random seed")
    parser.add_argument("--quiet",   action="store_true",                  help="Suppress progress output")
    args = parser.parse_args()

    print(f"Generating {args.users} synthetic users (seed={args.seed}) …")
    generate_all(n_users=args.users, seed=args.seed, verbose=not args.quiet)
