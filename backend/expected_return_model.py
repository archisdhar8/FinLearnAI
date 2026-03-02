"""
Expected Return Model — forward-looking, macro-aware return decomposition.

Produces a **3-year annualised expected return** for each stock, decomposed
into seven additive components:

  1. Market baseline        risk_free + ERP (regime-adjusted)
  2. Cash yield premium     dividend yield vs S&P 500 average
  3. Growth premium         earnings growth vs S&P 500 average
  4. Multiple reversion     valuation mean reversion over horizon
  5. Macro adjustment       regime × sector × duration sensitivity
  6. Risk adjustment        beta compensation (CAPM intuition)
  7. Factor tilt            optional small alpha overlay from composite score

    total = sum(1..7),  clamped to [clamp_min, clamp_max]

Theoretical grounding:
  Gordon Growth / DDM:
      E[R] ≈ yield + growth + repricing.
      A stock's expected return comes from the cash it distributes, the rate
      at which it grows, and how the market reprices it.

  CAPM / risk compensation:
      β > 1 → stock bears more systematic risk → requires higher return.

  Valuation mean reversion (Shiller, Campbell & Shiller):
      Over 3-5 year horizons, stretched valuations compress and depressed
      valuations expand.  Starting P/E explains ~40 % of subsequent 10-year
      real returns.

  Macro regimes (business cycle):
      Expansion / recession changes earnings risk premia and discount rates.
      Rising rates compress long-duration equities; defensives outperform in
      downturns.

Data constraints (Polygon free tier):
  - No P/E, EPS, revenue, or dividend data available per stock.
  - We use *sector default* fundamentals + *factor scores* as proxies.
  - The model degrades gracefully: missing fields → sector defaults → market
    defaults → warnings (never crashes).
"""

import os
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional

import numpy as np

from macro_data import FredClient, MacroSnapshot
from macro_regime import classify_regime, MacroRegime
from market_return import compute_market_return, MarketReturnEstimate

logger = logging.getLogger(__name__)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  CONFIGURATION                                                          ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@dataclass
class ExpectedReturnConfig:
    """All tunable parameters for the expected return model.

    Default values are chosen to produce reasonable outputs for a
    diversified US large-cap equity portfolio.  See inline comments
    for the rationale behind each default.
    """

    # -- ERP parameters (forwarded to market_return.py) -----------------------
    erp_base: float       = 0.050   # Long-run ERP (Damodaran 2024: ~4.6-5.5 %)
    erp_stress_add: float = 0.020   # Max ERP increase in full risk-off

    # -- Investment horizon ---------------------------------------------------
    horizon_years: int    = 3       # Expected return projection horizon

    # -- Output clamping (annualised decimals) --------------------------------
    clamp_min: float      = -0.05   # −5 % floor
    clamp_max: float      =  0.30   # +30 % ceiling
    # Rationale: individual stock returns beyond this range are implausible
    # for a 3-year horizon and likely reflect data artefacts or extreme
    # extrapolation.

    # -- Valuation mean reversion ---------------------------------------------
    mean_reversion_strength: float = 0.50   # Fraction of gap closed over horizon
    valuation_multiple_range: float = 0.30  # ±30 % implied P/E range from score
    # mean_reversion_strength=0.5 means the P/E goes halfway to its anchor.
    # Academic evidence: mean reversion explains ~20-40 % of subsequent multi-
    # year returns (Campbell & Shiller 1988).

    # -- Growth estimation ----------------------------------------------------
    growth_shrinkage: float = 0.30  # Blending weight on stock-specific adj
    # 70 % sector baseline + 30 % stock-specific.  Higher shrinkage avoids
    # chasing recent momentum as "growth".

    # -- Risk / beta ----------------------------------------------------------
    beta_premium: float = 0.015     # Annual return per unit of excess β
    # Kept conservative (1.5 % per unit) to avoid beta dominating the model.
    # Full CAPM would use the entire ERP (~5 %), but that produces unstable
    # outputs; we dampen it.

    # -- Factor overlay -------------------------------------------------------
    use_factor_overlay: bool  = True
    factor_overlay_max: float = 0.02   # ±2 % max from composite score

    # -- Market-average benchmarks (S&P 500) ----------------------------------
    market_dividend_yield: float = 0.013   # ~1.3 %
    market_avg_growth: float     = 0.065   # ~6.5 % long-term earnings growth
    market_avg_volatility: float = 0.160   # ~16 % annualised vol


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  SECTOR DEFAULT CONSTANTS                                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# Dividend yield defaults (annual, decimal).
# Source: S&P Dow Jones Indices, sector yield approximations 2024-2025.
SECTOR_DIVIDEND_YIELD: Dict[str, float] = {
    "Technology":       0.007,
    "Communication":    0.010,
    "Consumer":         0.008,   # Consumer Discretionary
    "Consumer Staples": 0.025,
    "Energy":           0.030,
    "Finance":          0.020,
    "Healthcare":       0.015,
    "Industrial":       0.015,
    "Materials":        0.018,
    "Real Estate":      0.035,
    "Utilities":        0.032,
    "Other":            0.015,
}

# Long-term earnings growth defaults (annual, decimal).
# Source: FactSet / S&P consensus long-term growth estimates.
SECTOR_EARNINGS_GROWTH: Dict[str, float] = {
    "Technology":       0.120,
    "Communication":    0.080,
    "Consumer":         0.080,
    "Consumer Staples": 0.040,
    "Energy":           0.030,
    "Finance":          0.060,
    "Healthcare":       0.090,
    "Industrial":       0.070,
    "Materials":        0.050,
    "Real Estate":      0.040,
    "Utilities":        0.030,
    "Other":            0.060,
}

# Sector beta defaults.
# Source: Damodaran beta estimates by sector (US, 2024).
SECTOR_BETA: Dict[str, float] = {
    "Technology":       1.15,
    "Communication":    1.05,
    "Consumer":         1.10,
    "Consumer Staples": 0.65,
    "Energy":           1.20,
    "Finance":          1.15,
    "Healthcare":       0.80,
    "Industrial":       1.05,
    "Materials":        1.10,
    "Real Estate":      0.85,
    "Utilities":        0.55,
    "Other":            1.00,
}

# Long-run median trailing P/E anchors by sector.
# Used contextually but not directly exposed to the model since we lack
# per-stock P/E data.  Kept here for documentation / future use.
SECTOR_PE_ANCHOR: Dict[str, float] = {
    "Technology": 28, "Communication": 20, "Consumer": 22,
    "Consumer Staples": 22, "Energy": 14, "Finance": 13,
    "Healthcare": 22, "Industrial": 20, "Materials": 16,
    "Real Estate": 35, "Utilities": 18, "Other": 18,
}


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  MACRO × SECTOR TILT TABLES                                             ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# Annual adjustment (decimal) per sector per regime.
# Positive = tailwind, negative = headwind.

MACRO_SECTOR_TILTS: Dict[str, Dict[str, float]] = {
    "Recession": {
        # Rationale: cyclicals and rate-sensitive equities underperform;
        # defensives (Staples, Utilities, Healthcare) outperform.
        "Technology": -0.030, "Communication": -0.020,
        "Consumer": -0.030, "Consumer Staples": 0.020,
        "Energy": 0.000, "Finance": -0.020,
        "Healthcare": 0.015, "Industrial": -0.015,
        "Materials": -0.010, "Real Estate": -0.020,
        "Utilities": 0.020, "Other": -0.010,
    },
    "LateCycle": {
        # Rationale: rising rates compress long-duration (Tech, RE);
        # Energy and Financials benefit from inflation / higher rates.
        "Technology": -0.020, "Communication": -0.015,
        "Consumer": -0.010, "Consumer Staples": 0.010,
        "Energy": 0.015, "Finance": 0.010,
        "Healthcare": 0.005, "Industrial": 0.000,
        "Materials": 0.005, "Real Estate": -0.015,
        "Utilities": 0.005, "Other": 0.000,
    },
    "Recovery": {
        # Rationale: cyclicals rebound as earnings recover;
        # defensives lag slightly as risk appetite improves.
        "Technology": 0.015, "Communication": 0.010,
        "Consumer": 0.020, "Consumer Staples": -0.005,
        "Energy": 0.010, "Finance": 0.020,
        "Healthcare": 0.005, "Industrial": 0.020,
        "Materials": 0.015, "Real Estate": 0.010,
        "Utilities": -0.010, "Other": 0.010,
    },
    "Expansion": {
        # Rationale: broad-based but small positive tilt to cyclicals.
        "Technology": 0.010, "Communication": 0.005,
        "Consumer": 0.010, "Consumer Staples": 0.000,
        "Energy": 0.005, "Finance": 0.005,
        "Healthcare": 0.005, "Industrial": 0.010,
        "Materials": 0.005, "Real Estate": 0.005,
        "Utilities": 0.000, "Other": 0.005,
    },
}

# Duration sensitivity by regime.
# In rising-rate / stress regimes, high-duration stocks (high P/E / low risk
# score) face additional headwinds.  Positive → tailwind for high-duration.
DURATION_REGIME_EFFECT: Dict[str, float] = {
    "Recession":  -0.015,   # Flight to quality penalises high-duration
    "LateCycle":  -0.020,   # Rising rates compress long-duration
    "Recovery":    0.010,   # Rates stabilise; growth-at-reasonable-price
    "Expansion":   0.005,   # Slight benefit from low rates + growth
}


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  OUTPUT DATACLASS                                                       ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@dataclass
class ExpectedReturnComponents:
    """
    Full decomposition of a stock's expected return.

    All values are **annualised decimals** (0.05 = 5 %).
    """
    market_return: float           # Component 1: risk_free + ERP
    cash_yield_premium: float      # Component 2: div yield − mkt avg
    growth_premium: float          # Component 3: growth − mkt avg
    multiple_reversion: float      # Component 4: valuation repricing
    macro_adjustment: float        # Component 5: regime × sector × duration
    risk_adjustment: float         # Component 6: β compensation
    factor_tilt: float             # Component 7: optional α overlay
    total: float                   # Sum, clamped to [clamp_min, clamp_max]

    # Metadata
    ticker: str = ""
    sector: str = ""
    regime: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, float):
                d[k] = round(v, 6)
        return d


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  EXPECTED RETURN MODEL                                                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class ExpectedReturnModel:
    """
    Forward-looking expected return engine.

    Combines FRED-based macro regime detection, market return estimation,
    and stock-level fundamental decomposition.

    Usage::

        model = ExpectedReturnModel()
        model.refresh_macro()                   # Fetch FRED + compute regime

        components = model.stock_expected_return(stock_dict)
        print(f"Expected return: {components.total:.2%}")
        print(f"  Market:     {components.market_return:.2%}")
        print(f"  Yield:      {components.cash_yield_premium:.2%}")
        print(f"  Growth:     {components.growth_premium:.2%}")
        print(f"  Reversion:  {components.multiple_reversion:.2%}")
        print(f"  Macro:      {components.macro_adjustment:.2%}")
        print(f"  Risk:       {components.risk_adjustment:.2%}")
        print(f"  Factor:     {components.factor_tilt:.2%}")

    The model caches macro state and reuses it across stocks.
    Call ``refresh_macro()`` to update (e.g. daily / weekly).
    """

    def __init__(
        self,
        config: Optional[ExpectedReturnConfig] = None,
        fred_api_key: Optional[str] = None,
    ):
        self.config = config or ExpectedReturnConfig()

        api_key = fred_api_key or os.environ.get("FRED_API_KEY", "")
        self.fred_client = FredClient(api_key=api_key)

        # Cached macro state (populated by refresh_macro)
        self._snapshot: Optional[MacroSnapshot] = None
        self._regime:   Optional[MacroRegime]   = None
        self._market:   Optional[MarketReturnEstimate] = None
        self._initialized = False

    # -- Macro management ----------------------------------------------------

    def refresh_macro(self, force: bool = False):
        """
        Fetch latest macro data from FRED and compute regime + market return.

        Call on startup and periodically (daily / weekly).  Results are cached
        both in-memory and on disk (``backend/cache/fred_cache.json``).
        """
        self._snapshot = self.fred_client.get_snapshot(force_refresh=force)
        self._regime   = classify_regime(self._snapshot)
        self._market   = compute_market_return(
            self._snapshot,
            self._regime,
            erp_base=self.config.erp_base,
            erp_stress_add=self.config.erp_stress_add,
        )
        self._initialized = True

        logger.info(
            "Macro refreshed: regime=%s, market_return=%.3f, source=%s",
            self._regime.state,
            self._market.market_expected_return,
            self._snapshot.data_source,
        )

    def _ensure_initialized(self):
        """Lazy-initialise if ``refresh_macro()`` hasn't been called."""
        if not self._initialized:
            logger.info("Auto-initialising macro data (first call) …")
            self.refresh_macro()

    # -- Properties (read-only) ----------------------------------------------

    @property
    def regime(self) -> Optional[MacroRegime]:
        self._ensure_initialized()
        return self._regime

    @property
    def market(self) -> Optional[MarketReturnEstimate]:
        self._ensure_initialized()
        return self._market

    @property
    def snapshot(self) -> Optional[MacroSnapshot]:
        self._ensure_initialized()
        return self._snapshot

    # -- Per-stock expected return -------------------------------------------

    def stock_expected_return(
        self, stock: Dict[str, Any]
    ) -> ExpectedReturnComponents:
        """
        Compute the forward-looking 3-year annualised expected return
        for a single stock.

        Parameters
        ----------
        stock : dict
            Must contain at least ``ticker`` and ``sector``.
            Richer results when ``factor_scores``, ``composite_score``,
            and ``volatility_90d`` are available.

        Returns
        -------
        ExpectedReturnComponents
            Full decomposition including ``.total`` (clamped).
        """
        self._ensure_initialized()

        cfg         = self.config
        ticker      = stock.get("ticker", "???")
        sector      = stock.get("sector", "Other")
        scores      = stock.get("factor_scores", {})
        composite   = stock.get("composite_score", 50.0)
        vol_90d     = stock.get("volatility_90d", 20.0) / 100.0   # → decimal

        valuation    = scores.get("valuation",    50.0)
        fundamentals = scores.get("fundamentals", 50.0)
        sentiment    = scores.get("sentiment",    50.0)
        momentum     = scores.get("momentum",     50.0)
        risk_score   = scores.get("risk",         50.0)  # higher = lower risk

        # ═══════════════════════════════════════════════════════════════════
        # Component 1 — MARKET BASELINE
        # ═══════════════════════════════════════════════════════════════════
        market_return = self._market.market_expected_return

        # ═══════════════════════════════════════════════════════════════════
        # Component 2 — CASH YIELD PREMIUM
        #   Gordon Growth: part of total return comes from cash distributions.
        #   Premium = stock's sector yield  −  S&P 500 average yield.
        # ═══════════════════════════════════════════════════════════════════
        sector_yield = SECTOR_DIVIDEND_YIELD.get(sector, 0.015)
        cash_yield_premium = sector_yield - cfg.market_dividend_yield

        # ═══════════════════════════════════════════════════════════════════
        # Component 3 — GROWTH PREMIUM
        #   Sector baseline growth + stock-specific adjustment from scores.
        #   Premium = stock's growth estimate  −  S&P 500 average growth.
        #
        #   Since we lack per-stock EPS / revenue data, we use:
        #     - Sector default growth as anchor
        #     - Momentum score to nudge (higher momentum ≈ growing faster)
        #     - Fundamentals score to nudge (higher quality ≈ sustainable growth)
        #     - Shrinkage keeps it mostly at sector level to avoid noise.
        # ═══════════════════════════════════════════════════════════════════
        base_growth = SECTOR_EARNINGS_GROWTH.get(sector, 0.06)

        mom_z  = (momentum     - 50) / 50   # [−1, 1]
        fund_z = (fundamentals - 50) / 50
        stock_adj = mom_z * 0.03 + fund_z * 0.02   # up to ±5 %

        stock_growth   = base_growth + cfg.growth_shrinkage * stock_adj
        growth_premium = stock_growth - cfg.market_avg_growth

        # ═══════════════════════════════════════════════════════════════════
        # Component 4 — MULTIPLE MEAN REVERSION
        #   We use the valuation factor score as a proxy for relative
        #   cheapness (no actual P/E data available).
        #
        #   High valuation score (100) → stock is near bottom of price range
        #     → "cheap" → expect positive repricing.
        #   Low valuation score (0) → stock is near top of price range
        #     → "expensive" → expect negative repricing.
        #
        #   Mathematics:
        #     val_z = (V − 50) / 50 ∈ [−1, 1]   (positive = cheap)
        #     implied_discount = −range × val_z
        #       V=100 → discount = −0.30  → current PE = 70 % of anchor (cheap)
        #       V=50  → discount =  0.00  → at anchor
        #       V=0   → discount = +0.30  → current PE = 130 % of anchor
        #     target_PE / current_PE → partial reversion over horizon
        #     annual_reversion = (target / current)^(1/H) − 1
        # ═══════════════════════════════════════════════════════════════════
        val_z            = (valuation - 50) / 50
        implied_discount = -cfg.valuation_multiple_range * val_z
        current_pe_ratio = 1.0 + implied_discount          # relative to anchor
        target_pe_ratio  = (
            current_pe_ratio
            + cfg.mean_reversion_strength * (1.0 - current_pe_ratio)
        )

        if current_pe_ratio > 0.01:
            multiple_reversion = (
                (target_pe_ratio / current_pe_ratio)
                ** (1.0 / cfg.horizon_years)
                - 1
            )
        else:
            multiple_reversion = 0.0

        # ═══════════════════════════════════════════════════════════════════
        # Component 5 — MACRO ADJUSTMENT  (regime × sector × duration)
        #
        #   a) Sector tilt: e.g. Technology −3 % in Recession, +1 % in
        #      Expansion.
        #   b) Duration sensitivity: stocks with lower risk_score (higher
        #      implied duration / riskier) face additional regime headwind
        #      or tailwind.
        # ═══════════════════════════════════════════════════════════════════
        regime_state = self._regime.state
        sector_tilt  = MACRO_SECTOR_TILTS.get(regime_state, {}).get(sector, 0.0)

        # Duration proxy: risk_score < 50 → longer duration / riskier
        duration_sensitivity = max(0.0, (50 - risk_score) / 50)  # [0, 1]
        duration_effect      = DURATION_REGIME_EFFECT.get(regime_state, 0.0)
        duration_adj         = duration_sensitivity * duration_effect

        macro_adjustment = sector_tilt + duration_adj

        # ═══════════════════════════════════════════════════════════════════
        # Component 6 — RISK ADJUSTMENT  (β compensation)
        #   CAPM intuition: higher β → higher required return.
        #   β estimated from sector default + vol-implied β (blended).
        # ═══════════════════════════════════════════════════════════════════
        sector_beta     = SECTOR_BETA.get(sector, 1.0)
        vol_implied_beta = (vol_90d / cfg.market_avg_volatility) * 0.75
        stock_beta      = 0.6 * sector_beta + 0.4 * vol_implied_beta

        risk_adjustment = (stock_beta - 1.0) * cfg.beta_premium

        # ═══════════════════════════════════════════════════════════════════
        # Component 7 — FACTOR TILT  (optional alpha overlay)
        #   Small additional tilt from the composite quality score.
        #   This is the residual "alpha" signal from the scoring model;
        #   kept small (±2 %) because the fundamentals + macro components
        #   now carry the heavy lift.
        # ═══════════════════════════════════════════════════════════════════
        if cfg.use_factor_overlay:
            composite_z = (composite - 50) / 50   # [−1, 1]
            factor_tilt = composite_z * cfg.factor_overlay_max
        else:
            factor_tilt = 0.0

        # ═══════════════════════════════════════════════════════════════════
        # TOTAL  —  clamp to [clamp_min, clamp_max]
        # ═══════════════════════════════════════════════════════════════════
        raw_total = (
            market_return
            + cash_yield_premium
            + growth_premium
            + multiple_reversion
            + macro_adjustment
            + risk_adjustment
            + factor_tilt
        )
        total = float(np.clip(raw_total, cfg.clamp_min, cfg.clamp_max))

        if abs(total - raw_total) > 0.001:
            logger.debug("%s: clamped %.4f → %.4f", ticker, raw_total, total)

        return ExpectedReturnComponents(
            market_return=market_return,
            cash_yield_premium=cash_yield_premium,
            growth_premium=growth_premium,
            multiple_reversion=multiple_reversion,
            macro_adjustment=macro_adjustment,
            risk_adjustment=risk_adjustment,
            factor_tilt=factor_tilt,
            total=total,
            ticker=ticker,
            sector=sector,
            regime=regime_state,
        )

    # -- Portfolio-level expected return -------------------------------------

    def portfolio_expected_return(
        self,
        stocks: List[Dict[str, Any]],
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Compute portfolio-level expected return with component breakdown.

        Returns a dict with:
          - ``total``: weighted portfolio expected return (decimal)
          - ``components``: weighted sum of each component
          - ``stock_details``: per-stock decomposition
          - ``regime``, ``market_estimate``, ``macro_source``
        """
        self._ensure_initialized()

        weighted = {
            "market_return": 0.0,
            "cash_yield_premium": 0.0,
            "growth_premium": 0.0,
            "multiple_reversion": 0.0,
            "macro_adjustment": 0.0,
            "risk_adjustment": 0.0,
            "factor_tilt": 0.0,
            "total": 0.0,
        }
        stock_details = []

        for stock in stocks:
            ticker = stock.get("ticker", "???")
            w = weights.get(ticker, 0.0)
            comp = self.stock_expected_return(stock)

            weighted["market_return"]       += w * comp.market_return
            weighted["cash_yield_premium"]  += w * comp.cash_yield_premium
            weighted["growth_premium"]      += w * comp.growth_premium
            weighted["multiple_reversion"]  += w * comp.multiple_reversion
            weighted["macro_adjustment"]    += w * comp.macro_adjustment
            weighted["risk_adjustment"]     += w * comp.risk_adjustment
            weighted["factor_tilt"]         += w * comp.factor_tilt
            weighted["total"]               += w * comp.total

            stock_details.append({
                "ticker": ticker,
                "weight": round(w * 100, 2),
                "expected_return": round(comp.total * 100, 2),
                "components": comp.to_dict(),
            })

        for k in weighted:
            weighted[k] = round(weighted[k], 6)

        return {
            "total": weighted["total"],
            "components": weighted,
            "regime": self._regime.to_dict() if self._regime else None,
            "market_estimate": {
                "risk_free": self._market.risk_free_rate,
                "erp": self._market.total_erp,
                "total": self._market.market_expected_return,
            } if self._market else None,
            "macro_source": (
                self._snapshot.data_source if self._snapshot else "unknown"
            ),
            "stock_details": stock_details,
        }
