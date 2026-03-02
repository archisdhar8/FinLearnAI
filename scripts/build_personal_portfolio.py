#!/usr/bin/env python3
"""
Personal Portfolio Builder
==========================

Selects the best 2-4 stocks per S&P 500 sector using:
  1. Existing composite scores (valuation, fundamentals, sentiment, momentum, risk)
  2. Technical analysis (RSI, MACD, MA crossovers, Bollinger Bands)
  3. Backtesting (momentum & mean-reversion signals)
  4. ML model (Gradient Boosting trained on all features)
  5. Macro-aware expected return model (FRED-based)

Then optimises the portfolio for maximum Sharpe ratio.

Usage:
    cd FinLearnAI
    source backend/venv/bin/activate
    python scripts/build_personal_portfolio.py [--stocks-per-sector 3] [--top-candidates 10]
"""

import os
import sys
import json
import argparse
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score

warnings.filterwarnings("ignore")

# Ensure backend modules are importable
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Load .env
from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

CACHE_FILE = BACKEND_DIR / "cache" / "sp500_analysis.json"
STOCKS_PER_SECTOR_DEFAULT = 3
TOP_CANDIDATES_DEFAULT = 10  # pre-screen: keep top N per sector before deep analysis


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 0 — Load cached S&P 500 analysis
# ═══════════════════════════════════════════════════════════════════════════════

def load_sp500_cache() -> list:
    """Load pre-computed S&P 500 analysis from cache."""
    if not CACHE_FILE.exists():
        print("ERROR: Cache file not found. Run the S&P 500 analysis first:")
        print("  python scripts/run_universe_analysis.py")
        sys.exit(1)

    with open(CACHE_FILE) as f:
        data = json.load(f)

    stocks = data.get("stocks", [])
    print(f"Loaded {len(stocks)} stocks from cache ({data.get('timestamp', 'unknown')})")
    return stocks


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 1 — Pre-screen: top N candidates per sector
# ═══════════════════════════════════════════════════════════════════════════════

def prescreen(stocks: list, top_n: int) -> dict:
    """Return top_n stocks per sector by composite score."""
    by_sector = defaultdict(list)
    for s in stocks:
        by_sector[s.get("sector", "Other")].append(s)

    candidates = {}
    for sector, sector_stocks in sorted(by_sector.items()):
        ranked = sorted(sector_stocks, key=lambda x: x.get("composite_score", 0), reverse=True)
        candidates[sector] = ranked[:top_n]
        print(f"  {sector:20s}: {len(sector_stocks):3d} stocks → top {len(candidates[sector])}")

    total = sum(len(v) for v in candidates.values())
    print(f"  Pre-screened {total} candidates across {len(candidates)} sectors\n")
    return candidates


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 2 — Technical Analysis (Polygon daily prices)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_daily_prices(ticker: str, client, days: int = 365) -> pd.DataFrame:
    """Fetch daily OHLCV from Polygon."""
    end = datetime.now()
    start = end - timedelta(days=days)
    try:
        aggs = list(client.list_aggs(
            ticker, 1, "day",
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            limit=50000,
        ))
        if not aggs:
            return pd.DataFrame()
        df = pd.DataFrame([{
            "date": datetime.fromtimestamp(a.timestamp / 1000),
            "open": a.open, "high": a.high, "low": a.low,
            "close": a.close, "volume": a.volume,
        } for a in aggs])
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except Exception as e:
        return pd.DataFrame()


def compute_rsi(closes: pd.Series, period: int = 14) -> float:
    """Relative Strength Index (latest value)."""
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if len(rsi) > 0 and not np.isnan(rsi.iloc[-1]) else 50.0


def compute_macd(closes: pd.Series) -> dict:
    """MACD (12, 26, 9) — returns signal, histogram, crossover."""
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": float(macd_line.iloc[-1]) if len(macd_line) else 0,
        "signal": float(signal_line.iloc[-1]) if len(signal_line) else 0,
        "histogram": float(histogram.iloc[-1]) if len(histogram) else 0,
        "bullish_cross": bool(
            len(histogram) > 1
            and histogram.iloc[-1] > 0
            and histogram.iloc[-2] <= 0
        ),
    }


def compute_ma_crossover(closes: pd.Series) -> dict:
    """50-day vs 200-day moving average crossover."""
    if len(closes) < 200:
        return {"ma50": 0, "ma200": 0, "golden_cross": False, "above_ma50": False}
    ma50 = closes.rolling(50).mean()
    ma200 = closes.rolling(200).mean()
    return {
        "ma50": float(ma50.iloc[-1]),
        "ma200": float(ma200.iloc[-1]),
        "golden_cross": bool(ma50.iloc[-1] > ma200.iloc[-1]),
        "above_ma50": bool(closes.iloc[-1] > ma50.iloc[-1]),
    }


def compute_bollinger(closes: pd.Series, period: int = 20, num_std: float = 2.0) -> dict:
    """Bollinger Band position (0 = at lower band, 1 = at upper band)."""
    if len(closes) < period:
        return {"bb_position": 0.5, "bb_width": 0}
    ma = closes.rolling(period).mean()
    std = closes.rolling(period).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    price = closes.iloc[-1]
    width = float((upper.iloc[-1] - lower.iloc[-1]) / ma.iloc[-1]) if ma.iloc[-1] > 0 else 0
    band_range = upper.iloc[-1] - lower.iloc[-1]
    position = float((price - lower.iloc[-1]) / band_range) if band_range > 0 else 0.5
    return {"bb_position": np.clip(position, 0, 1), "bb_width": width}


def compute_technical_indicators(df: pd.DataFrame) -> dict:
    """Compute all technical indicators from daily OHLCV data."""
    if df.empty or len(df) < 30:
        return {
            "rsi": 50.0, "macd_histogram": 0.0, "macd_bullish": False,
            "golden_cross": False, "above_ma50": False,
            "bb_position": 0.5, "bb_width": 0.0,
            "avg_volume_ratio": 1.0, "price_trend_slope": 0.0,
        }

    closes = df["close"]
    volumes = df["volume"]

    rsi = compute_rsi(closes)
    macd = compute_macd(closes)
    ma = compute_ma_crossover(closes)
    bb = compute_bollinger(closes)

    # Volume trend: recent 10-day avg vs 50-day avg
    vol_10 = volumes.tail(10).mean()
    vol_50 = volumes.tail(50).mean() if len(volumes) >= 50 else vol_10
    avg_vol_ratio = float(vol_10 / vol_50) if vol_50 > 0 else 1.0

    # Price trend: linear regression slope of last 60 days (normalised)
    recent = closes.tail(60)
    if len(recent) > 10:
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent.values, 1)[0]
        price_trend = float(slope / recent.mean()) if recent.mean() > 0 else 0
    else:
        price_trend = 0.0

    return {
        "rsi": rsi,
        "macd_histogram": macd["histogram"],
        "macd_bullish": macd["bullish_cross"],
        "golden_cross": ma["golden_cross"],
        "above_ma50": ma["above_ma50"],
        "bb_position": bb["bb_position"],
        "bb_width": bb["bb_width"],
        "avg_volume_ratio": avg_vol_ratio,
        "price_trend_slope": price_trend,
    }


def run_technical_analysis(candidates: dict, polygon_key: str) -> dict:
    """Fetch prices and compute TA for all candidates."""
    from polygon import RESTClient
    client = RESTClient(polygon_key)

    print("Phase 2: Technical Analysis (fetching daily prices from Polygon)...")
    all_ta = {}
    flat = [(sec, s) for sec, stocks in candidates.items() for s in stocks]
    total = len(flat)

    for i, (sector, stock) in enumerate(flat):
        ticker = stock["ticker"]
        print(f"  [{i+1:3d}/{total}] {ticker:6s} ({sector})", end="", flush=True)
        df = fetch_daily_prices(ticker, client, days=400)
        ta = compute_technical_indicators(df)
        all_ta[ticker] = ta
        print(f"  RSI={ta['rsi']:.0f}  MACD={'▲' if ta['macd_bullish'] else '▼'}  "
              f"MA={'G' if ta['golden_cross'] else 'D'}  BB={ta['bb_position']:.2f}")

        # Small delay to respect rate limits
        import time
        time.sleep(0.15)

    print(f"  Completed TA for {len(all_ta)} stocks\n")
    return all_ta


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 3 — Backtesting (momentum & mean-reversion signals)
# ═══════════════════════════════════════════════════════════════════════════════

def backtest_signals(stock: dict) -> dict:
    """
    Generate backtesting-style signals from cached return data.

    Momentum signal:  positive 3M + positive 6M = strong trend
    Mean reversion:   low price_position + high fundamentals = bounce candidate
    Risk-adjusted:    return / volatility = consistency
    """
    r1m = stock.get("return_1m", 0)
    r3m = stock.get("return_3m", 0)
    r6m = stock.get("return_6m", 0)
    vol_90 = max(stock.get("volatility_90d", 20), 1)
    price_pos = stock.get("price_position", 50)
    fund_score = stock.get("factor_scores", {}).get("fundamentals", 50)
    val_score = stock.get("factor_scores", {}).get("valuation", 50)

    # Momentum score: weighted trend consistency
    momentum_signal = 0
    if r3m > 0 and r6m > 0:
        momentum_signal = 1.0  # Consistent uptrend
    elif r3m > 0 or r6m > 0:
        momentum_signal = 0.5  # Mixed
    else:
        momentum_signal = 0.0  # Downtrend

    # Acceleration: improving recently
    acceleration = (r1m - r3m / 3) if r3m != 0 else 0

    # Risk-adjusted return (Sortino-like)
    risk_adj_return = r6m / vol_90 if vol_90 > 0 else 0

    # Mean reversion: cheap + quality
    mean_rev_signal = 0
    if price_pos < 30 and fund_score > 60:
        mean_rev_signal = 1.0  # Oversold + quality
    elif price_pos < 50 and val_score > 60:
        mean_rev_signal = 0.5  # Reasonable value

    # Drawdown recovery potential
    max_dd = abs(stock.get("max_drawdown", 0))
    recovery_potential = min(max_dd / 20, 1.0) if val_score > 50 else 0

    return {
        "momentum_signal": momentum_signal,
        "acceleration": acceleration,
        "risk_adj_return": risk_adj_return,
        "mean_rev_signal": mean_rev_signal,
        "recovery_potential": recovery_potential,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 4 — ML Model (Gradient Boosting)
# ═══════════════════════════════════════════════════════════════════════════════

def build_ml_features(stock: dict, ta: dict, bt: dict) -> dict:
    """Combine all features into a flat dict for ML."""
    fs = stock.get("factor_scores", {})
    return {
        # Factor scores
        "valuation": fs.get("valuation", 50),
        "fundamentals": fs.get("fundamentals", 50),
        "sentiment_score_factor": fs.get("sentiment", 50),
        "momentum_factor": fs.get("momentum", 50),
        "risk_factor": fs.get("risk", 50),
        "composite_score": stock.get("composite_score", 50),

        # Returns & volatility
        "return_1m": stock.get("return_1m", 0),
        "return_3m": stock.get("return_3m", 0),
        "return_6m": stock.get("return_6m", 0),
        "volatility_30d": stock.get("volatility_30d", 20),
        "volatility_90d": stock.get("volatility_90d", 20),
        "max_drawdown": stock.get("max_drawdown", 0),
        "volume_trend": stock.get("volume_trend", 0),
        "price_position": stock.get("price_position", 50),
        "sentiment_raw": stock.get("sentiment_score", 0),

        # Technical indicators
        "rsi": ta.get("rsi", 50),
        "macd_histogram": ta.get("macd_histogram", 0),
        "macd_bullish": int(ta.get("macd_bullish", False)),
        "golden_cross": int(ta.get("golden_cross", False)),
        "above_ma50": int(ta.get("above_ma50", False)),
        "bb_position": ta.get("bb_position", 0.5),
        "bb_width": ta.get("bb_width", 0),
        "avg_volume_ratio": ta.get("avg_volume_ratio", 1),
        "price_trend_slope": ta.get("price_trend_slope", 0),

        # Backtesting signals
        "momentum_signal": bt.get("momentum_signal", 0),
        "acceleration": bt.get("acceleration", 0),
        "risk_adj_return": bt.get("risk_adj_return", 0),
        "mean_rev_signal": bt.get("mean_rev_signal", 0),
        "recovery_potential": bt.get("recovery_potential", 0),
    }


def train_ml_model(all_features: list, all_targets: list) -> tuple:
    """
    Train a Gradient Boosting model to predict expected return.

    Uses cross-validation to estimate generalization performance.
    Returns (model, scaler, cv_score).
    """
    X = pd.DataFrame(all_features)
    y = np.array(all_targets)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_leaf=3,
        random_state=42,
    )

    # Cross-validation
    cv_scores = cross_val_score(model, X_scaled, y, cv=min(5, len(y) // 3), scoring="r2")
    print(f"  ML Cross-validation R²: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Fit on full data
    model.fit(X_scaled, y)

    # Feature importance
    importances = sorted(
        zip(X.columns, model.feature_importances_),
        key=lambda x: -x[1]
    )
    print("  Top 10 features:")
    for feat, imp in importances[:10]:
        print(f"    {feat:25s}: {imp:.4f}")

    return model, scaler, cv_scores.mean()


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 5 — Final Scoring & Selection
# ═══════════════════════════════════════════════════════════════════════════════

def compute_final_score(
    stock: dict,
    ta: dict,
    bt: dict,
    ml_score: float,
    expected_return: float,
) -> float:
    """
    Combine all signal sources into a final selection score.

    Weights:
      30% — Macro-aware expected return (forward-looking, theory-grounded)
      25% — ML model prediction
      20% — Composite score (valuation + fundamentals + sentiment + momentum + risk)
      15% — Technical signals (RSI, MACD, MA, Bollinger)
      10% — Backtesting signals (momentum, mean reversion)
    """
    # Normalise expected return to 0-100 scale
    er_score = np.clip((expected_return - 0.02) / (0.25 - 0.02) * 100, 0, 100)

    # ML prediction to 0-100
    ml_norm = np.clip((ml_score - 0.02) / (0.25 - 0.02) * 100, 0, 100)

    # Composite score already 0-100
    comp_score = stock.get("composite_score", 50)

    # Technical score (0-100)
    rsi_score = 100 - abs(ta.get("rsi", 50) - 50) * 2  # Best near 50-60
    if ta.get("rsi", 50) > 70:
        rsi_score = max(rsi_score - 20, 0)  # Overbought penalty
    elif ta.get("rsi", 50) < 30:
        rsi_score = max(rsi_score - 10, 0)  # Oversold mild penalty
    macd_score = 70 if ta.get("macd_histogram", 0) > 0 else 30
    if ta.get("macd_bullish", False):
        macd_score = 90
    ma_score = 70 if ta.get("golden_cross", False) else 40
    if ta.get("above_ma50", False):
        ma_score += 15
    bb_score = np.clip(ta.get("bb_position", 0.5) * 100, 0, 100)
    trend_score = np.clip(50 + ta.get("price_trend_slope", 0) * 5000, 0, 100)

    tech_score = (
        0.20 * rsi_score
        + 0.25 * macd_score
        + 0.25 * ma_score
        + 0.15 * bb_score
        + 0.15 * trend_score
    )

    # Backtest score (0-100)
    bt_score = (
        bt.get("momentum_signal", 0) * 30
        + np.clip(bt.get("risk_adj_return", 0) * 10, 0, 30)
        + bt.get("mean_rev_signal", 0) * 20
        + bt.get("recovery_potential", 0) * 10
        + np.clip(bt.get("acceleration", 0) * 2, 0, 10)
    )

    # Weighted final score
    final = (
        0.30 * er_score
        + 0.25 * ml_norm
        + 0.20 * comp_score
        + 0.15 * tech_score
        + 0.10 * bt_score
    )

    return float(final)


def select_portfolio(
    candidates: dict,
    ta_data: dict,
    bt_data: dict,
    ml_predictions: dict,
    er_data: dict,
    stocks_per_sector: int,
) -> list:
    """Select top N stocks per sector based on final combined score."""
    selected = []

    print("Phase 5: Final Selection")
    print(f"{'Sector':<20s}  {'Ticker':<7s} {'Final':>6s} {'ER%':>6s} "
          f"{'ML%':>6s} {'Comp':>5s} {'Tech':>5s} {'BT':>4s}")
    print("-" * 80)

    for sector in sorted(candidates.keys()):
        scored = []
        for stock in candidates[sector]:
            ticker = stock["ticker"]
            ta = ta_data.get(ticker, {})
            bt = bt_data.get(ticker, {})
            ml_pred = ml_predictions.get(ticker, 0.10)
            er = er_data.get(ticker, 0.10)

            final = compute_final_score(stock, ta, bt, ml_pred, er)
            scored.append((stock, final, er, ml_pred))

        scored.sort(key=lambda x: -x[1])

        for stock, final, er, ml_pred in scored[:stocks_per_sector]:
            ticker = stock["ticker"]
            ta = ta_data.get(ticker, {})
            bt = bt_data.get(ticker, {})
            print(f"{sector:<20s}  {ticker:<7s} {final:6.1f} {er*100:6.1f} "
                  f"{ml_pred*100:6.1f} {stock.get('composite_score',0):5.1f} "
                  f"{ta.get('rsi',50):5.0f} {bt.get('momentum_signal',0):4.1f}")
            selected.append(stock)

    print(f"\nSelected {len(selected)} stocks across {len(candidates)} sectors\n")
    return selected


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 6 — Portfolio Optimisation
# ═══════════════════════════════════════════════════════════════════════════════

def optimise_and_analyse(selected: list) -> dict:
    """Run the macro-aware portfolio optimizer on selected stocks."""
    from portfolio_optimizer import PortfolioOptimizer

    print("Phase 6: Portfolio Optimisation (Sharpe maximisation)...")
    weights = PortfolioOptimizer.optimize_portfolio(
        selected,
        objective="sharpe",
        constraints={"min_weight": 0.02, "max_weight": 0.15},
    )
    analysis = PortfolioOptimizer.analyze_portfolio(selected, weights)
    return analysis


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 7 — Display Results
# ═══════════════════════════════════════════════════════════════════════════════

def print_portfolio(analysis: dict):
    """Pretty-print the final portfolio."""
    print("\n" + "=" * 80)
    print("  YOUR PERSONAL S&P 500 PORTFOLIO")
    print("=" * 80)

    print(f"\n  Macro Regime:     {analysis.get('macro_regime', {}).get('state', 'Unknown')}")
    print(f"  Risk-free Rate:   {analysis.get('risk_free_rate', 0):.2f}%")
    print(f"  Expected Return:  {analysis.get('expected_return', 0):.2f}%")
    print(f"  Volatility:       {analysis.get('volatility', 0):.2f}%")
    print(f"  Sharpe Ratio:     {analysis.get('sharpe_ratio', 0):.3f}")
    print(f"  Num Holdings:     {analysis.get('num_holdings', 0)}")
    print(f"  Concentration:    {analysis.get('concentration_index', 0):.4f} (HHI)")

    # Sector allocation
    print(f"\n  Sector Allocation:")
    for sector, pct in sorted(
        analysis.get("sector_allocation", {}).items(),
        key=lambda x: -x[1],
    ):
        bar = "█" * int(pct / 2)
        print(f"    {sector:<20s} {pct:6.1f}% {bar}")

    # Holdings
    print(f"\n  Holdings (sorted by weight):")
    print(f"  {'Ticker':<7s} {'Weight':>7s} {'E[R]':>7s} {'Sector':<20s} "
          f"{'Mkt':>5s} {'Yield':>5s} {'Grow':>5s} {'Rever':>5s} {'Macro':>5s}")
    print(f"  {'-'*75}")

    for detail in analysis.get("stock_details", []):
        rc = detail.get("return_components", {})
        print(
            f"  {detail['ticker']:<7s} "
            f"{detail['weight']:6.1f}% "
            f"{detail['expected_return']:6.1f}% "
            f"{detail['sector']:<20s} "
            f"{rc.get('market_baseline', 0):5.1f} "
            f"{rc.get('cash_yield', 0):5.1f} "
            f"{rc.get('growth', 0):5.1f} "
            f"{rc.get('valuation_reversion', 0):5.1f} "
            f"{rc.get('macro_adjustment', 0):5.1f}"
        )

    # Return decomposition
    print(f"\n  Portfolio Return Decomposition:")
    decomp = analysis.get("return_decomposition", {})
    for comp in ["market_return", "cash_yield_premium", "growth_premium",
                 "multiple_reversion", "macro_adjustment", "risk_adjustment",
                 "factor_tilt", "total"]:
        val = decomp.get(comp, 0)
        label = comp.replace("_", " ").title()
        marker = " ◀" if comp == "total" else ""
        print(f"    {label:<25s} {val:+7.2f}%{marker}")

    print(f"\n  Methodology: {analysis.get('methodology', 'N/A')}")
    print("=" * 80)

    # Save JSON
    output_file = BACKEND_DIR.parent / "scripts" / "my_portfolio.json"
    with open(output_file, "w") as f:
        json.dump(analysis, f, indent=2)
    print(f"\n  Full analysis saved to: {output_file}")

    # Save CSV
    import csv
    csv_file = BACKEND_DIR.parent / "scripts" / "my_portfolio.csv"
    rows = []
    for detail in analysis.get("stock_details", []):
        rc = detail.get("return_components", {})
        rows.append({
            "Ticker": detail["ticker"],
            "Sector": detail.get("sector", ""),
            "Weight (%)": detail["weight"],
            "Expected Return (%)": detail["expected_return"],
            "Volatility (%)": detail.get("volatility", ""),
            "Composite Score": detail.get("composite_score", ""),
            "Market Baseline (%)": rc.get("market_baseline", ""),
            "Cash Yield (%)": rc.get("cash_yield", ""),
            "Growth (%)": rc.get("growth", ""),
            "Valuation Reversion (%)": rc.get("valuation_reversion", ""),
            "Macro Adjustment (%)": rc.get("macro_adjustment", ""),
            "Risk Premium (%)": rc.get("risk_premium", ""),
            "Factor Tilt (%)": rc.get("factor_tilt", ""),
        })
    if rows:
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    print(f"  CSV saved to:  {csv_file}\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Build a personal S&P 500 portfolio")
    parser.add_argument("--stocks-per-sector", type=int, default=STOCKS_PER_SECTOR_DEFAULT,
                        help="Number of stocks to select per sector (default: 3)")
    parser.add_argument("--top-candidates", type=int, default=TOP_CANDIDATES_DEFAULT,
                        help="Pre-screen: top N per sector for deep analysis (default: 10)")
    parser.add_argument("--skip-ta", action="store_true",
                        help="Skip Polygon TA fetch (faster, uses cached data only)")
    args = parser.parse_args()

    polygon_key = os.environ.get("POLYGON_API_KEY")
    if not polygon_key and not args.skip_ta:
        print("WARNING: No POLYGON_API_KEY found. Skipping technical analysis.")
        args.skip_ta = True

    print("=" * 60)
    print("  PERSONAL PORTFOLIO BUILDER")
    print(f"  {args.stocks_per_sector} stocks/sector | "
          f"top {args.top_candidates} candidates | "
          f"TA={'ON' if not args.skip_ta else 'OFF'}")
    print("=" * 60 + "\n")

    # ── Phase 0: Load data ──────────────────────────────────────────────
    stocks = load_sp500_cache()

    # ── Phase 1: Pre-screen ─────────────────────────────────────────────
    print("\nPhase 1: Pre-screening by composite score...")
    candidates = prescreen(stocks, args.top_candidates)

    # ── Phase 2: Technical analysis ─────────────────────────────────────
    ta_data = {}
    if not args.skip_ta:
        ta_data = run_technical_analysis(candidates, polygon_key)
    else:
        print("Phase 2: Technical Analysis — SKIPPED (using cached features)\n")
        # Generate pseudo-TA from cached data
        for sector, sector_stocks in candidates.items():
            for s in sector_stocks:
                ta_data[s["ticker"]] = {
                    "rsi": 50 + (s.get("return_1m", 0) / 5),  # approximate
                    "macd_histogram": s.get("return_1m", 0) - s.get("return_3m", 0) / 3,
                    "macd_bullish": s.get("return_1m", 0) > 0 and s.get("return_3m", 0) > 0,
                    "golden_cross": s.get("return_3m", 0) > 0 and s.get("return_6m", 0) > 0,
                    "above_ma50": s.get("return_1m", 0) > 0,
                    "bb_position": s.get("price_position", 50) / 100,
                    "bb_width": s.get("volatility_30d", 20) / 100,
                    "avg_volume_ratio": 1.0 + (s.get("volume_trend", 0) / 100),
                    "price_trend_slope": s.get("return_3m", 0) / 300,
                }

    # ── Phase 3: Backtesting signals ────────────────────────────────────
    print("Phase 3: Backtesting signals...")
    bt_data = {}
    for sector, sector_stocks in candidates.items():
        for s in sector_stocks:
            bt_data[s["ticker"]] = backtest_signals(s)
    print(f"  Computed backtesting signals for {len(bt_data)} stocks\n")

    # ── Phase 4: ML model ───────────────────────────────────────────────
    print("Phase 4: ML Model (Gradient Boosting)...")

    # Get expected returns from the macro-aware model
    from expected_return_model import ExpectedReturnModel
    er_model = ExpectedReturnModel()
    er_model.refresh_macro()
    print(f"  Macro regime: {er_model.regime.state} "
          f"(market E[R] = {er_model.market.market_expected_return:.2%})")

    er_data = {}
    flat_stocks = [s for slist in candidates.values() for s in slist]
    for s in flat_stocks:
        comp = er_model.stock_expected_return(s)
        er_data[s["ticker"]] = comp.total

    # Build ML dataset
    feature_list = []
    target_list = []
    ticker_list = []
    for s in flat_stocks:
        ticker = s["ticker"]
        ta = ta_data.get(ticker, {})
        bt = bt_data.get(ticker, {})
        features = build_ml_features(s, ta, bt)
        feature_list.append(features)
        # Target: the expected return from the macro model (what we're learning to predict)
        target_list.append(er_data.get(ticker, 0.10))
        ticker_list.append(ticker)

    model, scaler, cv_r2 = train_ml_model(feature_list, target_list)

    # Generate ML predictions
    X_all = pd.DataFrame(feature_list)
    X_scaled = scaler.transform(X_all)
    ml_preds = model.predict(X_scaled)
    ml_predictions = dict(zip(ticker_list, ml_preds))
    print()

    # ── Phase 5: Final selection ────────────────────────────────────────
    selected = select_portfolio(
        candidates, ta_data, bt_data, ml_predictions, er_data,
        stocks_per_sector=args.stocks_per_sector,
    )

    # ── Phase 6: Optimise ───────────────────────────────────────────────
    analysis = optimise_and_analyse(selected)

    # ── Phase 7: Display ────────────────────────────────────────────────
    print_portfolio(analysis)


if __name__ == "__main__":
    main()
