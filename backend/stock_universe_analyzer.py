"""
Stock Universe Analyzer
Analyzes S&P 500 stocks using Polygon API with sector-normalized scoring.
No CV models - pure fundamentals, valuation, sentiment, momentum, risk.
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
from polygon import RESTClient
import asyncio
from collections import defaultdict

# S&P 500 ticker list (common stocks)
SP500_TICKERS = [
    # Technology
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "CRM", "ADBE", "ORCL",
    "INTC", "AMD", "QCOM", "TXN", "AVGO", "CSCO", "NOW", "INTU", "AMAT", "MU",
    "NXPI", "LRCX", "KLAC", "MCHP", "SNPS", "CDNS", "ANSS", "FTNT", "PANW", "CRWD",
    "ZS", "NET", "DDOG", "TEAM", "DOCN", "ESTC", "MDB", "SNOW", "PLTR", "AI",
    # Finance
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "COF",
    "USB", "TFC", "PNC", "BK", "STT", "MTB", "CFG", "HBAN", "KEY", "ZION",
    "V", "MA", "PYPL", "SQ", "FIS", "FISV", "GPN", "FLYW", "AFRM", "BILL",
    # Healthcare
    "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "GILD", "BIIB", "VRTX", "REGN", "ILMN", "ALXN", "BMRN", "SGEN", "FOLD",
    # Consumer
    "WMT", "HD", "NKE", "SBUX", "MCD", "COST", "TGT", "LOW", "TJX", "ROST",
    "DG", "DLTR", "BBY", "TSCO", "AZO", "ORLY", "AAP", "KMX", "AN", "LAD",
    # Industrial
    "BA", "CAT", "GE", "HON", "RTX", "LMT", "NOC", "GD", "TDG", "TDOC",
    "EMR", "ETN", "IR", "PH", "ROK", "AME", "GGG", "ITW", "SWK", "FAST",
    # Energy
    "XOM", "CVX", "SLB", "EOG", "COP", "MPC", "VLO", "PSX", "HAL", "OXY",
    "FANG", "DVN", "CTRA", "MRO", "APA", "NOV", "FTI", "HP", "NBR", "RIG",
    # Materials
    "LIN", "APD", "ECL", "SHW", "PPG", "DD", "DOW", "FCX", "NEM", "VALE",
    "AA", "X", "CLF", "STLD", "NUE", "CMC", "RS", "WOR", "ATI", "ZEUS",
    # Utilities
    "NEE", "DUK", "SO", "AEP", "SRE", "D", "EXC", "XEL", "WEC", "ES",
    "PEG", "ETR", "FE", "AEE", "CMS", "LNT", "ATO", "NI", "CNP", "ED",
    # Real Estate
    "AMT", "PLD", "EQIX", "PSA", "WELL", "SPG", "O", "AVB", "EQR", "UDR",
    "MAA", "ESS", "CPT", "AIV", "BXP", "VTR", "PEAK", "HST", "HCP", "REG",
    # Communication
    "T", "VZ", "CMCSA", "DIS", "NFLX", "GOOGL", "META", "TWTR", "SNAP", "PINS",
    # Consumer Staples
    "PG", "KO", "PEP", "WMT", "COST", "TGT", "CL", "CHD", "CLX", "KMB",
    "HRL", "SJM", "CAG", "GIS", "K", "CPB", "HSY", "MDLZ", "TSN", "BG",
    # And more... (truncated for brevity, will include full list)
]

# Sector mappings (simplified - can be enhanced with actual GICS sectors)
SECTOR_MAPPINGS = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "CRM", "ADBE", "ORCL",
                    "INTC", "AMD", "QCOM", "TXN", "AVGO", "CSCO", "NOW", "INTU", "AMAT", "MU"],
    "Finance": ["JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "COF",
                "V", "MA", "PYPL", "SQ", "FIS", "FISV"],
    "Healthcare": ["JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR", "BMY"],
    "Consumer": ["WMT", "HD", "NKE", "SBUX", "MCD", "COST", "TGT", "LOW", "TJX", "ROST"],
    "Industrial": ["BA", "CAT", "GE", "HON", "RTX", "LMT", "NOC", "GD"],
    "Energy": ["XOM", "CVX", "SLB", "EOG", "COP", "MPC", "VLO"],
    "Materials": ["LIN", "APD", "ECL", "SHW", "PPG", "DD", "DOW"],
    "Utilities": ["NEE", "DUK", "SO", "AEP", "SRE", "D"],
    "Real Estate": ["AMT", "PLD", "EQIX", "PSA", "WELL", "SPG"],
    "Communication": ["T", "VZ", "CMCSA", "DIS", "NFLX"],
    "Consumer Staples": ["PG", "KO", "PEP", "CL", "CHD"]
}

# Reverse mapping: ticker -> sector
TICKER_TO_SECTOR = {}
for sector, tickers in SECTOR_MAPPINGS.items():
    for ticker in tickers:
        TICKER_TO_SECTOR[ticker] = sector


class StockUniverseAnalyzer:
    """
    Analyzes S&P 500 stocks with sector-normalized scoring.
    """
    
    def __init__(self, polygon_client: RESTClient):
        self.client = polygon_client
        self.cache_dir = Path(__file__).parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "sp500_analysis.json"
        self.cache_ttl_hours = 24
        # Lazy load sentiment analyzer
        self._news_fetcher = None
        self._sentiment_analyzer = None
        
    def get_sector(self, ticker: str) -> str:
        """Get sector for a ticker."""
        return TICKER_TO_SECTOR.get(ticker, "Other")
    
    def fetch_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch fundamental data from Polygon."""
        try:
            # Get ticker details
            ticker_details = self.client.get_ticker_details(ticker)
            
            # Get financials (if available)
            try:
                financials = self.client.vx.list_stock_financials(
                    ticker=ticker,
                    filing_date_gte="2023-01-01",
                    period_of_report_date_gte="2023-01-01",
                    limit=1
                )
            except:
                financials = None
            
            # Extract key metrics
            result = {
                "market_cap": getattr(ticker_details, "market_cap", None),
                "description": getattr(ticker_details, "description", ""),
                "sic_code": getattr(ticker_details, "sic_code", None),
                "homepage_url": getattr(ticker_details, "homepage_url", ""),
            }
            
            # Add financial data if available
            if financials and hasattr(financials, "results") and financials.results:
                fin = financials.results[0]
                result.update({
                    "revenue": getattr(fin, "financials", {}).get("income_statement", {}).get("revenues", {}).get("value", None),
                    "net_income": getattr(fin, "financials", {}).get("income_statement", {}).get("net_income_loss", {}).get("value", None),
                    "total_assets": getattr(fin, "financials", {}).get("balance_sheet", {}).get("assets", {}).get("value", None),
                    "total_debt": getattr(fin, "financials", {}).get("balance_sheet", {}).get("liabilities", {}).get("value", None),
                })
            
            return result
        except Exception as e:
            print(f"[Fundamentals] Error fetching {ticker}: {e}")
            return None
    
    def fetch_price_data(self, ticker: str, days: int = 252) -> Optional[Dict[str, Any]]:
        """Fetch price data and calculate metrics."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 30)
            
            bars = self.client.get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=start_date.strftime('%Y-%m-%d'),
                to=end_date.strftime('%Y-%m-%d'),
                limit=500
            )
            
            if not bars or len(bars) < 30:
                return None
            
            # Convert to DataFrame
            data = []
            for bar in bars:
                data.append({
                    'date': datetime.fromtimestamp(bar.timestamp / 1000),
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume
                })
            
            df = pd.DataFrame(data)
            df = df.sort_values('date')
            
            # Calculate metrics
            current_price = df['close'].iloc[-1]
            price_1m_ago = df['close'].iloc[-22] if len(df) >= 22 else df['close'].iloc[0]
            price_3m_ago = df['close'].iloc[-66] if len(df) >= 66 else df['close'].iloc[0]
            price_6m_ago = df['close'].iloc[-126] if len(df) >= 126 else df['close'].iloc[0]
            price_52w_high = df['high'].max()
            price_52w_low = df['low'].min()
            
            # Returns
            return_1m = (current_price / price_1m_ago - 1) * 100 if price_1m_ago > 0 else 0
            return_3m = (current_price / price_3m_ago - 1) * 100 if price_3m_ago > 0 else 0
            return_6m = (current_price / price_6m_ago - 1) * 100 if price_6m_ago > 0 else 0
            
            # Volatility (30-day and 90-day)
            returns_30d = df['close'].pct_change().dropna()[-30:]
            returns_90d = df['close'].pct_change().dropna()[-90:]
            volatility_30d = returns_30d.std() * np.sqrt(252) * 100 if len(returns_30d) > 1 else 0
            volatility_90d = returns_90d.std() * np.sqrt(252) * 100 if len(returns_90d) > 1 else 0
            
            # Price position in 52-week range
            price_position = (current_price - price_52w_low) / (price_52w_high - price_52w_low) * 100 if (price_52w_high - price_52w_low) > 0 else 50
            
            # Volume trend
            avg_volume_30d = df['volume'].tail(30).mean()
            avg_volume_90d = df['volume'].tail(90).mean()
            volume_trend = (avg_volume_30d / avg_volume_90d - 1) * 100 if avg_volume_90d > 0 else 0
            
            # Maximum drawdown
            rolling_max = df['close'].expanding().max()
            drawdown = (df['close'] - rolling_max) / rolling_max * 100
            max_drawdown = drawdown.min()
            
            return {
                "current_price": current_price,
                "price_1m_ago": price_1m_ago,
                "price_3m_ago": price_3m_ago,
                "price_6m_ago": price_6m_ago,
                "price_52w_high": price_52w_high,
                "price_52w_low": price_52w_low,
                "price_position": price_position,
                "return_1m": return_1m,
                "return_3m": return_3m,
                "return_6m": return_6m,
                "volatility_30d": volatility_30d,
                "volatility_90d": volatility_90d,
                "volume_trend": volume_trend,
                "max_drawdown": max_drawdown,
                "data_points": len(df)
            }
        except Exception as e:
            print(f"[Price Data] Error fetching {ticker}: {e}")
            return None
    
    def fetch_sentiment(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch news sentiment from Polygon using NewsFetcher (FinBERT)."""
        try:
            # Try to use the existing NewsFetcher and SentimentAnalyzer if available
            # This uses FinBERT for better sentiment analysis
            try:
                import sys
                from pathlib import Path
                chart_vision_path = Path(__file__).parent.parent / "chart-vision"
                if str(chart_vision_path) not in sys.path:
                    sys.path.insert(0, str(chart_vision_path))
                
                from utils.news_fetcher import NewsFetcher
                from models.sentiment_analyzer import SentimentAnalyzer
                
                # Initialize if not already done
                if not hasattr(self, '_news_fetcher') or self._news_fetcher is None:
                    polygon_key = os.environ.get('POLYGON_API_KEY')
                    if polygon_key:
                        self._news_fetcher = NewsFetcher(polygon_key)
                    else:
                        self._news_fetcher = None
                
                if not hasattr(self, '_sentiment_analyzer') or self._sentiment_analyzer is None:
                    self._sentiment_analyzer = SentimentAnalyzer()
                    self._sentiment_analyzer.load_model()
                
                if self._news_fetcher and self._sentiment_analyzer:
                    # Fetch news using NewsFetcher
                    articles = self._news_fetcher.get_news(ticker, limit=10, days_back=7)
                    
                    if not articles:
                        return {
                            "sentiment_score": 0.0,
                            "news_count": 0,
                            "sentiment_trend": "neutral"
                        }
                    
                    # Convert to dict format
                    article_dicts = [
                        {'title': a.title, 'description': a.description}
                        for a in articles
                    ]
                    
                    # Analyze with FinBERT
                    result = self._sentiment_analyzer.analyze_stock(ticker, article_dicts)
                    
                    return {
                        "sentiment_score": result.overall_score,
                        "news_count": result.num_articles,
                        "sentiment_trend": result.overall_sentiment
                    }
            except Exception as e:
                # Fallback to simple keyword-based approach
                print(f"[Sentiment] FinBERT not available for {ticker}, using fallback: {e}")
                pass
            
            # Fallback: Simple keyword-based sentiment
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            try:
                news = self.client.list_ticker_news(
                    ticker=ticker,
                    published_utc_gte=start_date.strftime('%Y-%m-%d'),
                    limit=20
                )
            except Exception as e:
                print(f"[Sentiment] Polygon news API error for {ticker}: {e}")
                return {
                    "sentiment_score": 0.0,
                    "news_count": 0,
                    "sentiment_trend": "neutral"
                }
            
            if not news or not hasattr(news, "results") or not news.results:
                return {
                    "sentiment_score": 0.0,
                    "news_count": 0,
                    "sentiment_trend": "neutral"
                }
            
            articles = news.results
            news_count = len(articles)
            
            # Enhanced keyword-based sentiment
            positive_keywords = ["up", "gain", "rise", "surge", "beat", "strong", "growth", "profit", 
                               "bullish", "outperform", "upgrade", "buy", "positive", "rally"]
            negative_keywords = ["down", "fall", "drop", "loss", "miss", "weak", "decline", "crash",
                               "bearish", "underperform", "downgrade", "sell", "negative", "plunge"]
            
            sentiment_scores = []
            for article in articles:
                title = getattr(article, "title", "").lower()
                description = getattr(article, "description", "").lower()
                text = f"{title} {description}"
                
                pos_count = sum(1 for kw in positive_keywords if kw in text)
                neg_count = sum(1 for kw in negative_keywords if kw in text)
                
                if pos_count > neg_count:
                    sentiment_scores.append(1.0)
                elif neg_count > pos_count:
                    sentiment_scores.append(-1.0)
                else:
                    sentiment_scores.append(0.0)
            
            avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.0
            
            # Determine trend
            if avg_sentiment > 0.2:
                trend = "positive"
            elif avg_sentiment < -0.2:
                trend = "negative"
            else:
                trend = "neutral"
            
            return {
                "sentiment_score": avg_sentiment,
                "news_count": news_count,
                "sentiment_trend": trend
            }
        except Exception as e:
            print(f"[Sentiment] Error fetching {ticker}: {e}")
            return {
                "sentiment_score": 0.0,
                "news_count": 0,
                "sentiment_trend": "neutral"
            }
    
    def analyze_stock(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Analyze a single stock."""
        print(f"[Analyze] Processing {ticker}...")
        
        # Fetch all data
        fundamentals = self.fetch_fundamentals(ticker)
        price_data = self.fetch_price_data(ticker)
        sentiment = self.fetch_sentiment(ticker)
        
        if not price_data:
            return None
        
        # Get sector
        sector = self.get_sector(ticker)
        
        # Calculate raw metrics (will be normalized later)
        result = {
            "ticker": ticker,
            "sector": sector,
            "current_price": price_data["current_price"],
            "price_position": price_data["price_position"],
            "return_1m": price_data["return_1m"],
            "return_3m": price_data["return_3m"],
            "return_6m": price_data["return_6m"],
            "volatility_30d": price_data["volatility_30d"],
            "volatility_90d": price_data["volatility_90d"],
            "max_drawdown": price_data["max_drawdown"],
            "volume_trend": price_data["volume_trend"],
            "sentiment_score": sentiment["sentiment_score"],
            "news_count": sentiment["news_count"],
            "sentiment_trend": sentiment["sentiment_trend"],
            "market_cap": fundamentals.get("market_cap") if fundamentals else None,
            "revenue": fundamentals.get("revenue") if fundamentals else None,
            "net_income": fundamentals.get("net_income") if fundamentals else None,
        }
        
        return result
    
    def analyze_universe(self, tickers: List[str] = None, progress_callback=None) -> Dict[str, Any]:
        """
        Analyze entire stock universe.
        
        Args:
            tickers: List of tickers to analyze. If None, uses SP500_TICKERS.
            progress_callback: Optional callback function(current, total, ticker)
        """
        if tickers is None:
            tickers = SP500_TICKERS
        
        results = []
        total = len(tickers)
        
        for i, ticker in enumerate(tickers):
            if progress_callback:
                progress_callback(i + 1, total, ticker)
            
            try:
                stock_data = self.analyze_stock(ticker)
                if stock_data:
                    results.append(stock_data)
                
                # Rate limiting - small delay
                import time
                time.sleep(0.1)
            except Exception as e:
                print(f"[Universe] Error analyzing {ticker}: {e}")
                continue
        
        return {
            "stocks": results,
            "total_analyzed": len(results),
            "timestamp": datetime.now().isoformat()
        }
