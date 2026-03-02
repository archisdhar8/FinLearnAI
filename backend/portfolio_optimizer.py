"""
Portfolio Optimizer
Forward-looking portfolio optimization using factor-based expected returns
and Modern Portfolio Theory.

Key principles:
- Expected returns are derived from fundamental quality scores (forward-looking),
  NOT from past price performance (backward-looking)
- All selected stocks receive a minimum allocation
- Optimization maximizes risk-adjusted returns (Sharpe ratio)
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# Market assumptions
RISK_FREE_RATE = 0.045      # ~4.5% current T-bill rate
EQUITY_RISK_PREMIUM = 0.055  # ~5.5% long-term equity risk premium
MARKET_RETURN = RISK_FREE_RATE + EQUITY_RISK_PREMIUM  # ~10%


class PortfolioOptimizer:
    """
    Portfolio optimization using factor-based expected returns and MPT.
    """

    @staticmethod
    def _stock_expected_return(stock: Dict[str, Any]) -> float:
        """
        Calculate forward-looking expected return for a single stock.
        
        Uses a factor-based model:
        - Base = risk-free rate + equity risk premium
        - Valuation alpha: undervalued stocks (high valuation score) get higher expected returns
        - Quality alpha: strong fundamentals get a premium
        - Sentiment tilt: positive sentiment gives a small forward boost
        - Momentum tilt: small tilt for recent trend continuation
        - Risk discount: higher-risk stocks need higher return to compensate
        
        A stock with average scores (50/100) gets approximately the market return (~10%).
        Score 80 → ~15-16%. Score 20 → ~5-6%.
        """
        scores = stock.get("factor_scores", {})
        valuation = scores.get("valuation", 50.0)       # 0-100, higher = more undervalued
        fundamentals = scores.get("fundamentals", 50.0)  # 0-100, higher = better quality
        sentiment = scores.get("sentiment", 50.0)        # 0-100, higher = better sentiment
        momentum = scores.get("momentum", 50.0)          # 0-100, higher = stronger trend
        risk = scores.get("risk", 50.0)                  # 0-100, higher = LOWER risk

        # Normalize scores to [-1, 1] range (50 is neutral)
        val_z = (valuation - 50) / 50
        fund_z = (fundamentals - 50) / 50
        sent_z = (sentiment - 50) / 50
        mom_z = (momentum - 50) / 50
        risk_z = (risk - 50) / 50  # positive = lower risk

        # Factor premiums (annual, in decimal)
        # Undervalued stocks should outperform (value premium)
        valuation_premium = val_z * 0.04       # ±4% max from valuation
        # High-quality fundamentals earn a premium
        quality_premium = fund_z * 0.025       # ±2.5% max from quality
        # Positive sentiment suggests near-term outperformance
        sentiment_premium = sent_z * 0.015     # ±1.5% max from sentiment
        # Momentum: trend continuation (small factor, mean-reverts)
        momentum_premium = mom_z * 0.01        # ±1% max from momentum
        # Risk premium: riskier stocks (low risk score) should have higher expected returns
        risk_premium = -risk_z * 0.02          # ±2% (higher risk → higher expected return)

        expected = (MARKET_RETURN 
                    + valuation_premium 
                    + quality_premium 
                    + sentiment_premium 
                    + momentum_premium 
                    + risk_premium)

        # Floor and cap at reasonable bounds
        expected = max(0.02, min(0.25, expected))  # 2% to 25% annualized

        return expected

    @staticmethod
    def calculate_expected_returns(stocks: List[Dict[str, Any]],
                                   weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate weighted portfolio expected return."""
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
    def _get_stock_expected_returns_vector(stocks: List[Dict[str, Any]]) -> np.ndarray:
        """Get expected returns as a numpy array (for optimization)."""
        return np.array([PortfolioOptimizer._stock_expected_return(s) for s in stocks])

    @staticmethod
    def calculate_portfolio_volatility(stocks: List[Dict[str, Any]],
                                       weights: Optional[Dict[str, float]] = None,
                                       correlation_matrix: Optional[np.ndarray] = None) -> float:
        """
        Calculate portfolio volatility (annualized).
        volatility_90d in the data is ALREADY annualized (std * sqrt(252) * 100).
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
            # Assume moderate intra-sector correlation (0.5) and cross-sector (0.3)
            # Simplified: uniform 0.4 correlation
            rho = 0.4
            correlation_matrix = np.full((n, n), rho)
            np.fill_diagonal(correlation_matrix, 1.0)

            # Boost correlation for same-sector pairs
            sectors = [s.get("sector", "Other") for s in stocks]
            for i in range(n):
                for j in range(i + 1, n):
                    if sectors[i] == sectors[j]:
                        correlation_matrix[i, j] = 0.6
                        correlation_matrix[j, i] = 0.6

        cov = np.outer(vols, vols) * correlation_matrix
        port_var = w @ cov @ w
        return float(np.sqrt(max(port_var, 0.0)))

    @staticmethod
    def calculate_sharpe_ratio(stocks: List[Dict[str, Any]],
                                weights: Optional[Dict[str, float]] = None) -> float:
        """Sharpe ratio = (expected return - risk free) / volatility."""
        er = PortfolioOptimizer.calculate_expected_returns(stocks, weights)
        vol = PortfolioOptimizer.calculate_portfolio_volatility(stocks, weights)
        if vol == 0:
            return 0.0
        return (er - RISK_FREE_RATE) / vol

    @staticmethod
    def optimize_portfolio(stocks: List[Dict[str, Any]],
                           objective: str = "sharpe",
                           constraints: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Optimize portfolio weights.

        ALL selected stocks receive at least a minimum weight.
        The optimizer overweights the best risk-adjusted stocks.

        Args:
            stocks: List of stock data
            objective: "sharpe", "min_risk", or "max_return"
            constraints: Dict with max_weight, min_weight

        Returns:
            Dictionary of ticker -> optimized weight
        """
        if not stocks:
            return {}

        n = len(stocks)
        tickers = [s["ticker"] for s in stocks]
        equal_weight = 1.0 / n

        if constraints is None:
            constraints = {}

        # Ensure every selected stock gets at least some weight
        # Default min: half of equal weight (so all stocks participate)
        default_min = max(0.01, equal_weight * 0.3)
        min_w = constraints.get("min_weight", default_min)
        # Ensure min_weight * n <= 1.0
        if min_w * n > 1.0:
            min_w = 1.0 / n

        max_w = constraints.get("max_weight", min(0.25, 1.0))
        # Ensure max_weight * n >= 1.0 (feasible)
        if max_w * n < 1.0:
            max_w = 1.0 / n

        x0 = np.ones(n) / n
        bounds = [(min_w, max_w)] * n

        # Weights must sum to 1
        eq_constraint = {"type": "eq", "fun": lambda x: np.sum(x) - 1.0}

        # Pre-compute expected returns vector for efficiency
        er_vec = PortfolioOptimizer._get_stock_expected_returns_vector(stocks)

        # Build covariance matrix once
        vols = np.array([s.get("volatility_90d", 20.0) / 100.0 for s in stocks])
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

        def port_return(w):
            return float(w @ er_vec)

        def port_vol(w):
            return float(np.sqrt(max(w @ cov @ w, 1e-10)))

        def neg_sharpe(w):
            return -(port_return(w) - RISK_FREE_RATE) / port_vol(w)

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
                obj_func, x0,
                method="SLSQP",
                bounds=bounds,
                constraints=[eq_constraint],
                options={"maxiter": 2000, "ftol": 1e-10}
            )

            if result.success:
                weights = {tickers[i]: float(result.x[i]) for i in range(n)}
                # Normalize
                total = sum(weights.values())
                if total > 0:
                    weights = {k: v / total for k, v in weights.items()}
                return weights
            else:
                print(f"[Optimizer] Did not converge: {result.message}. Using equal weights.")
                return {t: equal_weight for t in tickers}
        except Exception as e:
            print(f"[Optimizer] Error: {e}. Using equal weights.")
            return {t: equal_weight for t in tickers}

    @staticmethod
    def analyze_portfolio(stocks: List[Dict[str, Any]],
                          weights: Dict[str, float]) -> Dict[str, Any]:
        """
        Comprehensive portfolio analysis.
        """
        expected_return = PortfolioOptimizer.calculate_expected_returns(stocks, weights)
        volatility = PortfolioOptimizer.calculate_portfolio_volatility(stocks, weights)
        sharpe = PortfolioOptimizer.calculate_sharpe_ratio(stocks, weights)

        # Sector allocation
        sector_alloc = {}
        for stock in stocks:
            t = stock["ticker"]
            w = weights.get(t, 0.0)
            sec = stock.get("sector", "Other")
            sector_alloc[sec] = sector_alloc.get(sec, 0.0) + w

        num_holdings = sum(1 for w in weights.values() if w > 0.001)
        herfindahl = sum(w ** 2 for w in weights.values())

        # Show ALL holdings sorted by weight
        sorted_w = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        all_holdings = [
            {"ticker": t, "weight": round(w * 100, 2)}
            for t, w in sorted_w if w > 0.001
        ]

        # Per-stock expected returns for transparency
        stock_details = []
        for stock in stocks:
            t = stock["ticker"]
            w = weights.get(t, 0.0)
            er = PortfolioOptimizer._stock_expected_return(stock)
            stock_details.append({
                "ticker": t,
                "weight": round(w * 100, 2),
                "expected_return": round(er * 100, 2),
                "volatility": round(stock.get("volatility_90d", 0), 1),
                "composite_score": round(stock.get("composite_score", 0), 1),
                "sector": stock.get("sector", "Other")
            })
        stock_details.sort(key=lambda x: x["weight"], reverse=True)

        return {
            "expected_return": round(expected_return * 100, 2),
            "volatility": round(volatility * 100, 2),
            "sharpe_ratio": round(sharpe, 3),
            "num_holdings": num_holdings,
            "concentration_index": round(herfindahl, 4),
            "sector_allocation": {k: round(v * 100, 2) for k, v in sector_alloc.items()},
            "top_holdings": all_holdings,
            "stock_details": stock_details,
            "weights": {k: round(v * 100, 2) for k, v in weights.items()},
            "methodology": "Factor-based expected returns using valuation, quality, sentiment, momentum, and risk scores. Not based on past price performance."
        }
