#!/usr/bin/env python3
"""
Personal Stock Analyzer
Standalone script for analyzing stocks and building portfolios.
Run independently of the web app for personal use.

Usage:
    python scripts/personal_stock_analyzer.py --analyze-sp500
    python scripts/personal_stock_analyzer.py --tickers AAPL MSFT GOOGL
    python scripts/personal_stock_analyzer.py --optimize --tickers AAPL MSFT GOOGL --risk moderate
    python scripts/personal_stock_analyzer.py --portfolio my_portfolio.json
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from polygon import RESTClient
from stock_universe_analyzer import StockUniverseAnalyzer, SP500_TICKERS
from sector_normalizer import SectorNormalizer
from stock_scorer import StockScorer
from portfolio_optimizer import PortfolioOptimizer


def analyze_sp500(output_file: Optional[str] = None, verbose: bool = True):
    """Analyze all S&P 500 stocks."""
    polygon_key = os.environ.get('POLYGON_API_KEY')
    if not polygon_key:
        print("ERROR: POLYGON_API_KEY not found in environment variables.")
        print("Set it in .env file or export it.")
        return None
    
    client = RESTClient(polygon_key)
    analyzer = StockUniverseAnalyzer(client)
    
    if verbose:
        print("=" * 60)
        print("Analyzing S&P 500 Stocks")
        print("=" * 60)
        print(f"Total stocks to analyze: {len(SP500_TICKERS)}")
        print("This will take approximately 15-20 minutes...")
        print()
    
    def progress_callback(current, total, ticker):
        if verbose:
            progress = int((current / total) * 100)
            print(f"[{progress:3d}%] Analyzing {ticker}... ({current}/{total})")
    
    # Run analysis
    results = analyzer.analyze_universe(SP500_TICKERS, progress_callback)
    
    if verbose:
        print("\nNormalizing by sector...")
    
    # Normalize by sector
    normalized_stocks = SectorNormalizer.normalize_all_metrics(results["stocks"])
    
    if verbose:
        print("Calculating composite scores...")
    
    # Score all stocks
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
    import numpy as np
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
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(final_results, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    
    return final_results


def analyze_tickers(tickers: List[str], detailed: bool = False):
    """Analyze specific tickers."""
    polygon_key = os.environ.get('POLYGON_API_KEY')
    if not polygon_key:
        print("ERROR: POLYGON_API_KEY not found.")
        return None
    
    client = RESTClient(polygon_key)
    analyzer = StockUniverseAnalyzer(client)
    
    print(f"Analyzing {len(tickers)} stocks: {', '.join(tickers)}")
    print()
    
    results = analyzer.analyze_universe(tickers)
    normalized_stocks = SectorNormalizer.normalize_all_metrics(results["stocks"])
    scored_stocks = StockScorer.score_all_stocks(normalized_stocks)
    
    if detailed:
        for stock in scored_stocks:
            print(f"\n{'='*60}")
            print(f"{stock['ticker']} - {stock['sector']}")
            print(f"{'='*60}")
            print(f"Composite Score: {stock['composite_score']:.2f}/100")
            print(f"Overall Rank: #{stock['overall_rank']}")
            print(f"Sector Rank: #{stock['sector_rank']}")
            print(f"\nFactor Scores:")
            for factor, score in stock['factor_scores'].items():
                print(f"  {factor.capitalize()}: {score:.2f}")
            print(f"\nMetrics:")
            print(f"  Current Price: ${stock.get('current_price', 0):.2f}")
            print(f"  3M Return: {stock.get('return_3m', 0):.2f}%")
            print(f"  Sentiment: {stock.get('sentiment_score', 0):.2f}")
            print(f"  News Count: {stock.get('news_count', 0)}")
    else:
        print("\nResults:")
        print(f"{'Ticker':<8} {'Score':<8} {'Rank':<6} {'Sector':<15} {'3M Return':<10}")
        print("-" * 60)
        for stock in scored_stocks:
            print(f"{stock['ticker']:<8} {stock['composite_score']:>6.1f}   #{stock['overall_rank']:<4} "
                  f"{stock['sector']:<15} {stock.get('return_3m', 0):>8.1f}%")
    
    return scored_stocks


def optimize_portfolio(tickers: List[str], risk_tolerance: str = "moderate", 
                       max_weight: float = 0.25, output_file: Optional[str] = None):
    """Optimize portfolio allocation."""
    polygon_key = os.environ.get('POLYGON_API_KEY')
    if not polygon_key:
        print("ERROR: POLYGON_API_KEY not found.")
        return None
    
    # Load analysis results (or analyze if needed)
    cache_file = Path(__file__).parent.parent / "backend" / "cache" / "sp500_analysis.json"
    
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        stocks_data = cache_data.get("stocks", [])
    else:
        print("No cached analysis found. Running analysis first...")
        results = analyze_sp500(verbose=False)
        if not results:
            return None
        stocks_data = results["stocks"]
    
    # Get selected stocks
    selected_stocks = [s for s in stocks_data if s["ticker"] in [t.upper() for t in tickers]]
    
    if not selected_stocks:
        print(f"ERROR: No data found for tickers: {', '.join(tickers)}")
        return None
    
    print(f"\nOptimizing portfolio for {len(selected_stocks)} stocks...")
    
    # Map risk tolerance to objective
    objective_map = {
        "conservative": "min_risk",
        "moderate": "sharpe",
        "aggressive": "max_return"
    }
    objective = objective_map.get(risk_tolerance.lower(), "sharpe")
    
    # Optimize
    weights = PortfolioOptimizer.optimize_portfolio(
        selected_stocks,
        objective=objective,
        constraints={"max_weight": max_weight}
    )
    
    # Analyze
    analysis = PortfolioOptimizer.analyze_portfolio(selected_stocks, weights)
    
    # Display results
    print("\n" + "=" * 60)
    print("Portfolio Optimization Results")
    print("=" * 60)
    print(f"\nPortfolio Metrics:")
    print(f"  Expected Return: {analysis['expected_return']:.2f}%")
    print(f"  Volatility (Risk): {analysis['volatility']:.2f}%")
    print(f"  Sharpe Ratio: {analysis['sharpe_ratio']:.3f}")
    print(f"  Number of Holdings: {analysis['num_holdings']}")
    print(f"  Concentration Index: {analysis['concentration_index']:.3f}")
    
    print(f"\nSector Allocation:")
    for sector, weight in sorted(analysis['sector_allocation'].items(), 
                                key=lambda x: x[1], reverse=True):
        print(f"  {sector:<20} {weight:>6.2f}%")
    
    print(f"\nTop Holdings:")
    for i, holding in enumerate(analysis['top_holdings'][:10], 1):
        print(f"  {i:2d}. {holding['ticker']:<8} {holding['weight']:>6.2f}%")
    
    print(f"\nFull Allocation:")
    for ticker, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
        if weight > 0.001:
            print(f"  {ticker:<8} {weight*100:>6.2f}%")
    
    # Save if requested
    if output_file:
        portfolio_data = {
            "tickers": list(weights.keys()),
            "weights": {k: v * 100 for k, v in weights.items()},  # Convert to percentage
            "analysis": analysis,
            "optimized_at": datetime.now().isoformat(),
            "risk_tolerance": risk_tolerance
        }
        with open(output_file, 'w') as f:
            json.dump(portfolio_data, f, indent=2)
        print(f"\nPortfolio saved to: {output_file}")
    
    return {"weights": weights, "analysis": analysis}


def load_portfolio(portfolio_file: str):
    """Load and display a saved portfolio."""
    with open(portfolio_file, 'r') as f:
        portfolio = json.load(f)
    
    print("=" * 60)
    print(f"Portfolio: {portfolio_file}")
    print("=" * 60)
    print(f"\nOptimized: {portfolio.get('optimized_at', 'Unknown')}")
    print(f"Risk Tolerance: {portfolio.get('risk_tolerance', 'Unknown')}")
    
    if "analysis" in portfolio:
        analysis = portfolio["analysis"]
        print(f"\nPortfolio Metrics:")
        print(f"  Expected Return: {analysis.get('expected_return', 0):.2f}%")
        print(f"  Volatility: {analysis.get('volatility', 0):.2f}%")
        print(f"  Sharpe Ratio: {analysis.get('sharpe_ratio', 0):.3f}")
    
    if "weights" in portfolio:
        print(f"\nAllocation:")
        for ticker, weight in sorted(portfolio["weights"].items(), 
                                    key=lambda x: x[1], reverse=True):
            print(f"  {ticker:<8} {weight:>6.2f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Personal Stock Analyzer - Analyze stocks and build portfolios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all S&P 500 stocks
  python scripts/personal_stock_analyzer.py --analyze-sp500 --output results.json
  
  # Analyze specific stocks
  python scripts/personal_stock_analyzer.py --tickers AAPL MSFT GOOGL --detailed
  
  # Optimize portfolio
  python scripts/personal_stock_analyzer.py --optimize --tickers AAPL MSFT GOOGL --risk moderate
  
  # Load saved portfolio
  python scripts/personal_stock_analyzer.py --portfolio my_portfolio.json
        """
    )
    
    parser.add_argument("--analyze-sp500", action="store_true",
                       help="Analyze all S&P 500 stocks")
    parser.add_argument("--tickers", nargs="+",
                       help="List of tickers to analyze")
    parser.add_argument("--detailed", action="store_true",
                       help="Show detailed analysis for each stock")
    parser.add_argument("--optimize", action="store_true",
                       help="Optimize portfolio allocation")
    parser.add_argument("--risk", choices=["conservative", "moderate", "aggressive"],
                       default="moderate", help="Risk tolerance for optimization")
    parser.add_argument("--max-weight", type=float, default=0.25,
                       help="Maximum weight per stock (default: 0.25)")
    parser.add_argument("--output", type=str,
                       help="Output file for results")
    parser.add_argument("--portfolio", type=str,
                       help="Load and display a saved portfolio")
    
    args = parser.parse_args()
    
    if args.portfolio:
        load_portfolio(args.portfolio)
    elif args.analyze_sp500:
        analyze_sp500(args.output)
    elif args.optimize:
        if not args.tickers:
            print("ERROR: --tickers required for --optimize")
            sys.exit(1)
        optimize_portfolio(args.tickers, args.risk, args.max_weight, args.output)
    elif args.tickers:
        analyze_tickers(args.tickers, args.detailed)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
