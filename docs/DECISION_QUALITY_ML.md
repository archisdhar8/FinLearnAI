# ML Decision-Quality Model — How to Build It

This doc describes how to build an **ML model** that evaluates user choices in the Simulator, ETF Recommender, and Stock Builder and returns feedback (e.g. “too risky for your goals,” “good fit”). It fits **after** you have rule-based feedback working; the model can augment or replace rules over time.

---

## 1. What the model does

**Input:** A feature vector describing:
- **User context:** stated goal, risk tolerance, time horizon, (optional) learning progress.
- **Choice:** what they did in the tool (simulator params, ETF allocation, or stock portfolio).

**Output (pick one framing):**

- **Option A — Classification:** One of `{ good_fit, risky, mismatch_goals, suggest_learn_more }` (+ optional free-text message).
- **Option B — Score:** A scalar “decision quality” 0–1; backend maps score to a message bucket.
- **Option C — Multi-label:** Which feedback types apply (e.g. `[too_aggressive, short_horizon]`); then template messages.

For capstone and iteration, **Option A** is the simplest: one label per decision, and you can add a small template or generator for the message.

---

## 2. Where labels come from (critical)

You need **labeled examples**: (features, label). Options:

### A. Rules as oracle (recommended to start)

- Implement **rule-based feedback** first (as in `PERSONALIZATION_DESIGN.md`).
- For each tool, define 5–10 rules that map (user context, choice) → a **category** (e.g. `good_fit` / `too_risky` / `mismatch_goals`).
- Run the rules on **synthetic or logged data** to get (feature vector, label). No human needed for v1.
- **Example:** “If horizon < 5 and equity_pct > 80% → `too_risky`.” Sample many (horizon, equity_pct, …) and label with this rule. You get a training set.

### B. Human labeling

- Store (anonymized) (user_id, tool, context, choice) when users hit the tools; later, a human (or you) labels a subset: “good_fit,” “risky,” etc.
- Improves over time; start with a few hundred.

### C. Hybrid

- Use rules to label 80% of samples; humans label 20%. Train the model; later you can replace rule labels with human-only where they disagree.

**Practical path:** Start with **A**. Define clear rule categories per tool, generate 500–2000 synthetic (or replay) examples per tool, train a small classifier. For capstone, you can say “labels from a rule-based oracle; future work: human labeling.”

---

## 3. Features per tool

These become the **input vector** to the model. Normalize (0–1 or z-score) for numeric features.

### Simulator

| Feature | Type | Description |
|--------|------|-------------|
| `monthly_contribution` | float | $/month (or log / cap for scale) |
| `years` | int/float | Time horizon |
| `expected_return_pct` | float | Assumed annual return |
| `goal` (optional) | categorical → one-hot | From dashboard: e.g. retirement_30y, house_5y |
| `user_risk_score` (optional) | float | 0–1 from ETF quiz if available |

**Derived:** `monthly_as_share_of_income` (if you ever have income), or rule-of-thumb flags like `years < 5`, `return_assumption > 12`.

### ETF Recommender / Allocator

| Feature | Type | Description |
|--------|------|-------------|
| `risk_score` | float | 0–1 from risk quiz |
| `time_horizon_years` | float | From quiz |
| `equity_pct` | float | Sum of weights in equity ETFs (VTI, VOO, QQQ, VXUS, …) |
| `bond_pct` | float | BND, AGG, TLT, TIP, … |
| `max_single_etf_weight` | float | Concentration |
| `num_etfs` | int | Number of ETFs with weight > 0 |
| `profile_label` | categorical | conservative / moderate / balanced / growth / aggressive (from quiz) |

**Derived:** Distance between recommended profile allocation and actual (e.g. L1 or L2 on weight vector); `equity_pct` vs profile’s typical equity.

### Stock Builder (AI Stock Discovery)

| Feature | Type | Description |
|--------|------|-------------|
| `num_stocks` | int | Holdings count |
| `herfindahl` or `concentration` | float | Sum of squared weights |
| `max_single_weight` | float | Largest weight |
| `sector_entropy` or `top_sector_pct` | float | Diversification (e.g. max sector weight) |
| `user_modules_completed` | int | From progress (readiness proxy) |
| `portfolio_volatility` (optional) | float | From optimizer output |
| `portfolio_expected_return` (optional) | float | From optimizer output |

**Derived:** “Under-diversified” flag (e.g. num_stocks < 5 or herfindahl > 0.3), “sector bet” (one sector > 50%).

---

## 4. Model choice

- **Logistic regression or small MLP (2–3 layers):** Good for capstone. Interpretable (LR coefficients or feature importance), fast to train, works with 500–2k samples.
- **Gradient boosting (XGBoost / LightGBM):** Better accuracy with more features and data; still interpretable (feature importance). Use if you have 2k+ samples.
- **Avoid** large transformers or heavy deep learning; the input is a small vector, not text or images.

**Output layer:** Softmax for Option A (4 classes) or sigmoid for Option B (one score). For Option C, multi-label sigmoids per feedback type.

---

## 5. Training pipeline (sketch)

1. **Define label taxonomy** per tool (e.g. `good_fit`, `too_risky`, `mismatch_goals`, `suggest_learn_more`).
2. **Implement rule oracle:** functions that take (context, choice) → label (and optionally message key).
3. **Generate dataset:** Sample (or replay from logs) many (context, choice); label with rule oracle; vectorize to (features, label). Save as CSV/Parquet or in-memory.
4. **Train:** e.g. scikit-learn `LogisticRegression` or `MLPClassifier`, or XGBoost. Use a small holdout (e.g. 20%) for validation; if you later have human labels, hold out human-only for test.
5. **Export:** Serialize model (joblib/pickle or ONNX). Backend loads it once at startup.
6. **Inference:** When frontend calls `POST /api/feedback/etf-allocation`, backend builds the same feature vector, runs model.predict (or predict_proba), maps predicted class to a message template, returns `{ "feedback": "..." }`.

---

## 6. Where it lives in the repo

- **Training (offline):** e.g. `backend/decision_quality/` or `ml/decision_quality/`:
  - `features.py` — build feature vector from (context, choice) per tool.
  - `rules_oracle.py` — rule-based labeling (same logic you’d use for v1 feedback).
  - `train.py` — load data, train model, save artifact.
  - `dataset_generate.py` — sample synthetic or replay logs → CSV with features + label.
- **Inference (backend):** In `main.py` or a small `decision_quality/service.py`: load model, expose one function `evaluate_etf(user_context, allocation) -> { "label": "...", "feedback": "..." }`, and same for simulator / stock builder. The existing `POST /api/feedback/*` endpoints call this instead of (or in addition to) pure rules.

---

## 7. Message from the model

- **Option A (class):** Map class to a fixed message per tool, e.g. `too_risky` → “This allocation may be too aggressive for your stated horizon. Consider adding bonds.”
- **Optional:** Add a second step: given (class, features), use a **tiny generator** (e.g. 1–2 prompt calls to Gemini with strict templates) to produce one sentence. For capstone, fixed templates are enough; “LLM-generated message” is a nice future work.

---

## 8. Capstone narrative

- “We built a **decision-quality model** that classifies user choices in the Simulator, ETF Recommender, and Stock Builder. Labels were generated from a **rule-based oracle** aligned with investor-education guidelines. The model consumes **user context** (goal, risk score, horizon) and **choice features** (allocation, concentration, etc.) and outputs a **feedback category** that is mapped to an explanatory message. This keeps the system **interpretable** and allows future improvement with human labels.”  
- You can report **accuracy vs. rule oracle** on a holdout set, and optionally **feature importance** (which dimensions most drive “too_risky” vs “good_fit”).

---

## 9. Summary

| Step | Action |
|------|--------|
| 1 | Define 3–4 decision-quality labels per tool. |
| 2 | Implement rule-based labeling (oracle) for those labels. |
| 3 | Build feature pipelines (context + choice → vector) per tool. |
| 4 | Generate 500–2k labeled examples per tool using the oracle. |
| 5 | Train a classifier (LR or small MLP/XGBoost); export artifact. |
| 6 | In backend, load model; in feedback endpoints, compute features → predict → map to message. |
| 7 | (Optional) Later: add human labeling and retrain. |

The ML model stays **separate** from static content and from the core tool logic; it only powers the **feedback** branch of the API.
