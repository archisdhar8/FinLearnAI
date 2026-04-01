"""
Model training script for the next-best-lesson personalization model.

Trains three models and saves them to artifacts/:
  1. Logistic Regression (fast baseline)
  2. Random Forest
  3. Gradient Boosting (primary model, best accuracy)

Usage
-----
From repo root:
    python -m backend.decision_quality.personalization.training.train

From backend/:
    python -m decision_quality.personalization.training.train

Flags:
  --target  mastery_gain | completion_score  (default: mastery_gain)
  --rebuild-data   re-run synthetic generation before training
"""

from __future__ import annotations

import sys
from pathlib import Path

_here    = Path(__file__).resolve().parent
_backend = _here.parent.parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

import argparse
import warnings
warnings.filterwarnings("ignore")

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

from ..config import ARTIFACTS_DIR, DATA_DIR, RANDOM_SEED
from ..feature_engineering import ALL_FEATURE_COLS
from .dataset_builder import build_training_dataset, load_training_dataset, save_training_dataset
from .targets import DEFAULT_TARGET, SIMPLE_TARGET, LabelDefinition


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

def _make_models() -> dict:
    return {
        "logistic_regression": LogisticRegression(
            C=1.0, max_iter=500, random_state=RANDOM_SEED, class_weight="balanced"
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=150, max_depth=8, min_samples_leaf=10,
            random_state=RANDOM_SEED, class_weight="balanced", n_jobs=-1,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=150, max_depth=4, min_samples_leaf=15,
            learning_rate=0.08, subsample=0.85, random_state=RANDOM_SEED,
        ),
    }


# ---------------------------------------------------------------------------
# Training pipeline
# ---------------------------------------------------------------------------

def train(
    target:      LabelDefinition = DEFAULT_TARGET,
    rebuild_data: bool = False,
    verbose:     bool = True,
) -> dict:
    """
    Full training pipeline: load data → featurise → train → evaluate → save.

    Returns dict of {model_name: artifact_path}.
    """
    # ------------------------------------------------------------------
    # 1. Load or build training data
    # ------------------------------------------------------------------
    train_set_name = f"training_set_{target.name}"
    train_path = DATA_DIR / f"{train_set_name}.parquet"

    if rebuild_data or not train_path.exists():
        if verbose:
            print("Loading raw events and snapshots …")
        events_path    = DATA_DIR / "events.parquet"
        snapshots_path = DATA_DIR / "mastery_snapshots.parquet"
        if not events_path.exists():
            raise FileNotFoundError(
                f"{events_path} not found. "
                "Run:  python -m backend.decision_quality.personalization.synthetic.generate"
            )
        events    = pd.read_parquet(events_path)
        snapshots = pd.read_parquet(snapshots_path)

        if verbose:
            print(f"Events: {len(events):,}   Snapshots: {len(snapshots):,}")

        df = build_training_dataset(events, snapshots, target=target, verbose=verbose)
        save_training_dataset(df, name=train_set_name)
    else:
        if verbose:
            print(f"Loading existing training set from {train_path}")
        df = pd.read_parquet(train_path)

    if verbose:
        print(f"Training rows: {len(df):,}   Label dist: {df['label'].value_counts().to_dict()}")

    # ------------------------------------------------------------------
    # 2. Prepare feature matrix
    # ------------------------------------------------------------------
    # Use only columns that exist in this dataset
    feature_cols = [c for c in ALL_FEATURE_COLS if c in df.columns]
    missing_cols = [c for c in ALL_FEATURE_COLS if c not in df.columns]
    if missing_cols and verbose:
        print(f"  Warning: {len(missing_cols)} feature cols missing (will be zeroed): {missing_cols[:5]}…")
    for col in missing_cols:
        df[col] = 0.0

    X = df[ALL_FEATURE_COLS].fillna(0.0).values.astype(float)
    y = df["label"].values.astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_SEED, stratify=y
    )
    if verbose:
        print(f"Train: {len(X_train):,}  Test: {len(X_test):,}")

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    sample_weights = compute_sample_weight("balanced", y_train)

    # ------------------------------------------------------------------
    # 3. Train each model
    # ------------------------------------------------------------------
    models = _make_models()
    artifact_paths: dict = {}

    for model_name, model in models.items():
        if verbose:
            print(f"\nTraining {model_name} …")

        # GBM accepts sample_weight; others accept it via fit kwargs
        fit_kwargs: dict = {}
        if hasattr(model, "fit") and model_name != "logistic_regression":
            try:
                model.fit(X_train_s, y_train, sample_weight=sample_weights)
            except TypeError:
                model.fit(X_train_s, y_train)
        else:
            model.fit(X_train_s, y_train)

        # CV score
        cv_scores = cross_val_score(
            model, X_train_s, y_train, cv=5, scoring="roc_auc"
        )
        if verbose:
            print(f"  5-fold CV AUC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

        # Test evaluation
        y_pred  = model.predict(X_test_s)
        y_proba = model.predict_proba(X_test_s)[:, 1] if hasattr(model, "predict_proba") else None
        if verbose:
            print(classification_report(y_test, y_pred, zero_division=0))
            if y_proba is not None:
                print(f"  Test AUC: {roc_auc_score(y_test, y_proba):.3f}")

        # Feature importance (GBM / RF)
        if hasattr(model, "feature_importances_") and verbose:
            importance = pd.Series(
                model.feature_importances_, index=ALL_FEATURE_COLS
            ).sort_values(ascending=False)
            print(f"\n  Top-10 features:\n{importance.head(10).to_string()}")

        # Save artifact
        artifact = {
            "model":        model,
            "scaler":       scaler,
            "feature_cols": ALL_FEATURE_COLS,
            "target":       target.name,
            "model_name":   model_name,
        }
        art_path = ARTIFACTS_DIR / f"personalization_{model_name}.pkl"
        joblib.dump(artifact, art_path)
        artifact_paths[model_name] = art_path
        if verbose:
            print(f"  Saved → {art_path}")

    # Save scaler separately for quick reload
    joblib.dump(scaler, ARTIFACTS_DIR / "personalization_scaler.pkl")

    return artifact_paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train FinLearn personalization model")
    parser.add_argument(
        "--target",
        choices=["mastery_gain", "completion_score"],
        default="mastery_gain",
        help="Label definition to use",
    )
    parser.add_argument(
        "--rebuild-data", action="store_true",
        help="Rebuild training set from raw events (slow)",
    )
    args = parser.parse_args()

    target = DEFAULT_TARGET if args.target == "mastery_gain" else SIMPLE_TARGET
    train(target=target, rebuild_data=args.rebuild_data)
