# FinLearn AI

An AI-powered financial education and investment analysis platform. FinLearn AI combines interactive learning modules, real-time market analysis tools, and a custom portfolio builder—all backed by machine learning models and a RAG-based AI tutor.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
  - [AI Tutor (RAG Chat)](#1-ai-tutor-rag-chat)
  - [Learning Modules](#2-learning-modules)
  - [Stock Screener](#3-stock-screener)
  - [Chart Analyzer (Computer Vision)](#4-chart-analyzer-computer-vision)
  - [Sentiment Analyzer (FinBERT)](#5-sentiment-analyzer-finbert)
  - [Portfolio Simulator](#6-portfolio-simulator)
  - [ETF Recommender](#7-etf-recommender)
  - [AI Stock Discovery & Portfolio Builder](#8-ai-stock-discovery--portfolio-builder)
  - [Leaderboard & Community](#9-leaderboard--community)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Running](#setup--running)
- [Deployment](#deployment)

---

## Overview

FinLearn AI is a full-stack application designed to teach beginner investors how markets work while giving them professional-grade analysis tools. Users progress through structured learning modules, take quizzes, and immediately apply what they learn using AI-powered tools—all within the same platform.

The platform serves two audiences:
- **Learners**: Step-by-step investing education with quizzes, leaderboards, and an AI tutor that answers questions using a curated financial knowledge base.
- **Investors**: Real-time stock screening with CV-based chart analysis, FinBERT-powered sentiment analysis, a custom S&P 500 index builder with portfolio optimization, and Monte Carlo simulations.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                    │
│   TypeScript · Tailwind CSS · shadcn/ui · Recharts          │
│   Auth (Supabase) · React Router · React Query              │
├─────────────────────────────────────────────────────────────┤
│                     FastAPI Backend                           │
│   REST API · CORS · Background Tasks · Caching              │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  RAG     │  Chart   │ FinBERT  │ Asset    │ Polygon API     │
│  System  │  Vision  │Sentiment │Allocation│ (Market Data)   │
│          │  (CV)    │  (NLP)   │  (MPT)   │                 │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│          ML Layer: PyTorch · Transformers · SciPy            │
├─────────────────────────────────────────────────────────────┤
│   Supabase (Auth + DB)  │  Polygon.io  │  Google Gemini     │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

### 1. AI Tutor (RAG Chat)

A conversational AI assistant that answers investing questions using a curated knowledge base of trusted financial sources.

**How it works:**
- A Retrieval-Augmented Generation (RAG) pipeline retrieves relevant content before generating an answer.
- **Hybrid retrieval**: Combines BM25 keyword search with semantic embedding search (all-MiniLM-L6-v2) for high recall.
- **Reranking**: A cross-encoder (BAAI/bge-reranker-base) reranks the top candidates for precision.
- **Confidence gating**: If retrieval confidence is below threshold, the system refuses to answer rather than hallucinate.
- **Lesson-aware context**: When a user is on a specific lesson, the retriever boosts chunks from that lesson by 50%.
- **LLM generation**: Google Gemini (or Ollama as fallback) generates the final response grounded in retrieved context.

**Knowledge base sources:** SEC Investor.gov, Investopedia, Vanguard, Fidelity, Bogleheads, FINRA, Federal Reserve Education.

**Key files:** `quantcademy-app/rag/retrieval.py`, `quantcademy-app/rag/knowledge_base_v2.py`, `quantcademy-app/rag/llm_provider.py`

---

### 2. Learning Modules

Structured, multi-lesson courses that teach investing from the ground up.

**Modules:**
- **The Foundation** (Beginner) — What is investing, asset types, how markets work, compound interest, risk basics, account setup, and investor mindset.
- **Building Your Portfolio** (Intermediate) — Asset allocation, diversification, ETF selection, rebalancing strategies.
- **Advanced Strategies** (Advanced) — Options basics, sector analysis, technical indicators, quantitative methods.

**Each lesson includes:**
- Rich markdown content with real-world examples and data.
- Interactive quizzes with explanations for each answer.
- Direct links to AI tools (e.g., "Go try the Stock Screener now").
- End-of-module final quizzes that track scores on the leaderboard.

**Progress tracking:** All quiz scores and lesson completions are stored in Supabase with best-score tracking across attempts.

**Key files:** `finlearn-ai-assistant-main/src/data/moduleContent.ts`, `finlearn-ai-assistant-main/src/pages/LearningModule.tsx`

---

### 3. Stock Screener

Real-time stock analysis with AI-generated BUY/HOLD/SELL signals for curated watchlists.

**How it works:**
1. Fetches 30 days of daily OHLCV data from **Polygon.io** for each ticker.
2. Generates a candlestick chart image programmatically (matplotlib).
3. Runs the chart through two **computer vision models** (see Chart Analyzer below) to detect trends and support/resistance levels.
4. Annotates the chart with S/R lines and trend indicators.
5. Runs **FinBERT sentiment analysis** on the latest news articles for each stock.
6. Generates a **Gemini AI analysis paragraph** summarizing all signals.
7. Computes a composite signal (BUY/HOLD/SELL) with confidence percentage.

**Default watchlists:** Tech Giants, Finance, Consumer, Healthcare, ETFs, Growth (36 stocks total, pre-loaded on startup).

**Caching:** Results are cached for 15 minutes to avoid redundant API calls.

**Key files:** `backend/main.py` (endpoints + chart generation), `finlearn-ai-assistant-main/src/pages/StockScreener.tsx`

---

### 4. Chart Analyzer (Computer Vision)

Upload any stock chart image and get AI-detected trend classification and support/resistance zones.

**Models:**
- **Trend Classifier** — EfficientNet-B2 backbone trained on synthetic + real chart data. Classifies charts as uptrend, downtrend, or sideways with confidence scores and slope regression.
- **S/R Zone Detector** — ResNet-34 backbone that predicts 10 support and 10 resistance zones as probability distributions across the price range.

**Additional capabilities:**
- **Explainable AI (Grad-CAM)**: Generates heatmap overlays showing exactly which parts of the chart the model focused on for its prediction.
- **Annotated output**: Returns the original image with S/R lines and trend indicators drawn on it.

**Training data:** Generated from real Polygon.io price data, rendered as candlestick charts with various styles and augmentations (albumentations).

**Key files:** `chart-vision/models/trend_classifier.py`, `chart-vision/models/sr_detector.py`, `chart-vision/train_sr_model_v2.py`, `chart-vision/train_trend_model_v2.py`, `backend/main.py` (XAI endpoint)

---

### 5. Sentiment Analyzer (FinBERT)

AI-powered news sentiment analysis using a financial domain-specific language model.

**How it works:**
1. Fetches recent news articles (up to 15, last 7 days) for a given ticker from Polygon.io News API.
2. Runs each article's title and description through **FinBERT** (ProsusAI/finbert), a BERT model fine-tuned on financial text.
3. Classifies each article as positive, negative, or neutral with confidence scores.
4. Aggregates results into an overall sentiment score (-1 to +1) and generates a signal (BULLISH/BEARISH/NEUTRAL).

**Output includes:** Per-article sentiment breakdowns, overall score, signal strength, and article counts by sentiment category.

**Key files:** `chart-vision/models/sentiment_analyzer.py`, `chart-vision/utils/news_fetcher.py`, `finlearn-ai-assistant-main/src/pages/SentimentAnalyzer.tsx`

---

### 6. Portfolio Simulator

A compound growth calculator that visualizes how investments grow over time.

**Parameters:** Initial investment, monthly contribution, time horizon (years), expected annual return, and stock/bond allocation split.

**Output:** Year-by-year portfolio value chart showing total contributions vs. growth, with final value, total contributed, and total growth breakdown.

**Key files:** `finlearn-ai-assistant-main/src/pages/Simulator.tsx`

---

### 7. ETF Recommender

A three-step tool: risk assessment quiz, personalized ETF allocation, and Monte Carlo simulation.

**Step 1 — Risk Quiz:** Five behavioral questions (time horizon, loss tolerance, goals, knowledge level, savings percentage) that map to a risk profile: Conservative, Moderate, Balanced, Growth, or Aggressive.

**Step 2 — ETF Allocation:** Based on the risk profile, recommends a portfolio of Vanguard ETFs (VTI, VXUS, BND, TIP, QQQ, VUG, etc.) with percentage allocations. Users can customize allocations and add thematic overlays (Clean Energy, Tech, Crypto, etc.).

**Step 3 — Monte Carlo Simulation:** Runs 1,000 simulations of portfolio growth using the recommended allocation. Uses each ETF's historical average return and volatility with Box-Muller random sampling. Displays median, 10th, 25th, 75th, and 90th percentile outcomes with probability of reaching $500K and $1M milestones.

**Key files:** `finlearn-ai-assistant-main/src/pages/ETFRecommender.tsx`

---

### 8. AI Stock Discovery & Portfolio Builder

The flagship analysis tool. Performs a deep analysis of all S&P 500 stocks, scores them using sector-normalized metrics, and lets users build custom optimized portfolios.

**Phase 1 — Universe Analysis (runs as background job or scheduled script):**
1. Fetches 6 months of daily price data for ~230+ S&P 500 stocks from Polygon.io.
2. Computes per-stock metrics: 1M/3M/6M returns, 30-day and 90-day annualized volatility, max drawdown, price position, volume trends.
3. Fetches recent news and runs FinBERT sentiment analysis (or keyword-based fallback).
4. **Sector normalization**: All metrics are normalized within each stock's sector so that a "good" P/E for a tech stock is compared against other tech stocks, not utilities.
5. **Composite scoring**: Weighted combination of 5 factor scores:
   - Valuation (30%) — Price position within sector range
   - Fundamentals (20%) — Revenue/income metrics
   - Sentiment (15%) — News sentiment score
   - Momentum (20%) — Multi-timeframe returns
   - Risk (15%) — Volatility and drawdown metrics
6. Results are cached to `backend/cache/sp500_analysis.json` and persist across server restarts.

**Phase 2 — Stock Discovery UI:**
- Displays all analyzed stocks in a filterable, sortable table.
- Filters: Ticker search, sector dropdown, min/max composite score, sort by score/ticker/sector/return/sentiment.
- Each row shows ticker, sector, composite score, factor score breakdown, price, returns, volatility, and sentiment.

**Phase 3 — Portfolio Optimization:**
- Users select stocks from the table to build a custom portfolio.
- The optimizer uses **Modern Portfolio Theory (MPT)** via SciPy's SLSQP solver.
- **Forward-looking expected returns**: Instead of extrapolating past returns, the model derives expected returns from factor scores:
  - Base = risk-free rate (4.5%) + equity risk premium (5.5%)
  - Valuation premium: Undervalued stocks (high valuation score) get up to +4% expected return
  - Quality premium: Strong fundamentals add up to +2.5%
  - Sentiment tilt: Positive news sentiment adds up to +1.5%
  - Momentum tilt: Recent trend continuation adds up to +1%
  - Risk premium: Higher-risk stocks require higher expected return compensation (up to +2%)
  - Individual stock returns capped between 2% and 25% annualized
- **Minimum weight constraint**: Every selected stock gets at least ~30% of equal weight, ensuring all selected stocks appear in the final portfolio.
- **Correlation model**: Same-sector stocks have higher assumed correlation (0.6) vs cross-sector (0.4).
- **Optimization objectives**: Maximize Sharpe ratio, minimize risk, or maximize return.
- **Output**: Optimized weights, expected return, portfolio volatility, Sharpe ratio, sector allocation breakdown, concentration index, and per-stock detail.

**Standalone script:** `scripts/run_universe_analysis.py` runs the full S&P 500 analysis from the command line for personal use. `scripts/setup_weekly_analysis.sh` sets up a cron job for weekly automated updates.

**Key files:** `backend/stock_universe_analyzer.py`, `backend/sector_normalizer.py`, `backend/stock_scorer.py`, `backend/portfolio_optimizer.py`, `finlearn-ai-assistant-main/src/pages/AIStockDiscovery.tsx`

---

### 9. Leaderboard & Community

**Leaderboard:** Global and per-module rankings based on quiz performance. Tracks total score, quizzes completed, modules completed, and average percentage. Supports sample data for demo purposes when no real users exist.

**Community/Social:** User profiles with activity tracking, online status, and learning progress. Designed for future social features (discussions, sharing analysis).

**Key files:** `finlearn-ai-assistant-main/src/pages/Leaderboard.tsx`, `finlearn-ai-assistant-main/src/pages/Social.tsx`

---

## Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| **React 18** | UI framework |
| **TypeScript** | Type-safe development |
| **Vite** | Build tool and dev server |
| **Tailwind CSS** | Utility-first styling |
| **shadcn/ui** (Radix UI) | Accessible component library |
| **Recharts** | Data visualization / charts |
| **React Router** | Client-side routing |
| **React Query** | Server state management |
| **Supabase JS** | Auth and database client |
| **Lucide React** | Icon library |
| **Zod** | Schema validation |

### Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | REST API framework |
| **Uvicorn** | ASGI server |
| **Python 3.13** | Backend language |
| **Polygon.io API** | Real-time and historical market data, news |
| **Supabase** | Auth, user profiles, quiz scores, progress tracking |

### Machine Learning
| Technology | Purpose |
|---|---|
| **PyTorch** | Deep learning framework |
| **torchvision** | Pre-trained CNN backbones (ResNet, EfficientNet) |
| **Transformers (HuggingFace)** | FinBERT sentiment model |
| **sentence-transformers** | Embedding model for RAG (all-MiniLM-L6-v2) |
| **Cross-Encoder** | Reranker for RAG (BAAI/bge-reranker-base) |
| **SciPy** | Portfolio optimization (SLSQP solver) |
| **NumPy / Pandas** | Data processing |
| **OpenCV** | Image processing for chart analysis |
| **Albumentations** | Training data augmentation |
| **scikit-learn** | Model evaluation metrics |

### LLM / AI
| Technology | Purpose |
|---|---|
| **Google Gemini** (gemini-1.5-flash) | LLM for RAG chat responses and stock analysis summaries |
| **Ollama** (optional) | Local LLM fallback (Llama 3) |
| **FinBERT** (ProsusAI/finbert) | Financial sentiment classification |

### Infrastructure
| Technology | Purpose |
|---|---|
| **AWS EC2** | Backend deployment |
| **Nginx** | Reverse proxy |
| **systemd** | Process management |
| **Cron** | Scheduled S&P 500 analysis updates |

---

## Project Structure

```
FinLearnAI/
├── finlearn-ai-assistant-main/     # React frontend
│   ├── src/
│   │   ├── pages/                  # All page components
│   │   │   ├── Index.tsx           # Auth (login/signup)
│   │   │   ├── Dashboard.tsx       # Main dashboard
│   │   │   ├── StockScreener.tsx   # Real-time stock analysis
│   │   │   ├── ChartAnalyzer.tsx   # Upload chart for CV analysis
│   │   │   ├── SentimentAnalyzer.tsx # FinBERT sentiment tool
│   │   │   ├── Simulator.tsx       # Portfolio growth simulator
│   │   │   ├── ETFRecommender.tsx  # Risk quiz + Monte Carlo
│   │   │   ├── AIStockDiscovery.tsx # S&P 500 discovery + portfolio builder
│   │   │   ├── LearningModule.tsx  # Interactive lessons + quizzes
│   │   │   ├── Leaderboard.tsx     # Quiz rankings
│   │   │   └── Social.tsx          # Community page
│   │   ├── components/             # Shared components (ChatPanel, Quiz, etc.)
│   │   ├── data/moduleContent.ts   # All lesson content + quizzes
│   │   └── integrations/supabase/  # Supabase client config
│   └── package.json
│
├── backend/                        # FastAPI backend
│   ├── main.py                     # All API endpoints + model loading
│   ├── stock_universe_analyzer.py  # S&P 500 data fetching + metrics
│   ├── sector_normalizer.py        # Sector-relative normalization
│   ├── stock_scorer.py             # Composite scoring system
│   ├── portfolio_optimizer.py      # MPT optimization + factor model
│   ├── cache/
│   │   └── sp500_analysis.json     # Cached analysis results
│   ├── requirements.txt
│   └── supabase_schema.sql         # Database schema
│
├── chart-vision/                   # CV model training + inference
│   ├── models/
│   │   ├── trend_classifier.py     # Trend detection model
│   │   ├── sr_detector.py          # Support/resistance detection
│   │   └── sentiment_analyzer.py   # FinBERT wrapper
│   ├── utils/
│   │   ├── chart_generator.py      # Synthetic chart generation
│   │   └── news_fetcher.py         # Polygon news API client
│   ├── checkpoints/                # Trained model weights (.pt)
│   ├── train_trend_model_v2.py     # Trend model training script
│   ├── train_sr_model_v2.py        # S/R model training script
│   ├── explainable_ai.py           # Grad-CAM visualization
│   └── requirements.txt
│
├── quantcademy-app/                # RAG system + knowledge base
│   ├── rag/
│   │   ├── knowledge_base.py       # Financial education content
│   │   ├── knowledge_base_v2.py    # Chunked + tiered version
│   │   ├── retrieval.py            # Hybrid BM25 + semantic retrieval
│   │   ├── vector_store.py         # ChromaDB vector store
│   │   ├── llm_provider.py         # Gemini / Ollama LLM interface
│   │   └── content_fetcher.py      # Web content scraper for KB
│   ├── pages/                      # Original Streamlit app pages
│   └── requirements.txt
│
├── scripts/                        # Utility scripts
│   ├── run_universe_analysis.py    # Manual S&P 500 analysis
│   └── setup_weekly_analysis.sh    # Cron job setup
│
├── deploy/
│   └── setup_ec2.sh                # EC2 deployment script
│
├── eda/                            # Exploratory data analysis
│   ├── eda.py
│   └── SCFP2022.csv
│
└── rag_validation/                 # RAG quality testing
    ├── validate_rag.py
    ├── test_set.json
    └── validation_results.json
```

---

## Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- Polygon.io API key
- Supabase project (URL + anon key)
- Google Gemini API key (for RAG chat)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file with your keys
# POLYGON_API_KEY=your_key
# SUPABASE_URL=your_url
# SUPABASE_KEY=your_key
# GEMINI_API_KEY=your_key

# Start the server (preloads all models on startup)
python main.py
```

The backend starts on `http://localhost:8000`. On startup it preloads:
- RAG embedding model + reranker
- Chart Vision CV models (trend + S/R)
- FinBERT sentiment model
- Default watchlist stock data (background)
- S&P 500 analysis cache (from file)

### Frontend

```bash
cd finlearn-ai-assistant-main
npm install
npm run dev
```

The frontend starts on `http://localhost:5173`.

### S&P 500 Analysis (First Run)

Before using the AI Stock Discovery tool, run the initial analysis:

```bash
cd scripts
source ../backend/venv/bin/activate
python run_universe_analysis.py
```

This analyzes all S&P 500 stocks and saves results to `backend/cache/sp500_analysis.json`. Takes approximately 1-5 minutes depending on API response times.

To set up weekly automatic updates:

```bash
bash scripts/setup_weekly_analysis.sh
```

---

## Deployment

An EC2 deployment script is provided at `deploy/setup_ec2.sh`. It sets up:
- Python environment with all dependencies
- Nginx as a reverse proxy
- systemd service for the FastAPI backend
- SSL can be configured with Certbot

The frontend can be deployed to any static hosting (Vercel, Netlify, S3+CloudFront) by running `npm run build` and serving the `dist/` directory.
