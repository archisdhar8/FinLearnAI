"""
Lightweight CLI for the learning-personalization subsystem.

Usage
-----
  # Full pipeline (generate → train → evaluate → demo)
  python -m backend.decision_quality.personalization.cli run-all

  # Individual steps
  python -m backend.decision_quality.personalization.cli generate --users 3000
  python -m backend.decision_quality.personalization.cli train
  python -m backend.decision_quality.personalization.cli evaluate --sample-users 300
  python -m backend.decision_quality.personalization.cli demo --user-id u_<id>
  python -m backend.decision_quality.personalization.cli demo --persona engaged_learner
"""

from __future__ import annotations

import sys
from pathlib import Path

_here    = Path(__file__).resolve().parent
_backend = _here.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import argparse

import pandas as pd

from .config import DATA_DIR, N_SYNTHETIC_USERS


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_generate(args: argparse.Namespace) -> None:
    from .synthetic.generate import generate_all
    print(f"Generating {args.users} synthetic users …")
    generate_all(n_users=args.users, seed=args.seed)


def cmd_train(args: argparse.Namespace) -> None:
    from .training.train import train, DEFAULT_TARGET, SIMPLE_TARGET
    target = DEFAULT_TARGET if args.target == "mastery_gain" else SIMPLE_TARGET
    print(f"Training with target: {target.name}")
    train(target=target, rebuild_data=args.rebuild_data)


def cmd_evaluate(args: argparse.Namespace) -> None:
    from .evaluation.evaluator import compare_recommenders, educational_outcome_metrics

    events_path    = DATA_DIR / "events.parquet"
    snapshots_path = DATA_DIR / "mastery_snapshots.parquet"
    if not events_path.exists():
        print("No event data. Run: cli generate first.")
        sys.exit(1)

    events    = pd.read_parquet(events_path)
    snapshots = pd.read_parquet(snapshots_path)

    comparison = compare_recommenders(
        events, snapshots, k=args.k, sample_users=args.sample_users
    )
    print("\n=== Recommender Comparison ===")
    print(comparison.to_string())
    educational_outcome_metrics(events, snapshots)


def cmd_demo(args: argparse.Namespace) -> None:
    """Show example recommendations for a user."""
    from .inference.engine import RecommendationEngine

    events_path = DATA_DIR / "events.parquet"
    if not events_path.exists():
        print("No event data. Run: cli generate first.")
        sys.exit(1)

    events = pd.read_parquet(events_path)

    # Resolve user_id
    if args.user_id:
        user_id = args.user_id
        if user_id not in events["user_id"].unique():
            print(f"User '{user_id}' not found.")
            sys.exit(1)
    elif args.persona:
        # Pick first user of this persona
        profiles_path = DATA_DIR / "user_profiles.parquet"
        if profiles_path.exists():
            profiles = pd.read_parquet(profiles_path)
            match = profiles[profiles["persona"] == args.persona]
            if match.empty:
                print(f"No users with persona '{args.persona}'.")
                sys.exit(1)
            user_id = match.iloc[0]["user_id"]
        else:
            print("user_profiles.parquet not found.")
            sys.exit(1)
    else:
        # Pick a random user
        import numpy as np
        user_id = str(np.random.choice(events["user_id"].unique()))

    print(f"\n=== Demo: User {user_id} ===\n")

    engine = RecommendationEngine(prefer_ml=True)

    # Features
    feat_resp = engine.get_user_features_response(events, user_id)
    print(f"Lessons completed  : {feat_resp.lessons_completed}")
    print(f"Course progress    : {feat_resp.pct_course_complete:.0%}")
    print(f"Overall avg score  : {feat_resp.overall_avg_score:.0%}")
    print(f"Recent avg score   : {feat_resp.recent_avg_score:.0%}")
    print(f"Engagement         : {feat_resp.engagement_score:.2f}")
    print(f"Weak topics        : {feat_resp.top_weak_topics}")
    print(f"Strong topics      : {feat_resp.top_strong_topics}")

    # Mastery map
    mastery_resp = engine.get_topic_mastery_response(events, user_id)
    print("\nTopic mastery:")
    for topic, score in sorted(mastery_resp.mastery_map.items(), key=lambda x: x[1]):
        bar = "█" * int(score * 20)
        print(f"  {topic:25s} {score:.0%}  {bar}")

    # Readiness
    readiness = engine.get_readiness(events, user_id)
    print(f"\nReadiness score    : {readiness.readiness_score:.2f}")
    print(f"Ready for next mod : {readiness.ready_for_next_module}")
    print(f"Should review prereq: {readiness.should_review_prereq}")
    if readiness.suggested_tool:
        print(f"Suggested tool     : {readiness.suggested_tool}")
    print(f"Notes              : {readiness.notes}")

    # Recommendations
    recs = engine.recommend(events, user_id, k=3)
    if not recs:
        print("\nNo eligible lessons remaining.")
    else:
        print(f"\nTop {len(recs)} recommendation(s):")
        for i, rec in enumerate(recs, 1):
            print(f"\n  [{i}] {rec.lesson_id}: {rec.title}")
            print(f"      Topic: {rec.topic}  |  Difficulty: {rec.difficulty}  |  Confidence: {rec.confidence:.0%}")
            print(f"      {rec.explanation}")
            if rec.alternatives:
                print(f"      Alternatives: {[a.lesson_id for a in rec.alternatives]}")


def cmd_run_all(args: argparse.Namespace) -> None:
    """Full pipeline: generate → train → evaluate → demo."""
    print("=" * 60)
    print("Step 1 / 4  –  Generate synthetic data")
    print("=" * 60)
    args.users = getattr(args, "users", N_SYNTHETIC_USERS)
    args.seed  = getattr(args, "seed",  42)
    cmd_generate(args)

    print("\n" + "=" * 60)
    print("Step 2 / 4  –  Train models")
    print("=" * 60)
    args.target       = "mastery_gain"
    args.rebuild_data = True
    cmd_train(args)

    print("\n" + "=" * 60)
    print("Step 3 / 4  –  Evaluate")
    print("=" * 60)
    args.k            = 3
    args.sample_users = 300
    cmd_evaluate(args)

    print("\n" + "=" * 60)
    print("Step 4 / 4  –  Demo recommendations")
    print("=" * 60)
    args.user_id = None
    args.persona = "engaged_learner"
    cmd_demo(args)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="personalization",
        description="FinLearn AI learning-personalization CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # generate
    p_gen = sub.add_parser("generate", help="Generate synthetic learner data")
    p_gen.add_argument("--users", type=int, default=N_SYNTHETIC_USERS)
    p_gen.add_argument("--seed",  type=int, default=42)

    # train
    p_train = sub.add_parser("train", help="Train recommendation models")
    p_train.add_argument(
        "--target", choices=["mastery_gain", "completion_score"],
        default="mastery_gain",
    )
    p_train.add_argument("--rebuild-data", action="store_true")

    # evaluate
    p_eval = sub.add_parser("evaluate", help="Evaluate recommenders")
    p_eval.add_argument("--k",            type=int, default=3)
    p_eval.add_argument("--sample-users", type=int, default=300)

    # demo
    p_demo = sub.add_parser("demo", help="Show recommendations for a user")
    g = p_demo.add_mutually_exclusive_group()
    g.add_argument("--user-id", type=str)
    g.add_argument("--persona", type=str)

    # run-all
    p_all = sub.add_parser("run-all", help="Full pipeline: generate → train → evaluate → demo")
    p_all.add_argument("--users", type=int, default=N_SYNTHETIC_USERS)
    p_all.add_argument("--seed",  type=int, default=42)

    args = parser.parse_args()

    dispatch = {
        "generate": cmd_generate,
        "train":    cmd_train,
        "evaluate": cmd_evaluate,
        "demo":     cmd_demo,
        "run-all":  cmd_run_all,
    }

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
