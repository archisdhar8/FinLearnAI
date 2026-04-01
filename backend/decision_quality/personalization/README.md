# FinLearn AI — Learning Personalization Subsystem

A production-structured ML layer that sits on top of the existing static
educational content and delivers adaptive next-lesson recommendations.

## Architecture

```
personalization/
├── config.py              # constants, thresholds, topics, paths
├── schemas.py             # Event, UserProfile, RecommendationResponse (Pydantic)
├── content_meta.py        # static curriculum (5 modules, 20 lessons)
├── mastery.py             # topic mastery computation (composite formula)
├── feature_engineering.py # user / topic / candidate / interaction features
├── synthetic/
│   ├── personas.py        # 6 learner archetypes with behavioural parameters
│   ├── simulator.py       # event-stream simulation engine
│   └── generate.py        # entry point – writes parquet + CSV to data/
├── training/
│   ├── targets.py         # MasteryGainTarget | CompletionScoreTarget (swappable)
│   ├── dataset_builder.py # candidate-ranking training set construction
│   └── train.py           # trains LR / RF / GBM, saves to artifacts/
├── models/
│   ├── base.py            # BaseRecommender interface
│   ├── heuristic.py       # rule-based recommender (no training required)
│   └── ml_recommender.py  # ML recommender (loads trained artifact)
├── evaluation/
│   └── evaluator.py       # P@K, R@K, nDCG@K, mastery-gain metrics
├── inference/
│   └── engine.py          # RecommendationEngine + explanation generation
├── api/
│   └── routes.py          # FastAPI router (mount in main.py)
└── cli.py                 # command-line entry point
```

## Quick Start

All commands from `FinLearnAI/` root:

### 1. Generate synthetic data
```bash
cd backend
python -m decision_quality.personalization.synthetic.generate --users 3000
```
Writes:
- `data/events.parquet`            (raw interactions, ~300k+ rows)
- `data/user_profiles.parquet`     (one row per user)
- `data/mastery_snapshots.parquet` (point-in-time mastery)
- `data/user_summaries.csv`        (aggregated summary)

### 2. Train models
```bash
python -m decision_quality.personalization.training.train
```
Trains Logistic Regression, Random Forest, and Gradient Boosting.
Writes artifacts to `decision_quality/personalization/artifacts/`.

### 3. Evaluate
```bash
python -m decision_quality.personalization.evaluation.evaluator --sample-users 300
```
Prints P@3, R@3, nDCG@3, Top-1 accuracy for heuristic vs ML.

### 4. Demo recommendations
```bash
python -m decision_quality.personalization.cli demo --persona engaged_learner
```

### Or run the full pipeline at once
```bash
python -m decision_quality.personalization.cli run-all
```

---

## Mount the API in `main.py`

```python
# In backend/main.py (add these two lines)
from decision_quality.personalization.api.routes import personalization_router
app.include_router(personalization_router, prefix="/api/personalization")
```

### Available endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/personalization/health` | Subsystem health check |
| GET | `/api/personalization/users/{id}/features` | User-level feature summary |
| GET | `/api/personalization/users/{id}/mastery` | Per-topic mastery scores |
| GET | `/api/personalization/users/{id}/recommend` | Top-1 recommendation |
| GET | `/api/personalization/users/{id}/recommend/top3` | Top-3 recommendations |
| GET | `/api/personalization/users/{id}/readiness` | Module readiness status |
| POST | `/api/personalization/events` | Ingest a new user event |
| POST | `/api/personalization/cache/refresh` | Reload event log from disk |

---

## ML System Design

### Task framing
**Candidate-ranking**: For each user at a decision point, every eligible
lesson is a candidate. A training row is `(user_features ∥ topic_features ∥
candidate_features ∥ interaction_features, label)`.

### Feature groups (43 total)
| Group | Count | Examples |
|-------|-------|---------|
| User | 18+ | avg_score, retry_rate, engagement_score, confusion_indicator |
| Topic | 8 | mastery_score, error_rate, tutor_questions, repeated_mistakes |
| Candidate | 7 | difficulty, prereq_ratio, distance_from_front, has_tool |
| Interaction | 6 | mastery_gap, difficulty_mismatch, addresses_confusion |

### Target definitions
- **MasteryGainTarget** (default): positive if lesson → mastery gain ≥ 0.08
- **CompletionScoreTarget**: positive if completed + quiz score ≥ 0.70

### Models
| Model | Use case |
|-------|----------|
| `HeuristicRecommender` | Always available, no training, fully explainable |
| `LogisticRegression` | Fast baseline, interpretable coefficients |
| `RandomForest` | Better accuracy, feature importance |
| `GradientBoosting` | Primary model, best ranking quality |

### Explanations
All explanations are **deterministic template-based** — derived directly from
computed feature values. No LLM required.

Example outputs:
> *"Recommended because your recent quiz scores in diversification are below your
> course average (38% mastery vs 62% course average).  This lesson connects to the
> etf recommender tool."*

> *"Consider reviewing 'Why Diversify?' first — your mastery in diversification is
> currently low (32%), which may make this lesson harder."*

---

## Adding Real User Data

Replace `_get_events()` in `api/routes.py` with a DB query:
```python
def _get_events() -> pd.DataFrame:
    # e.g. read from Supabase
    return supabase_client.table("learning_events").select("*").execute().data
```

The rest of the pipeline is unchanged.
