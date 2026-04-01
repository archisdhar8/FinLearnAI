"""
Synthetic learner simulation engine.

Simulates a single user's journey through the FinLearn AI curriculum,
producing realistic event streams. The simulation models:
- Mastery evolution per topic (latent variable)
- Quiz score as a noisy function of mastery × difficulty
- Tutor usage triggered by confusion (low mastery + failed quiz)
- Tool usage shaped by persona and lesson context
- Dropout risk accumulating after failures and long sessions
- Prerequisites enforced at every lesson selection
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from ..config import (
    CONCEPTS_BY_TOPIC,
    MASTERY_THRESHOLD_PROFICIENT,
    MASTERY_THRESHOLD_WEAK,
    RANDOM_SEED,
    TOPICS,
    TOOLS,
)
from ..content_meta import (
    LESSON_BY_ID,
    LESSON_ORDER,
    LessonMeta,
    get_eligible_lessons,
)
from ..schemas import Event, EventType, UserProfile
from .personas import PERSONA_NAMES, PERSONA_WEIGHTS, PERSONAS, PersonaConfig


# ---------------------------------------------------------------------------
# Internal simulation state
# ---------------------------------------------------------------------------

@dataclass
class MasterySnapshot:
    """Point-in-time mastery for a user's topic, stored after each lesson."""
    timestamp:    datetime
    lesson_id:    str
    topic:        str
    mastery_before: float
    mastery_after:  float


@dataclass
class SimUser:
    """Full simulation state for one synthetic learner."""
    user_id:          str
    persona:          PersonaConfig
    profile:          UserProfile
    mastery:          Dict[str, float]       # topic -> current mastery (0–1)
    completed:        Set[str] = field(default_factory=set)
    snapshots:        List[MasterySnapshot] = field(default_factory=list)
    dropout:          bool = False
    current_time:     datetime = field(default_factory=datetime.utcnow)
    session_start:    Optional[datetime] = None
    confusion_counts: Dict[str, int] = field(default_factory=dict)  # topic -> count


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

class LearnerSimulator:
    """
    Simulates user interactions with the FinLearn AI curriculum.

    Usage
    -----
    sim = LearnerSimulator(seed=42)
    user, events = sim.simulate_user()
    """

    def __init__(self, seed: int = RANDOM_SEED) -> None:
        self.rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def simulate_user(
        self,
        persona_name: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
    ) -> Tuple[SimUser, List[Event]]:
        """
        Simulate one learner's full session sequence.

        Returns
        -------
        (SimUser, List[Event])
        """
        if persona_name is None:
            persona_name = self._sample_persona()
        persona = PERSONAS[persona_name]
        user_id = user_id or f"u_{uuid.uuid4().hex[:10]}"
        start_time = start_time or datetime(2024, 1, 1)

        mastery = self._init_mastery(persona)
        profile = UserProfile(
            user_id=user_id,
            persona=persona_name,
            experience_level=self._experience_level(mastery),
            learning_goal=self.rng.choice(["retirement", "general", "trading", "education"]),
            risk_profile=self.rng.choice(["conservative", "moderate", "aggressive"]),
            created_at=start_time,
        )

        user = SimUser(
            user_id=user_id,
            persona=persona,
            profile=profile,
            mastery=mastery,
            current_time=start_time,
        )
        events: List[Event] = []

        # Simulate sessions until dropout or course complete
        max_lessons = len(LESSON_ORDER)
        lesson_count = 0
        while lesson_count < max_lessons and not user.dropout:
            eligible = get_eligible_lessons(user.completed)
            if not eligible:
                break

            # --- Session start ---
            session_events = self._start_session(user)
            events.extend(session_events)

            # --- Pick next lesson ---
            lesson = self._pick_next_lesson(user, eligible)

            # --- Simulate lesson ---
            lesson_events = self._simulate_lesson(user, lesson)
            events.extend(lesson_events)

            lesson_count += 1

            # --- Check module completion ---
            module_event = self._check_module_completion(user)
            if module_event:
                events.append(module_event)

            # --- Dropout check ---
            if self._check_dropout(user):
                events.extend(self._end_session(user))
                user.dropout = True
                break

            # --- Session end ---
            events.extend(self._end_session(user))

            # Advance time between sessions (1–5 days gap)
            gap_days = float(self.rng.exponential(1.5))
            user.current_time += timedelta(days=gap_days)

        return user, events

    # ------------------------------------------------------------------
    # Persona and mastery initialisation
    # ------------------------------------------------------------------

    def _sample_persona(self) -> str:
        names  = list(PERSONA_WEIGHTS.keys())
        weights = np.array([PERSONA_WEIGHTS[n] for n in names])
        weights /= weights.sum()
        return str(self.rng.choice(names, p=weights))

    def _init_mastery(self, persona: PersonaConfig) -> Dict[str, float]:
        mastery: Dict[str, float] = {}
        for topic in TOPICS:
            raw = float(self.rng.normal(persona.base_mastery_mean, persona.base_mastery_std))
            mastery[topic] = float(np.clip(raw, 0.02, 0.95))
        return mastery

    def _experience_level(self, mastery: Dict[str, float]) -> str:
        avg = float(np.mean(list(mastery.values())))
        if avg >= 0.60:
            return "advanced"
        if avg >= 0.35:
            return "intermediate"
        return "beginner"

    # ------------------------------------------------------------------
    # Lesson selection
    # ------------------------------------------------------------------

    def _pick_next_lesson(
        self, user: SimUser, eligible: List[LessonMeta]
    ) -> LessonMeta:
        persona = user.persona

        # Occasionally advance early (skip recommended order)
        if (
            persona.p_advance_early > 0
            and self.rng.random() < persona.p_advance_early
            and len(eligible) > 1
        ):
            # Pick a harder candidate
            eligible_sorted = sorted(eligible, key=lambda l: l.difficulty, reverse=True)
            return eligible_sorted[0]

        # Prefer weak-topic lessons (go back to strengthen gaps) with some probability
        if self.rng.random() < 0.25:
            weakest = min(TOPICS, key=lambda t: user.mastery[t])
            weak_lessons = [l for l in eligible if l.topic == weakest]
            if weak_lessons:
                return weak_lessons[0]

        # Default: follow curriculum order
        for lid in LESSON_ORDER:
            for l in eligible:
                if l.lesson_id == lid:
                    return l

        return eligible[0]

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _start_session(self, user: SimUser) -> List[Event]:
        user.session_start = user.current_time
        return [Event(
            user_id=user.user_id,
            event_type=EventType.SESSION_STARTED.value,
            timestamp=user.current_time,
        )]

    def _end_session(self, user: SimUser) -> List[Event]:
        persona = user.persona
        duration = max(
            5.0,
            float(self.rng.normal(
                persona.session_length_mean_mins,
                persona.session_length_std_mins,
            )),
        )
        ts = user.current_time + timedelta(minutes=duration)
        return [Event(
            user_id=user.user_id,
            event_type=EventType.SESSION_ENDED.value,
            timestamp=ts,
            duration_mins=duration,
        )]

    # ------------------------------------------------------------------
    # Lesson simulation
    # ------------------------------------------------------------------

    def _simulate_lesson(self, user: SimUser, lesson: LessonMeta) -> List[Event]:
        events: List[Event] = []
        persona = user.persona
        topic = lesson.topic

        # --- Lesson start ---
        lesson_start_ts = user.current_time
        events.append(Event(
            user_id=user.user_id,
            event_type=EventType.LESSON_STARTED.value,
            timestamp=lesson_start_ts,
            lesson_id=lesson.lesson_id,
            module_id=lesson.module_id,
            topic=topic,
        ))

        # --- Tool before lesson ---
        if (
            lesson.tool_id
            and self.rng.random() < persona.p_tool_before_lesson
        ):
            tool_ts = user.current_time + timedelta(minutes=1)
            events.append(self._tool_event(user, lesson, tool_ts, phase="before"))
            mastery_gain = 0.01 if user.mastery[topic] < 0.40 else 0.03
            user.mastery[topic] = float(np.clip(
                user.mastery[topic] + mastery_gain, 0.0, 1.0
            ))
            user.current_time = tool_ts + timedelta(minutes=5)

        # --- Lesson skip? ---
        if self.rng.random() < persona.p_skip_lesson:
            user.current_time += timedelta(
                minutes=float(lesson.duration_mins * persona.time_multiplier * 0.3)
            )
            events.append(Event(
                user_id=user.user_id,
                event_type=EventType.LESSON_ABANDONED.value,
                timestamp=user.current_time,
                lesson_id=lesson.lesson_id,
                module_id=lesson.module_id,
                topic=topic,
            ))
            return events

        # --- Lesson study time ---
        study_time = float(
            lesson.duration_mins * persona.time_multiplier
            * self.rng.uniform(0.8, 1.2)
        )
        user.current_time += timedelta(minutes=study_time)

        # --- Mastery update from lesson ---
        mastery_before = user.mastery[topic]
        gain = (
            persona.learning_rate
            * (1.0 - user.mastery[topic])
            * (1.0 + 0.05 * (3 - lesson.difficulty))   # easier lessons give more gain early
        )
        user.mastery[topic] = float(np.clip(user.mastery[topic] + gain, 0.0, 1.0))

        # --- Lesson completed ---
        events.append(Event(
            user_id=user.user_id,
            event_type=EventType.LESSON_COMPLETED.value,
            timestamp=user.current_time,
            lesson_id=lesson.lesson_id,
            module_id=lesson.module_id,
            topic=topic,
            duration_mins=study_time,
        ))
        user.completed.add(lesson.lesson_id)

        # --- Tutor after lesson ---
        if self.rng.random() < persona.p_tutor_after_lesson:
            tutor_events = self._tutor_events(user, lesson, count=1)
            events.extend(tutor_events)

        # --- Quiz ---
        if lesson.has_quiz:
            quiz_events, passed = self._simulate_quiz(user, lesson)
            events.extend(quiz_events)

            # Tutor after fail
            if (
                not passed
                and self.rng.random() < persona.p_tutor_after_fail
            ):
                events.extend(self._tutor_events(user, lesson, count=self.rng.integers(1, 3)))

            # Retry
            if not passed and self.rng.random() < persona.p_retry_quiz:
                retry_events, passed = self._simulate_quiz(user, lesson, attempt=2)
                events.extend(retry_events)

        # --- Tool after lesson ---
        if (
            lesson.tool_id
            and self.rng.random() < persona.p_tool_use * (1.0 - persona.p_tool_before_lesson)
        ):
            tool_ts = user.current_time + timedelta(minutes=1)
            events.append(self._tool_event(user, lesson, tool_ts, phase="after"))
            # Appropriate tool use boosts mastery
            if user.mastery[topic] >= 0.40:
                user.mastery[topic] = float(np.clip(
                    user.mastery[topic] + 0.04 * (1.0 - user.mastery[topic]), 0.0, 1.0
                ))
            user.current_time = tool_ts + timedelta(minutes=8)

        # Store mastery snapshot
        user.snapshots.append(MasterySnapshot(
            timestamp=user.current_time,
            lesson_id=lesson.lesson_id,
            topic=topic,
            mastery_before=mastery_before,
            mastery_after=user.mastery[topic],
        ))

        return events

    # ------------------------------------------------------------------
    # Quiz simulation
    # ------------------------------------------------------------------

    def _simulate_quiz(
        self, user: SimUser, lesson: LessonMeta, attempt: int = 1
    ) -> Tuple[List[Event], bool]:
        """Simulate a quiz attempt. Returns (events, passed)."""
        events: List[Event] = []
        topic = lesson.topic
        mastery = user.mastery[topic]

        # Noise increases with difficulty
        noise_std = 0.05 + 0.02 * lesson.difficulty
        raw_score = float(mastery * (1.0 - 0.04 * (lesson.difficulty - 2)))
        score = float(np.clip(raw_score + self.rng.normal(0, noise_std), 0.0, 1.0))

        # Retry benefits from slight preparation boost
        if attempt > 1:
            score = float(np.clip(score + 0.05, 0.0, 1.0))

        passed = score >= 0.70
        quiz_ts = user.current_time + timedelta(minutes=5)
        user.current_time = quiz_ts

        events.append(Event(
            user_id=user.user_id,
            event_type=EventType.QUIZ_SUBMITTED.value,
            timestamp=quiz_ts,
            lesson_id=lesson.lesson_id,
            module_id=lesson.module_id,
            topic=topic,
            score=score,
            attempt_num=attempt,
            duration_mins=5.0,
        ))

        # Mastery update from quiz
        if passed:
            user.mastery[topic] = float(np.clip(
                user.mastery[topic] + 0.05 * (1.0 - user.mastery[topic]), 0.0, 1.0
            ))
        else:
            user.mastery[topic] = float(np.clip(
                user.mastery[topic] + 0.01, 0.0, 1.0
            ))
            # Track confusion
            user.confusion_counts[topic] = user.confusion_counts.get(topic, 0) + 1

        return events, passed

    # ------------------------------------------------------------------
    # Tutor events
    # ------------------------------------------------------------------

    def _tutor_events(
        self, user: SimUser, lesson: LessonMeta, count: int = 1
    ) -> List[Event]:
        events: List[Event] = []
        topic = lesson.topic
        concepts = CONCEPTS_BY_TOPIC.get(topic, ["general"])

        for _ in range(count):
            concept = str(self.rng.choice(concepts))
            user.current_time += timedelta(minutes=2)
            events.append(Event(
                user_id=user.user_id,
                event_type=EventType.TUTOR_QUESTION.value,
                timestamp=user.current_time,
                lesson_id=lesson.lesson_id,
                module_id=lesson.module_id,
                topic=topic,
                concept_tag=concept,
                duration_mins=2.0,
            ))
            # Tutor boosts mastery slightly
            user.mastery[topic] = float(np.clip(
                user.mastery[topic] + 0.03 * (1.0 - user.mastery[topic]), 0.0, 1.0
            ))
        return events

    # ------------------------------------------------------------------
    # Tool event
    # ------------------------------------------------------------------

    def _tool_event(
        self,
        user: SimUser,
        lesson: LessonMeta,
        ts: datetime,
        phase: str = "after",
    ) -> Event:
        return Event(
            user_id=user.user_id,
            event_type=EventType.TOOL_USED.value,
            timestamp=ts,
            lesson_id=lesson.lesson_id,
            module_id=lesson.module_id,
            topic=lesson.topic,
            duration_mins=float(self.rng.uniform(5, 15)),
            metadata={
                "tool_id": lesson.tool_id,
                "phase":   phase,
            },
        )

    # ------------------------------------------------------------------
    # Module completion
    # ------------------------------------------------------------------

    def _check_module_completion(self, user: SimUser) -> Optional[Event]:
        from ..content_meta import MODULE_BY_ID
        for mod in MODULE_BY_ID.values():
            if (
                mod.module_id not in {
                    e.module_id for e in [] if False  # not tracked separately yet
                }
                and all(lid in user.completed for lid in mod.lesson_ids)
            ):
                # Check if we already emitted this event
                already_emitted = any(
                    s.lesson_id in mod.lesson_ids and s.lesson_id == mod.lesson_ids[-1]
                    for s in user.snapshots[-3:]
                )
                if already_emitted:
                    return Event(
                        user_id=user.user_id,
                        event_type=EventType.MODULE_COMPLETED.value,
                        timestamp=user.current_time,
                        module_id=mod.module_id,
                    )
        return None

    # ------------------------------------------------------------------
    # Dropout
    # ------------------------------------------------------------------

    def _check_dropout(self, user: SimUser) -> bool:
        persona = user.persona
        # Accumulate dropout risk
        confusion_factor = sum(user.confusion_counts.values()) * 0.01
        base_p = persona.p_dropout + confusion_factor
        return bool(self.rng.random() < min(base_p, 0.40))
