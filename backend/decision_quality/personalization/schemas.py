"""
Domain schemas for the learning-personalization subsystem.

All data structures are defined here: events, user profiles, recommendation
outputs, and feature vectors. Pydantic is used for API-facing schemas;
plain dataclasses for internal computation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Event taxonomy
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    LESSON_STARTED          = "lesson_started"
    LESSON_COMPLETED        = "lesson_completed"
    LESSON_ABANDONED        = "lesson_abandoned"
    QUIZ_SUBMITTED          = "quiz_submitted"
    QUIZ_QUESTION_ANSWERED  = "quiz_question_answered"
    TUTOR_QUESTION          = "tutor_question"
    TOOL_USED               = "tool_used"
    MODULE_COMPLETED        = "module_completed"
    RECOMMENDATION_SHOWN    = "recommendation_shown"
    RECOMMENDATION_CLICKED  = "recommendation_clicked"
    SESSION_STARTED         = "session_started"
    SESSION_ENDED           = "session_ended"


# ---------------------------------------------------------------------------
# Raw event (both internal and DB-persisted)
# ---------------------------------------------------------------------------

@dataclass
class Event:
    """A single user-interaction event."""
    user_id:        str
    event_type:     str                          # EventType value
    timestamp:      datetime

    # Curriculum linkage (nullable)
    lesson_id:      Optional[str]  = None
    module_id:      Optional[str]  = None
    topic:          Optional[str]  = None
    concept_tag:    Optional[str]  = None        # for tutor/quiz events

    # Scoring
    score:          Optional[float] = None       # 0–1
    attempt_num:    int             = 1

    # Timing
    duration_mins:  Optional[float] = None

    # Flexible payload
    metadata:       Dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id":      self.user_id,
            "event_type":   self.event_type,
            "timestamp":    self.timestamp.isoformat(),
            "lesson_id":    self.lesson_id,
            "module_id":    self.module_id,
            "topic":        self.topic,
            "concept_tag":  self.concept_tag,
            "score":        self.score,
            "attempt_num":  self.attempt_num,
            "duration_mins":self.duration_mins,
            **self.metadata,
        }


# ---------------------------------------------------------------------------
# User profile
# ---------------------------------------------------------------------------

@dataclass
class UserProfile:
    """Static + slowly-changing user profile attributes."""
    user_id:          str
    persona:          str                        # e.g. "engaged_learner"
    experience_level: str                        # "beginner" | "intermediate" | "advanced"
    learning_goal:    str                        # e.g. "retirement", "general", "trading"
    risk_profile:     str                        # "conservative" | "moderate" | "aggressive"
    created_at:       datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id":          self.user_id,
            "persona":          self.persona,
            "experience_level": self.experience_level,
            "learning_goal":    self.learning_goal,
            "risk_profile":     self.risk_profile,
            "created_at":       self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Computed feature vectors (internal)
# ---------------------------------------------------------------------------

@dataclass
class UserFeatures:
    """Aggregate user-level features derived from events."""
    user_id: str

    # Quiz performance
    overall_avg_score:       float = 0.0
    recent_avg_score:        float = 0.0
    first_attempt_accuracy:  float = 0.0
    best_attempt_accuracy:   float = 0.0
    retry_rate:              float = 0.0

    # Progress
    modules_completed:        int   = 0
    lessons_completed:        int   = 0
    pct_course_complete:      float = 0.0
    lessons_left_module:      int   = 0
    prereq_completion_ratio:  float = 0.0

    # Engagement
    avg_session_length_mins:  float = 0.0
    days_since_last_session:  float = 0.0
    abandonment_rate:         float = 0.0
    engagement_score:         float = 0.0   # composite 0–1

    # Tutor usage
    total_tutor_questions:    int   = 0
    confusion_indicator:      float = 0.0   # high usage + low score

    # Tool usage
    tool_use_counts:          Dict[str, int] = field(default_factory=dict)
    used_tool_before_mastery: int = 0       # times tool used before proficiency
    used_tool_after_lesson:   int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "user_id":                self.user_id,
            "overall_avg_score":      self.overall_avg_score,
            "recent_avg_score":       self.recent_avg_score,
            "first_attempt_accuracy": self.first_attempt_accuracy,
            "best_attempt_accuracy":  self.best_attempt_accuracy,
            "retry_rate":             self.retry_rate,
            "modules_completed":      self.modules_completed,
            "lessons_completed":      self.lessons_completed,
            "pct_course_complete":    self.pct_course_complete,
            "lessons_left_module":    self.lessons_left_module,
            "prereq_completion_ratio":self.prereq_completion_ratio,
            "avg_session_length_mins":self.avg_session_length_mins,
            "days_since_last_session":self.days_since_last_session,
            "abandonment_rate":       self.abandonment_rate,
            "engagement_score":       self.engagement_score,
            "total_tutor_questions":  self.total_tutor_questions,
            "confusion_indicator":    self.confusion_indicator,
            "used_tool_before_mastery":self.used_tool_before_mastery,
            "used_tool_after_lesson": self.used_tool_after_lesson,
        }
        for tool, cnt in self.tool_use_counts.items():
            d[f"tool_{tool}_count"] = cnt
        return d


@dataclass
class TopicMastery:
    """Per-topic mastery features for one user."""
    user_id:             str
    topic:               str

    avg_score:           float = 0.0
    attempts:            int   = 0
    error_rate:          float = 0.0
    repeated_mistakes:   int   = 0
    time_spent_mins:     float = 0.0
    tutor_questions:     int   = 0
    lessons_completed:   int   = 0
    mastery_score:       float = 0.0   # composite 0–1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id":           self.user_id,
            "topic":             self.topic,
            "avg_score":         self.avg_score,
            "attempts":          self.attempts,
            "error_rate":        self.error_rate,
            "repeated_mistakes": self.repeated_mistakes,
            "time_spent_mins":   self.time_spent_mins,
            "tutor_questions":   self.tutor_questions,
            "lessons_completed": self.lessons_completed,
            "mastery_score":     self.mastery_score,
        }


# ---------------------------------------------------------------------------
# Recommendation output (Pydantic for API serialization)
# ---------------------------------------------------------------------------

class AlternativeSuggestion(BaseModel):
    lesson_id:   str
    title:       str
    confidence:  float
    reason:      str


class ReadinessStatus(BaseModel):
    ready_for_next_module: bool
    should_review_prereq:  bool
    suggested_tool:        Optional[str]
    readiness_score:       float          # 0–1
    notes:                 str


class RecommendationResponse(BaseModel):
    user_id:              str
    lesson_id:            str
    title:                str
    topic:                str
    difficulty:           int
    confidence:           float = Field(ge=0.0, le=1.0)
    explanation:          str
    weak_topic_summary:   str
    readiness:            ReadinessStatus
    alternatives:         List[AlternativeSuggestion] = []
    generated_at:         str             # ISO timestamp


class UserFeaturesResponse(BaseModel):
    user_id:             str
    overall_avg_score:   float
    recent_avg_score:    float
    lessons_completed:   int
    pct_course_complete: float
    engagement_score:    float
    days_since_last_session: float
    confusion_indicator: float
    top_weak_topics:     List[str]
    top_strong_topics:   List[str]


class TopicMasteryResponse(BaseModel):
    user_id:     str
    mastery_map: Dict[str, float]    # topic -> mastery_score 0–1
    weak_topics: List[str]
    strong_topics: List[str]
