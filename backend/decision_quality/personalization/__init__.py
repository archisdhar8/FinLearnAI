"""
FinLearn AI — Learning Personalization Subsystem
================================================

A self-contained ML personalization layer that sits on top of the existing
static educational content and tools.  It observes user behaviour, builds
feature vectors, trains a recommendation model, and serves next-step
recommendations without touching any other part of the platform.

Quick start
-----------
1. Generate synthetic data:
       python -m backend.decision_quality.personalization.synthetic.generate

2. Train models:
       python -m backend.decision_quality.personalization.training.train

3. Evaluate:
       python -m backend.decision_quality.personalization.evaluation.evaluator

4. Mount API in main.py:
       from decision_quality.personalization.api.routes import personalization_router
       app.include_router(personalization_router, prefix="/api/personalization")
"""

from .inference.engine import RecommendationEngine
from .api.routes import personalization_router

__all__ = ["RecommendationEngine", "personalization_router"]
