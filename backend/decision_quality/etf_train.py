from __future__ import annotations

"""
Training script for the ETF decision-quality classifier.

Run from the backend directory:

    cd /path/to/FinLearnAI/backend
    python -m decision_quality.etf_dataset_generate   # create data first
    python -m decision_quality.etf_train

Writes the model to decision_quality/models/etf_decision_quality.pkl.

Note: Labels come from a deterministic rule oracle, so a flexible model can
reach very high accuracy on the same synthetic distribution. We use
regularization (shallow trees, min_samples_leaf) and report cross-validation
to reduce overfitting and to spot instability on rare classes.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "etf_decision_quality.csv"
MODEL_DIR = ROOT / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODEL_DIR / "etf_decision_quality.pkl"

FEATURE_COLS = [
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


def train() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run etf_dataset_generate.py first."
        )

    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_COLS].values.astype(float)
    y = df["label"].astype(str).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    n_train, n_test = len(X_train), len(X_test)
    print(f"Training set: {n_train} | Test set: {n_test}")

    unique, counts = np.unique(y_train, return_counts=True)
    print("Train class counts:", dict(zip(unique, counts.tolist())))

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Balanced sample weights so rare classes count more in the loss
    sample_weight = compute_sample_weight("balanced", y_train)

    # Regularized GBM to avoid overfitting to the synthetic oracle distribution
    clf = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=4,
        min_samples_leaf=20,
        learning_rate=0.08,
        subsample=0.85,
        random_state=42,
    )
    clf.fit(X_train_scaled, y_train, sample_weight=sample_weight)

    # Cross-validation (unweighted) to see stability
    scores = cross_val_score(clf, X_train_scaled, y_train, cv=5, scoring="accuracy")
    print(f"5-fold CV accuracy (train): {scores.mean():.3f} ± {scores.std():.3f}")

    y_pred = clf.predict(X_test_scaled)
    print("\nClassification report (test holdout) vs oracle labels:")
    print(classification_report(y_test, y_pred, zero_division=0))

    artifact = {"scaler": scaler, "model": clf, "features": FEATURE_COLS}
    joblib.dump(artifact, MODEL_PATH)
    print(f"Saved model artifact to {MODEL_PATH}")


if __name__ == "__main__":
    train()

