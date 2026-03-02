"""
Stock Scorer
Calculates composite scores from normalized metrics.
No CV models - uses fundamentals, valuation, sentiment, momentum, risk.
"""

from typing import Dict, List, Any, Optional
import numpy as np


class StockScorer:
    """
    Composite scoring system with sector-normalized metrics.
    """
    
    # Factor weights
    WEIGHTS = {
        "valuation": 0.30,
        "fundamentals": 0.25,
        "sentiment": 0.20,
        "momentum": 0.15,
        "risk": 0.10
    }
    
    @staticmethod
    def calculate_valuation_score(stock: Dict[str, Any]) -> float:
        """
        Calculate valuation score (30% weight).
        
        Uses:
        - Price position in 52-week range
        - Market cap (if available)
        - P/E, P/B (if available from fundamentals)
        """
        normalized = stock.get("normalized_scores", {})
        
        # Primary: Price position (where stock is in 52w range)
        price_position_score = normalized.get("price_position", 50.0)
        
        # If we have fundamentals, we could add P/E, P/B here
        # For now, use price position as main valuation metric
        
        return price_position_score
    
    @staticmethod
    def calculate_fundamentals_score(stock: Dict[str, Any]) -> float:
        """
        Calculate fundamentals score (25% weight).
        
        Uses:
        - Revenue growth (if available)
        - Profitability (if available)
        - Market cap stability
        """
        # For now, use a combination of available data
        # If we have revenue/net_income, we could calculate growth rates
        
        # Default to neutral if no fundamental data
        base_score = 50.0
        
        # If we have market cap, that's a positive signal (company exists)
        if stock.get("market_cap"):
            base_score = 60.0
        
        # If we have revenue data, that's even better
        if stock.get("revenue"):
            base_score = 70.0
        
        # If we have net income (profitable), that's best
        if stock.get("net_income") and stock.get("net_income", 0) > 0:
            base_score = 80.0
        
        return base_score
    
    @staticmethod
    def calculate_sentiment_score(stock: Dict[str, Any]) -> float:
        """
        Calculate sentiment score (20% weight).
        
        Uses:
        - News sentiment score
        - News count (coverage)
        - Sentiment trend
        """
        normalized = stock.get("normalized_scores", {})
        
        sentiment_score = normalized.get("sentiment_score", 50.0)
        news_count_score = normalized.get("news_count", 50.0)
        
        # Combine: 70% sentiment, 30% news coverage
        combined = (sentiment_score * 0.7) + (news_count_score * 0.3)
        
        return combined
    
    @staticmethod
    def calculate_momentum_score(stock: Dict[str, Any]) -> float:
        """
        Calculate momentum score (15% weight).
        
        Uses:
        - 1M, 3M, 6M returns
        - Volume trend
        """
        normalized = stock.get("normalized_scores", {})
        
        return_1m = normalized.get("return_1m", 50.0)
        return_3m = normalized.get("return_3m", 50.0)
        return_6m = normalized.get("return_6m", 50.0)
        volume_trend = normalized.get("volume_trend", 50.0)
        
        # Weighted average: 3M return is most important
        momentum = (
            return_1m * 0.2 +
            return_3m * 0.5 +
            return_6m * 0.2 +
            volume_trend * 0.1
        )
        
        return momentum
    
    @staticmethod
    def calculate_risk_score(stock: Dict[str, Any]) -> float:
        """
        Calculate risk score (10% weight).
        Lower risk = higher score (inverted).
        
        Uses:
        - Volatility (30d, 90d)
        - Maximum drawdown
        """
        normalized = stock.get("normalized_scores", {})
        
        # These are already normalized with higher_is_better=False
        # So higher normalized score = lower risk = better
        vol_30d = normalized.get("volatility_30d", 50.0)
        vol_90d = normalized.get("volatility_90d", 50.0)
        max_dd = normalized.get("max_drawdown", 50.0)
        
        # Average of risk metrics (all inverted, so higher = lower risk)
        risk_score = (vol_30d * 0.4 + vol_90d * 0.4 + max_dd * 0.2)
        
        return risk_score
    
    @classmethod
    def calculate_composite_score(cls, stock: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate composite score and factor breakdown.
        
        Returns:
            Dictionary with composite_score and factor_scores
        """
        # Calculate each factor score
        factor_scores = {
            "valuation": cls.calculate_valuation_score(stock),
            "fundamentals": cls.calculate_fundamentals_score(stock),
            "sentiment": cls.calculate_sentiment_score(stock),
            "momentum": cls.calculate_momentum_score(stock),
            "risk": cls.calculate_risk_score(stock)
        }
        
        # Weighted composite score
        composite = (
            factor_scores["valuation"] * cls.WEIGHTS["valuation"] +
            factor_scores["fundamentals"] * cls.WEIGHTS["fundamentals"] +
            factor_scores["sentiment"] * cls.WEIGHTS["sentiment"] +
            factor_scores["momentum"] * cls.WEIGHTS["momentum"] +
            factor_scores["risk"] * cls.WEIGHTS["risk"]
        )
        
        return {
            "composite_score": round(composite, 2),
            "factor_scores": {k: round(v, 2) for k, v in factor_scores.items()},
            "weights": cls.WEIGHTS
        }
    
    @staticmethod
    def score_all_stocks(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Score all stocks and add composite scores.
        
        Returns:
            List of stocks with scoring data added, sorted by composite score (desc)
        """
        scored_stocks = []
        
        for stock in stocks:
            scoring_data = StockScorer.calculate_composite_score(stock)
            stock_copy = stock.copy()
            stock_copy.update(scoring_data)
            scored_stocks.append(stock_copy)
        
        # Sort by composite score (highest first)
        scored_stocks.sort(key=lambda x: x["composite_score"], reverse=True)
        
        # Add ranks
        for i, stock in enumerate(scored_stocks):
            stock["overall_rank"] = i + 1
            
            # Calculate sector rank
            sector = stock["sector"]
            sector_stocks = [s for s in scored_stocks if s["sector"] == sector]
            sector_stocks.sort(key=lambda x: x["composite_score"], reverse=True)
            sector_rank = next((i + 1 for i, s in enumerate(sector_stocks) if s["ticker"] == stock["ticker"]), None)
            stock["sector_rank"] = sector_rank
        
        return scored_stocks
