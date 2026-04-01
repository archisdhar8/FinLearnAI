"""
Learner persona definitions for the synthetic data simulator.

Each persona captures a distinct learner archetype with parameterised
behavioural tendencies. Randomness is applied at user-instantiation time
so users within a persona vary realistically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class PersonaConfig:
    """
    Full behavioural specification for a learner persona.

    Probabilities should be in [0, 1]; rates and multipliers are non-negative floats.
    """
    name:               str

    # --- Initial knowledge ---
    base_mastery_mean:  float   # mean starting mastery across topics
    base_mastery_std:   float   # topic-to-topic variation

    # --- Learning dynamics ---
    learning_rate:      float   # mastery gain per lesson (scaled by 1-current_mastery)
    improvement_decay:  float   # how quickly learning slows at high mastery (0=constant)

    # --- Engagement ---
    time_multiplier:    float   # relative time-on-task (1.0 = average)
    session_length_mean_mins: float
    session_length_std_mins:  float

    # --- Behaviours ---
    p_tutor_after_lesson: float  # P(asks tutor question after a lesson)
    p_tutor_after_fail:   float  # P(asks tutor question after failing quiz)
    p_retry_quiz:         float  # P(retries a failed quiz)
    p_skip_lesson:        float  # P(skips a lesson without completing it)
    p_tool_use:           float  # P(uses a tool when one is connected to the lesson)
    p_tool_before_lesson: float  # P(opens tool BEFORE reading the lesson)
    p_dropout:            float  # P(dropping out after each completed module)
    p_advance_early:      float  # P(attempting a harder lesson before suggested)

    # --- Confusion persistence ---
    confusion_decay:    float   # how fast confusion clears after re-study (0=instant)

    # --- Improvement trajectory ---
    engagement_trajectory: str  # "steady" | "accelerating" | "decelerating" | "erratic"

    # --- Tutor topics ---
    tutor_topic_weights: Dict[str, float] = field(default_factory=dict)
    # empty → proportional to lesson difficulty visited


# ---------------------------------------------------------------------------
# Persona catalogue
# ---------------------------------------------------------------------------

PERSONAS: Dict[str, PersonaConfig] = {

    "careful_beginner": PersonaConfig(
        name="careful_beginner",
        base_mastery_mean=0.25,
        base_mastery_std=0.08,
        learning_rate=0.18,
        improvement_decay=0.10,
        time_multiplier=1.4,
        session_length_mean_mins=28.0,
        session_length_std_mins=8.0,
        p_tutor_after_lesson=0.40,
        p_tutor_after_fail=0.80,
        p_retry_quiz=0.75,
        p_skip_lesson=0.05,
        p_tool_use=0.50,
        p_tool_before_lesson=0.10,
        p_dropout=0.04,
        p_advance_early=0.02,
        confusion_decay=0.35,
        engagement_trajectory="steady",
    ),

    "overconfident_beginner": PersonaConfig(
        name="overconfident_beginner",
        base_mastery_mean=0.20,
        base_mastery_std=0.15,
        learning_rate=0.10,
        improvement_decay=0.05,
        time_multiplier=0.7,
        session_length_mean_mins=16.0,
        session_length_std_mins=6.0,
        p_tutor_after_lesson=0.08,
        p_tutor_after_fail=0.15,
        p_retry_quiz=0.20,
        p_skip_lesson=0.25,
        p_tool_use=0.30,
        p_tool_before_lesson=0.40,
        p_dropout=0.12,
        p_advance_early=0.35,
        confusion_decay=0.15,
        engagement_trajectory="decelerating",
    ),

    "engaged_learner": PersonaConfig(
        name="engaged_learner",
        base_mastery_mean=0.40,
        base_mastery_std=0.10,
        learning_rate=0.22,
        improvement_decay=0.12,
        time_multiplier=1.0,
        session_length_mean_mins=22.0,
        session_length_std_mins=5.0,
        p_tutor_after_lesson=0.25,
        p_tutor_after_fail=0.60,
        p_retry_quiz=0.60,
        p_skip_lesson=0.08,
        p_tool_use=0.70,
        p_tool_before_lesson=0.20,
        p_dropout=0.03,
        p_advance_early=0.10,
        confusion_decay=0.50,
        engagement_trajectory="accelerating",
    ),

    "struggling_learner": PersonaConfig(
        name="struggling_learner",
        base_mastery_mean=0.15,
        base_mastery_std=0.08,
        learning_rate=0.08,
        improvement_decay=0.05,
        time_multiplier=1.8,
        session_length_mean_mins=35.0,
        session_length_std_mins=12.0,
        p_tutor_after_lesson=0.65,
        p_tutor_after_fail=0.90,
        p_retry_quiz=0.85,
        p_skip_lesson=0.02,
        p_tool_use=0.35,
        p_tool_before_lesson=0.05,
        p_dropout=0.18,
        p_advance_early=0.00,
        confusion_decay=0.15,
        engagement_trajectory="erratic",
    ),

    "fast_advanced": PersonaConfig(
        name="fast_advanced",
        base_mastery_mean=0.65,
        base_mastery_std=0.12,
        learning_rate=0.30,
        improvement_decay=0.20,
        time_multiplier=0.55,
        session_length_mean_mins=12.0,
        session_length_std_mins=4.0,
        p_tutor_after_lesson=0.05,
        p_tutor_after_fail=0.20,
        p_retry_quiz=0.25,
        p_skip_lesson=0.20,
        p_tool_use=0.60,
        p_tool_before_lesson=0.35,
        p_dropout=0.05,
        p_advance_early=0.45,
        confusion_decay=0.70,
        engagement_trajectory="steady",
    ),

    "tool_first_explorer": PersonaConfig(
        name="tool_first_explorer",
        base_mastery_mean=0.35,
        base_mastery_std=0.18,
        learning_rate=0.15,
        improvement_decay=0.08,
        time_multiplier=0.9,
        session_length_mean_mins=20.0,
        session_length_std_mins=7.0,
        p_tutor_after_lesson=0.20,
        p_tutor_after_fail=0.35,
        p_retry_quiz=0.40,
        p_skip_lesson=0.12,
        p_tool_use=0.90,
        p_tool_before_lesson=0.70,   # characteristically uses tools early
        p_dropout=0.07,
        p_advance_early=0.20,
        confusion_decay=0.40,
        engagement_trajectory="erratic",
    ),
}

PERSONA_NAMES: List[str] = list(PERSONAS.keys())

# Sampling weights for persona assignment (more beginners than advanced)
PERSONA_WEIGHTS: Dict[str, float] = {
    "careful_beginner":     0.20,
    "overconfident_beginner": 0.15,
    "engaged_learner":      0.25,
    "struggling_learner":   0.15,
    "fast_advanced":        0.10,
    "tool_first_explorer":  0.15,
}
