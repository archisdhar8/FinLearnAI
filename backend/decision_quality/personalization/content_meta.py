"""
Static content metadata for the FinLearn AI curriculum.

This module defines the full course structure: modules, lessons, topics,
difficulty, prerequisites, durations, quiz presence, and connected tools.
This layer is intentionally static and unchanged by the ML system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LessonMeta:
    lesson_id:       str
    module_id:       str
    title:           str
    topic:           str               # primary topic (from TOPICS in config)
    difficulty:      int               # 1–5
    duration_mins:   int               # estimated completion time
    prereq_ids:      tuple[str, ...]   # lesson IDs that must be completed first
    has_quiz:        bool   = True
    tool_id:         Optional[str] = None  # connected learning tool, if any
    concept_tags:    tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ModuleMeta:
    module_id:   str
    title:       str
    topics:      tuple[str, ...]
    lesson_ids:  tuple[str, ...]
    order:       int   # display order in curriculum


# ---------------------------------------------------------------------------
# Curriculum definition  (20 lessons, 5 modules)
# ---------------------------------------------------------------------------

LESSONS: List[LessonMeta] = [
    # ------------------------------------------------------------------
    # Module 1 – Foundations
    # ------------------------------------------------------------------
    LessonMeta(
        lesson_id="L01", module_id="M1",
        title="What is Investing?",
        topic="financial_basics", difficulty=1, duration_mins=10,
        prereq_ids=(),
        concept_tags=("time_value", "principal"),
    ),
    LessonMeta(
        lesson_id="L02", module_id="M1",
        title="Time Value of Money",
        topic="financial_basics", difficulty=1, duration_mins=12,
        prereq_ids=("L01",),
        concept_tags=("time_value", "interest_rates", "inflation"),
    ),
    LessonMeta(
        lesson_id="L03", module_id="M1",
        title="How Compound Interest Works",
        topic="compound_interest", difficulty=1, duration_mins=15,
        prereq_ids=("L02",),
        concept_tags=("compound_formula", "compound_frequency"),
    ),
    LessonMeta(
        lesson_id="L04", module_id="M1",
        title="Compounding in Practice",
        topic="compound_interest", difficulty=2, duration_mins=15,
        prereq_ids=("L03",),
        concept_tags=("future_value", "rule_of_72"),
    ),

    # ------------------------------------------------------------------
    # Module 2 – Risk and Return
    # ------------------------------------------------------------------
    LessonMeta(
        lesson_id="L05", module_id="M2",
        title="Understanding Risk",
        topic="risk_tolerance", difficulty=1, duration_mins=12,
        prereq_ids=("L04",),
        concept_tags=("loss_aversion", "risk_capacity"),
    ),
    LessonMeta(
        lesson_id="L06", module_id="M2",
        title="What is Volatility?",
        topic="volatility", difficulty=2, duration_mins=15,
        prereq_ids=("L05",),
        concept_tags=("standard_deviation", "beta", "volatility_meaning"),
    ),
    LessonMeta(
        lesson_id="L07", module_id="M2",
        title="Risk-Return Tradeoff",
        topic="risk_tolerance", difficulty=2, duration_mins=15,
        prereq_ids=("L06",),
        concept_tags=("risk_preference", "risk_score"),
    ),
    LessonMeta(
        lesson_id="L08", module_id="M2",
        title="Building Your Risk Profile",
        topic="risk_tolerance", difficulty=2, duration_mins=20,
        prereq_ids=("L07",),
        tool_id="etf_recommender",
        concept_tags=("risk_score", "risk_preference", "risk_capacity"),
    ),

    # ------------------------------------------------------------------
    # Module 3 – Portfolio Fundamentals
    # ------------------------------------------------------------------
    LessonMeta(
        lesson_id="L09", module_id="M3",
        title="Why Diversify?",
        topic="diversification", difficulty=2, duration_mins=15,
        prereq_ids=("L08",),
        concept_tags=("diversification_benefit", "idiosyncratic_risk"),
    ),
    LessonMeta(
        lesson_id="L10", module_id="M3",
        title="Correlation and Risk Reduction",
        topic="diversification", difficulty=3, duration_mins=18,
        prereq_ids=("L09",),
        concept_tags=("correlation", "uncorrelated_assets", "diversification_benefit"),
    ),
    LessonMeta(
        lesson_id="L11", module_id="M3",
        title="Asset Allocation Basics",
        topic="asset_allocation", difficulty=2, duration_mins=15,
        prereq_ids=("L08", "L09"),
        concept_tags=("stock_bond_mix", "age_based_allocation"),
    ),
    LessonMeta(
        lesson_id="L12", module_id="M3",
        title="Designing Your Allocation",
        topic="asset_allocation", difficulty=3, duration_mins=20,
        prereq_ids=("L10", "L11"),
        tool_id="portfolio_simulator",
        concept_tags=("target_date", "allocation_rebalancing", "stock_bond_mix"),
    ),

    # ------------------------------------------------------------------
    # Module 4 – Investment Vehicles
    # ------------------------------------------------------------------
    LessonMeta(
        lesson_id="L13", module_id="M4",
        title="Stocks vs Bonds",
        topic="stock_analysis", difficulty=2, duration_mins=15,
        prereq_ids=("L05",),
        concept_tags=("pe_ratio", "earnings", "fundamental_analysis"),
    ),
    LessonMeta(
        lesson_id="L14", module_id="M4",
        title="Introduction to ETFs",
        topic="etfs", difficulty=2, duration_mins=15,
        prereq_ids=("L13",),
        concept_tags=("expense_ratio", "index_tracking", "etf_types"),
    ),
    LessonMeta(
        lesson_id="L15", module_id="M4",
        title="ETF Strategies and Selection",
        topic="etfs", difficulty=3, duration_mins=20,
        prereq_ids=("L14",),
        tool_id="etf_recommender",
        concept_tags=("total_return", "etf_types", "expense_ratio"),
    ),
    LessonMeta(
        lesson_id="L16", module_id="M4",
        title="How to Screen Stocks",
        topic="stock_analysis", difficulty=3, duration_mins=20,
        prereq_ids=("L13", "L15"),
        tool_id="stock_screener",
        concept_tags=("technical_analysis", "fundamental_analysis", "pe_ratio"),
    ),

    # ------------------------------------------------------------------
    # Module 5 – Portfolio Management
    # ------------------------------------------------------------------
    LessonMeta(
        lesson_id="L17", module_id="M5",
        title="What is Rebalancing?",
        topic="rebalancing", difficulty=2, duration_mins=15,
        prereq_ids=("L12",),
        concept_tags=("drift", "rebalancing_trigger"),
    ),
    LessonMeta(
        lesson_id="L18", module_id="M5",
        title="Rebalancing Strategies",
        topic="rebalancing", difficulty=3, duration_mins=18,
        prereq_ids=("L17",),
        concept_tags=("threshold_rebalancing", "tax_efficiency", "drift"),
    ),
    LessonMeta(
        lesson_id="L19", module_id="M5",
        title="How Markets Work",
        topic="market_mechanics", difficulty=3, duration_mins=18,
        prereq_ids=("L13",),
        concept_tags=("market_orders", "bid_ask", "liquidity", "market_makers"),
    ),
    LessonMeta(
        lesson_id="L20", module_id="M5",
        title="Your Complete Portfolio Plan",
        topic="asset_allocation", difficulty=4, duration_mins=25,
        prereq_ids=("L18", "L19"),
        tool_id="portfolio_simulator",
        concept_tags=("allocation_rebalancing", "target_date", "stock_bond_mix"),
    ),
]

MODULES: List[ModuleMeta] = [
    ModuleMeta(
        module_id="M1", title="Investment Foundations",
        topics=("financial_basics", "compound_interest"),
        lesson_ids=("L01", "L02", "L03", "L04"),
        order=1,
    ),
    ModuleMeta(
        module_id="M2", title="Risk and Return",
        topics=("risk_tolerance", "volatility"),
        lesson_ids=("L05", "L06", "L07", "L08"),
        order=2,
    ),
    ModuleMeta(
        module_id="M3", title="Portfolio Fundamentals",
        topics=("diversification", "asset_allocation"),
        lesson_ids=("L09", "L10", "L11", "L12"),
        order=3,
    ),
    ModuleMeta(
        module_id="M4", title="Investment Vehicles",
        topics=("stock_analysis", "etfs"),
        lesson_ids=("L13", "L14", "L15", "L16"),
        order=4,
    ),
    ModuleMeta(
        module_id="M5", title="Portfolio Management",
        topics=("rebalancing", "market_mechanics", "asset_allocation"),
        lesson_ids=("L17", "L18", "L19", "L20"),
        order=5,
    ),
]

# ---------------------------------------------------------------------------
# Lookup helpers  (built once at import time)
# ---------------------------------------------------------------------------

LESSON_BY_ID:  Dict[str, LessonMeta]  = {l.lesson_id: l for l in LESSONS}
MODULE_BY_ID:  Dict[str, ModuleMeta]  = {m.module_id: m for m in MODULES}

# Lessons in curriculum order
LESSON_ORDER: List[str] = [l.lesson_id for l in LESSONS]
TOTAL_LESSONS: int = len(LESSONS)


def get_prerequisites(lesson_id: str) -> List[str]:
    """Return direct prerequisite lesson IDs for a given lesson."""
    return list(LESSON_BY_ID[lesson_id].prereq_ids)


def all_prerequisites_satisfied(lesson_id: str, completed: set[str]) -> bool:
    """Return True if every prerequisite of lesson_id is in completed."""
    return all(p in completed for p in LESSON_BY_ID[lesson_id].prereq_ids)


def get_eligible_lessons(completed: set[str]) -> List[LessonMeta]:
    """
    Return all lessons that are NOT yet completed and whose prerequisites
    are fully satisfied.
    """
    return [
        l for l in LESSONS
        if l.lesson_id not in completed
        and all_prerequisites_satisfied(l.lesson_id, completed)
    ]


def lessons_in_module(module_id: str) -> List[LessonMeta]:
    """Return ordered lessons for a module."""
    return [LESSON_BY_ID[lid] for lid in MODULE_BY_ID[module_id].lesson_ids]


def topic_to_lessons(topic: str) -> List[LessonMeta]:
    """Return all lessons that teach a given topic."""
    return [l for l in LESSONS if l.topic == topic]
