# FinLearn AI — Data Science & Architecture Summary (Class Presentation)

Use this for **~30 sec data pipeline**, **~1 min overall architecture**, and **45 sec–1 min per tool**. Speak to data pipeline, architecture, models, techniques, trade-offs, and results.

---

## 1. Data Pipeline (30 seconds)

**Sources:** Polygon (OHLCV, news), Supabase (users, progress), static knowledge base (Investopedia, SEC, Vanguard, etc.), and user inputs (quiz, tickers, chart uploads).

**Flow:** Raw data is ingested via APIs and stored in memory or disk cache where it makes sense (e.g. stock screener cache, S&P 500 analysis cache). RAG uses a pre-built chunked knowledge base with source tiering. No long-running ETL; we do on-demand fetch, normalize within sector where needed, and pass structured data into models. **Trade-off:** we favor low latency and simplicity over a full data warehouse; caching and TTLs handle freshness.

---

## 2. Overall Architecture & ML Pipeline (1 minute)

**Stack:** React frontend (Vercel), FastAPI backend (EC2), Supabase (auth + Postgres), and several ML components either in-process (PyTorch, Transformers, sentence-transformers) or via APIs (Gemini, Polygon).

**ML pipeline:** We don’t have one monolithic pipeline. Each tool is a small pipeline: **ingest → optional cache → feature/preprocess → model(s) → postprocess → response.** Examples: Stock Screener = Polygon + CV models + sentiment + LLM summary. RAG = hybrid retrieval (BM25 + embeddings) → rerank → Gemini with context. ETF Allocator = questionnaire → risk score → GA → optional Monte Carlo. So the “ML pipeline” is really **tool-specific pipelines** sharing backend, auth, and some models (e.g. same CV models for screener and chart analyzer).

**Why this design:** We can ship and tune each tool independently, reuse components (e.g. FinBERT, CV models), and keep latency low by avoiding unnecessary hops.

---

## 3. Stock Screener (45 sec–1 min)

**Under the hood:** For each ticker we pull 30+ days of OHLCV from Polygon, build a candlestick image (matplotlib), then run **two PyTorch CNNs**: (1) **Trend** — EfficientNet-B2 backbone, 3-way classification (uptrend/downtrend/sideways) plus a small slope head; (2) **Support/Resistance** — ResNet34 backbone, 10 zone outputs per side (support + resistance). We combine trend + S/R with **FinBERT** sentiment on recent news and a **Gemini** call to produce a short, actionable summary (no RAG; dedicated “analyst” prompt).

**Techniques:** Transfer learning (ImageNet backbones), binary/multiclass classification, regression for slope, sentiment aggregation, LLM summarization. **Challenges:** Chart images are synthetic (we control axes); real user charts would need more robust preprocessing. **Trade-off:** We use the same CV stack for screener and chart analyzer to avoid maintaining two code paths. **Results:** BUY/HOLD/SELL plus support/resistance levels and a 2–3 sentence narrative; cache reduces repeat calls.

---

## 4. Chart Analyzer (45 sec–1 min)

**Under the hood:** User uploads a chart image. We resize to 224×224, normalize (ImageNet stats), and run the **same Trend and S/R models** as the screener — ResNet34 S/R head (10+10 zones) and EfficientNet-B2 trend (3 classes + slope). We map zone logits to price levels using the image’s implied price range. Optional **Grad-CAM** on the last conv layer shows where the model “looked” for trend and S/R.

**Techniques:** Same as screener (CNNs, softmax/sigmoid), plus **explainability** via gradient-weighted activations (Grad-CAM). **Challenges:** Uploaded charts vary in style and aspect ratio; we assume candlestick-like content. **Trade-off:** One model set for both “synthetic” screener charts and “wild” uploads; we accept some domain shift for simplicity. **Results:** Trend label, confidence, S/R zones with confidence, and optional heatmaps for interpretability.

---

## 5. Sentiment Analyzer (45 sec–1 min)

**Under the hood:** We fetch recent news for a ticker (Polygon, last 7 days, ~10–15 articles). Titles and descriptions are passed into **FinBERT** (Transformer fine-tuned on financial text). We aggregate per-article scores into an overall sentiment and a BULLISH/BEARISH/NEUTRAL signal with strength.

**Techniques:** Pre-trained transformer (FinBERT), tokenization, pooling, and simple aggregation (e.g. mean or weighted by confidence). **Challenges:** News APIs can be sparse; we fall back to keyword-based sentiment if FinBERT or fetch fails. **Trade-off:** We don’t do temporal weighting or entity linking; we prioritize simplicity and robustness. **Results:** Per-article sentiment + overall score and signal used in the UI and in the Stock Screener narrative.

---

## 6. Portfolio Simulator (45 sec–1 min)

**Under the hood:** This one is **frontend-only**: no backend ML. User sets initial investment, monthly contribution, horizon, and expected return. We run a **deterministic compound-growth loop** in JavaScript (monthly compounding + contributions). No randomness.

**Techniques:** Simple time-series projection (no Monte Carlo here). **Trade-off:** We keep it lightweight and fast; the **Smart ETF Allocator** is where we do proper Monte Carlo with covariance. **Results:** Year-by-year portfolio and contribution curves; good for intuition, not for risk distribution.

---

## 7. AI Stock Discovery (45 sec–1 min)

**Under the hood:** We run a **batch job** over the S&P 500: for each ticker we get price, fundamentals, sector, and optional sentiment. **SectorNormalizer** normalizes metrics (e.g. 3M return, valuation) **within sector** so we compare tech to tech, not tech to utilities. **StockScorer** builds a **composite score** from five factors — valuation (30%), fundamentals (25%), sentiment (20%), momentum (15%), risk (10%) — each normalized 0–100. We rank by composite and optionally by sector rank. Results are cached (e.g. 7 days) and exposed via API; the frontend does filtering and portfolio construction.

**Techniques:** Sector-based normalization (min–max or rank within sector), weighted composite scoring, batch ETL with cache. **Challenges:** Fundamental data can be missing; we use fallbacks and neutral scores. **Trade-off:** We don’t use a predictive model (e.g. next-month return); we use a **ranking** model for discovery and let the user or ETF Allocator do allocation. **Results:** Sector-normalized rankings, composite scores, and optional portfolio optimization on selected names.

---

## 8. Smart ETF Allocator (45 sec–1 min)

**Under the hood:** User answers a **questionnaire** (time horizon, risk tolerance, drawdown tolerance, goal, knowledge, income stability). We map answers to a **risk score** in [0,1] and a target equity weight (e.g. conservative ~20% equity, aggressive ~95%). A **genetic algorithm** (real-valued, 120 individuals, 120 generations) optimizes weights over 25 ETFs. Fitness = expected return minus penalties: volatility (scaled by risk aversion), expense ratio, distance to target equity weight, and **Herfindahl–Hirschman** concentration. We enforce simplex (weights sum to 1) and optional minimum weights for “thematic” ETFs. Optional **Monte Carlo** (1000 paths, **geometric Brownian motion** with portfolio mean/variance from a heuristic covariance matrix) gives percentile outcomes and milestone probabilities (e.g. P(reach $1M)).

**Techniques:** Questionnaire → risk profiling, GA (selection, crossover, mutation, elitism), convex constraints, GBM simulation, covariance-based risk. **Challenges:** Expected returns and correlation matrix are heuristic (not estimated from long history); we prioritize stability and interpretability. **Trade-off:** We use a GA instead of quadratic programming so we can add complex constraints (e.g. min weights per theme) without rewriting the solver. **Results:** 3–5 ETF portfolios with weights, metrics (return, vol, Sharpe), and optional simulation bands.

---

## 9. RAG — Financial Education Chat (45 sec–1 min)

**Under the hood:** User question goes through **MultiQueryRetriever**: if the query is “complex” (e.g. compare X and Y, long, or multi-part), we decompose it into 2–4 subqueries. Each (sub)query hits **hybrid retrieval**: **BM25** (keyword, TF–IDF style) and **sentence-transformers** (all-MiniLM-L6-v2) embeddings with cosine similarity. We merge and **rerank** with a **cross-encoder** (BAAI/bge-reranker-base), take top 5 chunks, and compute a **confidence** score. If confidence is below a threshold we **refuse** and explain why. Otherwise we inject the chunks and citations into a **Gemini** prompt with a strict system prompt (citation-only, no stock picks, 40–150 words). We also **refuse** stock-picking questions and steer users to index funds.

**Techniques:** Hybrid retrieval (sparse + dense), reranking, confidence gating, query decomposition, citation-grounded generation, refusal policies. **Challenges:** Balancing brevity and completeness; avoiding hallucination when chunks are weak. **Trade-off:** We use a small embedding model and a single reranker for latency and resource limits; we could scale to larger models for quality. **Results:** Short, cited answers with sources; validation (e.g. LLM-as-judge, cosine to gold) used to tune prompts and thresholds.

---

## Quick Reference — Hats

- **CTO:** One backend, multiple small pipelines; cache and TTL for freshness; no big-data stack.
- **Data architect:** Per-tool data flow; RAG knowledge base chunked and tiered; APIs (Polygon, Supabase) as primary sources.
- **Data engineer:** On-demand fetch + cache (screener, S&P analysis); batch S&P job; no nightly DAGs.
- **Data scientist:** CNNs for charts, FinBERT for sentiment, GA for allocation, GBM for simulation, hybrid retrieval + rerank + LLM for RAG; each pipeline is ingest → model(s) → postprocess.

---

*Use the sections above as speaker notes: ~30 s pipeline, ~1 min architecture, then 45 s–1 min per tool (Screener, Chart, Sentiment, Simulator, Discovery, ETF Allocator, RAG).*
