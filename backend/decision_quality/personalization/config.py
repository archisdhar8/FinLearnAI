"""
Configuration constants for the learning-personalization subsystem.
All thresholds, topic taxonomies, difficulty scales, and path definitions live here.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
ARTIFACTS_DIR = HERE / "artifacts"
DATA_DIR = HERE / "data"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Topic taxonomy
# ---------------------------------------------------------------------------

TOPICS: list[str] = [
    "financial_basics",
    "compound_interest",
    "risk_tolerance",
    "volatility",
    "diversification",
    "asset_allocation",
    "etfs",
    "stock_analysis",
    "rebalancing",
    "market_mechanics",
]

# Fine-grained concept tags per topic (used for tutor question simulation)
CONCEPTS_BY_TOPIC: dict[str, list[str]] = {
    "financial_basics":    ["time_value", "interest_rates", "inflation", "principal"],
    "compound_interest":   ["compound_frequency", "future_value", "rule_of_72", "compound_formula"],
    "risk_tolerance":      ["risk_score", "loss_aversion", "risk_capacity", "risk_preference"],
    "volatility":          ["standard_deviation", "beta", "var", "volatility_meaning"],
    "diversification":     ["correlation", "uncorrelated_assets", "diversification_benefit", "idiosyncratic_risk"],
    "asset_allocation":    ["stock_bond_mix", "age_based_allocation", "target_date", "allocation_rebalancing"],
    "etfs":                ["expense_ratio", "index_tracking", "etf_types", "total_return"],
    "stock_analysis":      ["pe_ratio", "earnings", "fundamental_analysis", "technical_analysis"],
    "rebalancing":         ["drift", "rebalancing_trigger", "tax_efficiency", "threshold_rebalancing"],
    "market_mechanics":    ["market_orders", "bid_ask", "liquidity", "market_makers"],
}

# ---------------------------------------------------------------------------
# Difficulty scale  1 (intro) → 5 (expert)
# ---------------------------------------------------------------------------

DIFFICULTY_LABELS: dict[int, str] = {
    1: "intro",
    2: "beginner",
    3: "intermediate",
    4: "advanced",
    5: "expert",
}

# ---------------------------------------------------------------------------
# Mastery / quiz thresholds
# ---------------------------------------------------------------------------

MASTERY_THRESHOLD_PROFICIENT: float = 0.70   # above = proficient in topic
MASTERY_THRESHOLD_ADVANCED:   float = 0.85   # above = advanced in topic
MASTERY_THRESHOLD_WEAK:       float = 0.50   # below = needs review
QUIZ_PASS_THRESHOLD:          float = 0.70   # score needed to "pass" quiz

# Minimum mastery gain for a lesson to count as "beneficial"
TARGET_MASTERY_GAIN_THRESHOLD: float = 0.08

# Simple target: completed + score >= this
SIMPLE_TARGET_SCORE_THRESHOLD: float = 0.70

# ---------------------------------------------------------------------------
# Feature engineering windows
# ---------------------------------------------------------------------------

RECENT_QUIZ_WINDOW:    int = 5   # last N quizzes for "recent" average
RECENT_SESSION_DAYS:   int = 14  # look-back window for activity features

# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

TOP_K_RECOMMENDATIONS: int = 3

# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

RANDOM_SEED:        int = 42
N_NEGATIVE_SAMPLE:  int = 3   # negative candidates sampled per positive example

# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------

N_SYNTHETIC_USERS:   int = 3_000
MIN_SESSIONS:        int = 1
MAX_LESSONS_PER_SIM: int = 20   # hard cap so we don't simulate forever

# ---------------------------------------------------------------------------
# Available learning tools (must match frontend tool IDs)
# ---------------------------------------------------------------------------

TOOLS: list[str] = [
    "portfolio_simulator",
    "etf_recommender",
    "stock_screener",
    "ai_tutor",
]
