"""
Portfolio Optimizer — forward-looking optimisation using macro-aware expected
returns and Modern Portfolio Theory.

Key principles:
  - Expected returns are derived from a multi-component model grounded in
    Gordon Growth decomposition, FRED macro-regime detection, and valuation
    mean reversion — **not** from past price performance.
  - Macro data (yield curve, inflation, unemployment) from FRED drives
    regime classification and sector-level return adjustments.
  - All selected stocks receive a minimum allocation.
  - Optimisation maximises risk-adjusted returns (Sharpe ratio) by default,
    with support for min-risk and max-return objectives.
"""

from typing import Dict, List, Any, Optional
import numpy as np
from scipy.optimize import minimize
import logging
import warnings

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy-loaded expected return model singleton
# ---------------------------------------------------------------------------

_return_model = None


def _get_return_model():
    """Lazy-load the ExpectedReturnModel (and its FRED macro state)."""
    global _return_model
    if _return_model is None:
        from expected_return_model import ExpectedReturnModel
        _return_model = ExpectedReturnModel()
        # refresh_macro() is called lazily on first use inside the model
    return _return_model


# ---------------------------------------------------------------------------
# PortfolioOptimizer
# ---------------------------------------------------------------------------

class PortfolioOptimizer:
    """
    Portfolio optimisation using macro-aware expected returns and MPT.

    The expected return model:
      1. Fetches macro indicators from FRED (yield curve, inflation,
         unemployment, NFCI, credit spreads).
      2. Classifies macro regime (Expansion / LateCycle / Recession / Recovery).
      3. Computes market expected return (risk-free + regime-adjusted ERP).
      4. Decomposes each stock's E[R] into: market baseline, cash yield,
         growth, valuation reversion, macro sector tilt, beta risk
         compensation, and factor alpha overlay.
      5. Clamps to configurable bounds (default −5 % to +30 %).

    The SLSQP optimiser then finds weights that maximise the Sharpe ratio
    (or minimise risk / maximise return) subject to min/max weight bounds.
    """

    # == Macro management ====================================================

    @staticmethod
    def refresh_macro_data(force: bool = False):
        """
        Refresh macro data used for expected returns.

        Call on server startup or periodically (daily / weekly).
        """
        model = _get_return_model()
        model.refresh_macro(force=force)
        logger.info("Macro data refreshed for portfolio optimizer.")

    # == Per-stock expected return ===========================================

    @staticmethod
    def _stock_expected_return(stock: Dict[str, Any]) -> float:
        """
        Forward-looking expected return for a single stock (scalar, decimal).

        Delegates to the macro-aware ``ExpectedReturnModel``.
        """
        model = _get_return_model()
        components = model.stock_expected_return(stock)
        return components.total

    @staticmethod
    def _stock_expected_return_components(stock: Dict[str, Any]) -> dict:
        """Full decomposition dict for a stock (for transparency/debugging)."""
        model = _get_return_model()
        components = model.stock_expected_return(stock)
        return components.to_dict()

    # == Portfolio-level expected return ======================================

    @staticmethod
    def calculate_expected_returns(
        stocks: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Weighted portfolio expected return (decimal)."""
        if not stocks:
            return 0.0
        if weights is None:
            weights = {s["ticker"]: 1.0 / len(stocks) for s in stocks}
        total = 0.0
        for stock in stocks:
            w = weights.get(stock["ticker"], 0.0)
            total += w * PortfolioOptimizer._stock_expected_return(stock)
        return total

    @staticmethod
    def _get_stock_expected_returns_vector(
        stocks: List[Dict[str, Any]],
    ) -> np.ndarray:
        """Expected returns as a numpy array (for optimisation internals)."""
        return np.array(
            [PortfolioOptimizer._stock_expected_return(s) for s in stocks]
        )

    # == Volatility ==========================================================

    @staticmethod
    def calculate_portfolio_volatility(
        stocks: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None,
        correlation_matrix: Optional[np.ndarray] = None,
    ) -> float:
        """
        Annualised portfolio volatility.

        ``volatility_90d`` in the data is **already** annualised
        (std × √252 × 100).  Correlation model: 0.6 same-sector, 0.4 cross.
        """
        if not stocks:
            return 0.0
        if weights is None:
            weights = {s["ticker"]: 1.0 / len(stocks) for s in stocks}

        tickers = [s["ticker"] for s in stocks]
        vols = np.array([s.get("volatility_90d", 20.0) / 100.0 for s in stocks])
        w = np.array([weights.get(t, 0.0) for t in tickers])

        if correlation_matrix is None:
            n = len(stocks)
            rho = 0.4
            correlation_matrix = np.full((n, n), rho)
            np.fill_diagonal(correlation_matrix, 1.0)
            sectors = [s.get("sector", "Other") for s in stocks]
            for i in range(n):
                for j in range(i + 1, n):
                    if sectors[i] == sectors[j]:
                        correlation_matrix[i, j] = 0.6
                        correlation_matrix[j, i] = 0.6

        cov = np.outer(vols, vols) * correlation_matrix
        port_var = w @ cov @ w
        return float(np.sqrt(max(port_var, 0.0)))

    # == Sharpe ==============================================================

    @staticmethod
    def calculate_sharpe_ratio(
        stocks: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Sharpe ratio using the macro-derived risk-free rate."""
        model = _get_return_model()
        model._ensure_initialized()
        risk_free = (
            model._market.risk_free_rate if model._market else 0.045
        )

        er = PortfolioOptimizer.calculate_expected_returns(stocks, weights)
        vol = PortfolioOptimizer.calculate_portfolio_volatility(stocks, weights)
        if vol == 0:
            return 0.0
        return (er - risk_free) / vol

    # == Optimisation ========================================================

    @staticmethod
    def optimize_portfolio(
        stocks: List[Dict[str, Any]],
        objective: str = "sharpe",
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Optimise portfolio weights using SciPy SLSQP.

        **All** selected stocks receive at least a minimum weight so the
        optimiser cannot zero-out any of the user's picks.

        Parameters
        ----------
        stocks : list of dict
        objective : ``"sharpe"`` | ``"min_risk"`` | ``"max_return"``
        constraints : dict, optional
            Keys: ``min_weight``, ``max_weight`` (decimals).

        Returns
        -------
        dict  { ticker → weight (decimal, sums to 1) }
        """
        if not stocks:
            return {}

        n = len(stocks)
        tickers = [s["ticker"] for s in stocks]
        equal_weight = 1.0 / n

        if constraints is None:
            constraints = {}

        default_min = max(0.01, equal_weight * 0.3)
        min_w = constraints.get("min_weight", default_min)
        if min_w * n > 1.0:
            min_w = 1.0 / n

        max_w = constraints.get("max_weight", min(0.25, 1.0))
        if max_w * n < 1.0:
            max_w = 1.0 / n

        x0 = np.ones(n) / n
        bounds = [(min_w, max_w)] * n
        eq_constraint = {"type": "eq", "fun": lambda x: np.sum(x) - 1.0}

        er_vec = PortfolioOptimizer._get_stock_expected_returns_vector(stocks)

        # Build covariance matrix
        vols = np.array(
            [s.get("volatility_90d", 20.0) / 100.0 for s in stocks]
        )
        sectors = [s.get("sector", "Other") for s in stocks]
        rho = 0.4
        corr = np.full((n, n), rho)
        np.fill_diagonal(corr, 1.0)
        for i in range(n):
            for j in range(i + 1, n):
                if sectors[i] == sectors[j]:
                    corr[i, j] = 0.6
                    corr[j, i] = 0.6
        cov = np.outer(vols, vols) * corr

        # Risk-free rate from macro model
        model = _get_return_model()
        model._ensure_initialized()
        risk_free = (
            model._market.risk_free_rate if model._market else 0.045
        )

        def port_return(w):
            return float(w @ er_vec)

        def port_vol(w):
            return float(np.sqrt(max(w @ cov @ w, 1e-10)))

        def neg_sharpe(w):
            return -(port_return(w) - risk_free) / port_vol(w)

        if objective == "sharpe":
            obj_func = neg_sharpe
        elif objective == "min_risk":
            obj_func = port_vol
        elif objective == "max_return":
            obj_func = lambda w: -port_return(w)
        else:
            raise ValueError(f"Unknown objective: {objective}")

        try:
            result = minimize(
                obj_func,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=[eq_constraint],
                options={"maxiter": 2000, "ftol": 1e-10},
            )

            if result.success:
                weights = {tickers[i]: float(result.x[i]) for i in range(n)}
                total = sum(weights.values())
                if total > 0:
                    weights = {k: v / total for k, v in weights.items()}
                return weights
            else:
                logger.warning(
                    "Optimizer did not converge: %s. Using equal weights.",
                    result.message,
                )
                return {t: equal_weight for t in tickers}

        except Exception as exc:
            logger.warning("Optimizer error: %s. Using equal weights.", exc)
            return {t: equal_weight for t in tickers}

    # == Portfolio analysis ===================================================

    @staticmethod
    def analyze_portfolio(
        stocks: List[Dict[str, Any]],
        weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Comprehensive portfolio analysis with expected-return decomposition.

        Returns a dict with:
          - Portfolio metrics (E[R], vol, Sharpe, HHI, etc.)
          - Sector allocation
          - Per-stock expected-return breakdowns (7 components each)
          - Portfolio-level return decomposition
          - Macro regime information
          - Methodology description
        """
        model = _get_return_model()
        model._ensure_initialized()
        risk_free = (
            model._market.risk_free_rate if model._market else 0.045
        )

        expected_return = PortfolioOptimizer.calculate_expected_returns(
            stocks, weights
        )
        volatility = PortfolioOptimizer.calculate_portfolio_volatility(
            stocks, weights
        )
        sharpe = (
            (expected_return - risk_free) / volatility
            if volatility > 0
            else 0.0
        )

        # -- Sector allocation ------------------------------------------------
        sector_alloc: Dict[str, float] = {}
        for stock in stocks:
            t = stock["ticker"]
            w = weights.get(t, 0.0)
            sec = stock.get("sector", "Other")
            sector_alloc[sec] = sector_alloc.get(sec, 0.0) + w

        num_holdings = sum(1 for w in weights.values() if w > 0.001)
        herfindahl = sum(w ** 2 for w in weights.values())

        sorted_w = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        all_holdings = [
            {"ticker": t, "weight": round(w * 100, 2)}
            for t, w in sorted_w
            if w > 0.001
        ]

        # -- Per-stock detail with component breakdown ------------------------
        stock_details = []
        for stock in stocks:
            t = stock["ticker"]
            w = weights.get(t, 0.0)
            comp = PortfolioOptimizer._stock_expected_return_components(stock)

            stock_details.append({
                "ticker": t,
                "weight": round(w * 100, 2),
                "expected_return": round(comp["total"] * 100, 2),
                "return_components": {
                    "market_baseline":      round(comp["market_return"] * 100, 2),
                    "cash_yield":           round(comp["cash_yield_premium"] * 100, 2),
                    "growth":               round(comp["growth_premium"] * 100, 2),
                    "valuation_reversion":  round(comp["multiple_reversion"] * 100, 2),
                    "macro_adjustment":     round(comp["macro_adjustment"] * 100, 2),
                    "risk_premium":         round(comp["risk_adjustment"] * 100, 2),
                    "factor_tilt":          round(comp["factor_tilt"] * 100, 2),
                },
                "volatility": round(stock.get("volatility_90d", 0), 1),
                "composite_score": round(stock.get("composite_score", 0), 1),
                "sector": stock.get("sector", "Other"),
            })
        stock_details.sort(key=lambda x: x["weight"], reverse=True)

        # -- Portfolio-level return decomposition -----------------------------
        port_decomp = model.portfolio_expected_return(stocks, weights)

        # -- Regime info ------------------------------------------------------
        regime_info = (
            model.regime.to_dict() if model.regime else {"state": "Unknown"}
        )

        return {
            "expected_return": round(expected_return * 100, 2),
            "volatility": round(volatility * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "risk_free_rate": round(risk_free * 100, 2),
            "num_holdings": num_holdings,
            "concentration_index": round(herfindahl, 4),
            "sector_allocation": {
                k: round(v * 100, 2) for k, v in sector_alloc.items()
            },
            "top_holdings": all_holdings,
            "stock_details": stock_details,
            "weights": {
                k: round(v * 100, 2) for k, v in weights.items()
            },
            "macro_regime": regime_info,
            "return_decomposition": {
                k: round(v * 100, 2) if isinstance(v, float) else v
                for k, v in port_decomp.get("components", {}).items()
            },
            "methodology": (
                "Macro-aware expected returns using Gordon Growth decomposition "
                "(yield + growth + valuation reversion), FRED-based regime "
                "detection (yield curve, inflation, unemployment), sector-level "
                "macro tilts, and beta risk compensation.  "
                "3-year investment horizon."
            ),
        }
