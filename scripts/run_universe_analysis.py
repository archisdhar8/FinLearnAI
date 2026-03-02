#!/usr/bin/env python3
"""
Run Universe Analysis
Pre-populate the cache by running S&P 500 analysis.
Can be run manually or via cron/scheduler.

Usage:
    python scripts/run_universe_analysis.py
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from polygon import RESTClient
from stock_universe_analyzer import StockUniverseAnalyzer, SP500_TICKERS
from sector_normalizer import SectorNormalizer
from stock_scorer import StockScorer
import numpy as np
from datetime import datetime
import json


def main():
    """Run full S&P 500 analysis and cache results."""
    polygon_key = os.environ.get('POLYGON_API_KEY')
    if not polygon_key:
        print("ERROR: POLYGON_API_KEY not found in environment variables.")
        print("Set it in backend/.env file or export it.")
        sys.exit(1)
    
    client = RESTClient(polygon_key)
    analyzer = StockUniverseAnalyzer(client)
    
    print("=" * 60)
    print("S&P 500 Stock Universe Analysis")
    print("=" * 60)
    print(f"Total stocks to analyze: {len(SP500_TICKERS)}")
    print(f"Estimated time: ~20-25 minutes")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    def progress_callback(current, total, ticker):
        progress = int((current / total) * 100)
        print(f"[{progress:3d}%] ({current:3d}/{total}) Analyzing {ticker}...")
    
    try:
        # Run analysis
        print("Step 1/3: Fetching data for all stocks...")
        results = analyzer.analyze_universe(SP500_TICKERS, progress_callback)
        
        print(f"\nStep 2/3: Normalizing metrics by sector...")
        normalized_stocks = SectorNormalizer.normalize_all_metrics(results["stocks"])
        
        print(f"Step 3/3: Calculating composite scores...")
        scored_stocks = StockScorer.score_all_stocks(normalized_stocks)
        
        # Calculate sector stats
        sectors = {}
        for stock in scored_stocks:
            sector = stock["sector"]
            if sector not in sectors:
                sectors[sector] = {
                    "count": 0,
                    "avg_score": 0.0,
                    "top_stocks": []
                }
            sectors[sector]["count"] += 1
            sectors[sector]["avg_score"] += stock["composite_score"]
        
        for sector in sectors:
            sectors[sector]["avg_score"] /= sectors[sector]["count"]
            sector_stocks = [s for s in scored_stocks if s["sector"] == sector]
            sector_stocks.sort(key=lambda x: x["composite_score"], reverse=True)
            sectors[sector]["top_stocks"] = [
                {"ticker": s["ticker"], "score": s["composite_score"]}
                for s in sector_stocks[:5]
            ]
        
        # Overall stats
        scores = [s["composite_score"] for s in scored_stocks]
        stats = {
            "avg_score": float(np.mean(scores)),
            "median_score": float(np.median(scores)),
            "min_score": float(np.min(scores)),
            "max_score": float(np.max(scores)),
            "std_score": float(np.std(scores))
        }
        
        final_results = {
            "stocks": scored_stocks,
            "sectors": sectors,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
            "total_analyzed": len(scored_stocks)
        }
        
        # Save to cache file (same location backend uses)
        cache_dir = Path(__file__).parent.parent / "backend" / "cache"
        cache_dir.mkdir(exist_ok=True)
        cache_file = cache_dir / "sp500_analysis.json"
        
        with open(cache_file, 'w') as f:
            json.dump(final_results, f, indent=2)
        
        print("\n" + "=" * 60)
        print("Analysis Complete!")
        print("=" * 60)
        print(f"Total stocks analyzed: {len(scored_stocks)}")
        print(f"Average score: {stats['avg_score']:.2f}")
        print(f"Top stock: {scored_stocks[0]['ticker']} ({scored_stocks[0]['composite_score']:.2f})")
        print(f"\nResults cached to: {cache_file}")
        print(f"Cache will be valid for 24 hours")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
