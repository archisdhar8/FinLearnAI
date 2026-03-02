"""
Sector Normalizer
Normalizes stock metrics within sectors for fair comparison.
"""

from typing import Dict, List, Any
from collections import defaultdict
import numpy as np


class SectorNormalizer:
    """
    Normalizes metrics within sectors so stocks are compared to sector peers.
    """
    
    @staticmethod
    def normalize_metric(stocks: List[Dict[str, Any]], metric_name: str, 
                        higher_is_better: bool = True) -> Dict[str, float]:
        """
        Normalize a metric across all stocks, grouped by sector.
        
        Args:
            stocks: List of stock data dictionaries
            metric_name: Name of metric to normalize (e.g., "return_3m")
            higher_is_better: If True, higher values are better. If False, lower is better.
        
        Returns:
            Dictionary mapping ticker -> normalized score (0-100)
        """
        # Group stocks by sector
        sector_stocks = defaultdict(list)
        for stock in stocks:
            sector = stock.get("sector", "Other")
            sector_stocks[sector].append(stock)
        
        normalized_scores = {}
        
        # Normalize within each sector
        for sector, sector_list in sector_stocks.items():
            # Extract metric values
            values = []
            ticker_to_value = {}
            
            for stock in sector_list:
                value = stock.get(metric_name)
                if value is not None and not np.isnan(value):
                    ticker = stock["ticker"]
                    values.append(value)
                    ticker_to_value[ticker] = value
            
            if not values:
                # No valid values for this sector
                for stock in sector_list:
                    normalized_scores[stock["ticker"]] = 50.0  # Neutral score
                continue
            
            # Find min/max for normalization
            min_val = min(values)
            max_val = max(values)
            range_val = max_val - min_val
            
            if range_val == 0:
                # All values are the same
                for stock in sector_list:
                    normalized_scores[stock["ticker"]] = 50.0
            else:
                # Normalize to 0-100
                for ticker, value in ticker_to_value.items():
                    if higher_is_better:
                        normalized = ((value - min_val) / range_val) * 100
                    else:
                        # For metrics where lower is better (e.g., volatility, drawdown)
                        normalized = ((max_val - value) / range_val) * 100
                    
                    normalized_scores[ticker] = max(0, min(100, normalized))
        
        return normalized_scores
    
    @staticmethod
    def normalize_all_metrics(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize all relevant metrics for all stocks.
        
        Returns:
            List of stocks with normalized scores added.
        """
        # Define metrics and whether higher is better
        metrics_config = {
            # Valuation (will be calculated from fundamentals)
            "price_position": True,  # Higher price in 52w range is better
            
            # Momentum
            "return_1m": True,
            "return_3m": True,
            "return_6m": True,
            "volume_trend": True,  # Increasing volume is better
            
            # Risk (lower is better, so higher_is_better=False)
            "volatility_30d": False,
            "volatility_90d": False,
            "max_drawdown": False,  # Less drawdown is better
            
            # Sentiment
            "sentiment_score": True,
            "news_count": True,  # More news coverage can be good
        }
        
        # Normalize each metric
        normalized_metrics = {}
        for metric, higher_is_better in metrics_config.items():
            normalized_metrics[metric] = SectorNormalizer.normalize_metric(
                stocks, metric, higher_is_better
            )
        
        # Add normalized scores to each stock
        result = []
        for stock in stocks:
            stock_copy = stock.copy()
            stock_copy["normalized_scores"] = {
                metric: normalized_metrics[metric].get(stock["ticker"], 50.0)
                for metric in metrics_config.keys()
            }
            result.append(stock_copy)
        
        return result
