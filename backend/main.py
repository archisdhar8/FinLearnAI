"""
FastAPI Backend for FinLearn AI
Connects React frontend to RAG, CV models, and Polygon API
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import base64
import io
import numpy as np

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "quantcademy-app"))
sys.path.insert(0, str(Path(__file__).parent.parent / "chart-vision"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

app = FastAPI(
    title="FinLearn AI API",
    description="Backend API for RAG chat, chart analysis, and stock screening",
    version="1.0.0"
)

# CORS - allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Must be False when allow_origins is "*"
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Forward declarations for prewarming (actual functions defined below)
_cv_loaded = False
_sr_model = None
_trend_model = None

# Sentiment model (lazy loaded)
_sentiment_analyzer = None
_news_fetcher = None

# Stock analysis cache for default watchlists
_stock_cache: Dict[str, Any] = {}
_stock_cache_time: Dict[str, datetime] = {}
_CACHE_TTL_MINUTES = 720  # Cache expires after 12 hours (stock data refreshes on restart)
_SCREENER_CACHE_FILE = Path(__file__).parent / "cache" / "screener_cache.json"

# Default watchlists to preload (must match frontend StockScreener.tsx)
DEFAULT_WATCHLISTS = {
    "Tech Giants": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA"],
    "Finance": ["JPM", "BAC", "GS", "V", "MA", "AXP"],
    "Consumer": ["WMT", "HD", "NKE", "SBUX", "MCD", "COST"],
    "Healthcare": ["JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY"],
    "ETFs": ["SPY", "QQQ", "IWM", "DIA", "XLF", "XLE"],
    "Growth": ["TSLA", "NFLX", "CRM", "ADBE", "SQ", "SHOP"],
}

def _load_screener_cache_from_file():
    """Load stock screener cache from disk for instant startup."""
    global _stock_cache, _stock_cache_time
    if _SCREENER_CACHE_FILE.exists():
        try:
            import json
            with open(_SCREENER_CACHE_FILE, 'r') as f:
                data = json.load(f)
            for ticker, entry in data.items():
                _stock_cache[ticker] = entry["data"]
                _stock_cache_time[ticker] = datetime.fromisoformat(entry["time"])
            print(f"[Cache] Loaded {len(data)} screener stocks from disk cache")
        except Exception as e:
            print(f"[Cache] Failed to load screener cache: {e}")

def _save_screener_cache_to_file():
    """Persist stock screener cache to disk."""
    try:
        import json
        _SCREENER_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for ticker in _stock_cache:
            data[ticker] = {
                "data": _stock_cache[ticker],
                "time": _stock_cache_time.get(ticker, datetime.now()).isoformat()
            }
        with open(_SCREENER_CACHE_FILE, 'w') as f:
            json.dump(data, f)
        print(f"[Cache] Saved {len(data)} screener stocks to disk cache")
    except Exception as e:
        print(f"[Cache] Failed to save screener cache: {e}")

# Load screener cache immediately on import (before server starts)
_load_screener_cache_from_file()

def _prewarm_cv():
    """Helper to prewarm CV models - actual load_cv_models defined below."""
    global _cv_loaded, _sr_model, _trend_model
    # This will be replaced by the actual function below
    pass

# =============================================================================
# Startup Prewarming - Load all models on startup for faster first requests
# =============================================================================

@app.on_event("startup")
async def prewarm_models():
    """Prewarm all models on startup so first requests are fast."""
    global _cv_loaded, _sr_model, _trend_model
    
    print("\n" + "="*60)
    print("PREWARMING MODELS ON STARTUP...")
    print("="*60)
    
    # 1. Prewarm RAG (embedding model + reranker + knowledge base)
    print("\n[Prewarm] Loading RAG components...")
    try:
        from rag.retrieval import get_retriever
        retriever = get_retriever()
        # Do a dummy query to fully initialize
        retriever.retrieve("what is investing", top_k=1)
        print("[Prewarm] RAG ready")
    except Exception as e:
        print(f"[Prewarm] RAG failed: {e}")
    
    # 2. Prewarm CV models (call the actual function defined below)
    print("\n[Prewarm] Loading CV models...")
    try:
        # Import and call the actual load function
        load_cv_models()
        if _sr_model and _trend_model:
            print("[Prewarm] CV models ready")
        else:
            print("[Prewarm] CV models partially loaded")
    except Exception as e:
        print(f"[Prewarm] CV models failed: {e}")
    
    # 3. Check LLM connection
    print("\n[Prewarm] Checking LLM connection...")
    try:
        from rag.llm_provider import check_llm_status
        status = check_llm_status()
        if status.get('status') == 'online':
            print(f"[Prewarm] LLM ready ({status.get('provider')})")
        else:
            print(f"[Prewarm] LLM not available: {status}")
    except Exception as e:
        print(f"[Prewarm] LLM check failed: {e}")
    
    # 4. Prewarm Sentiment Model (FinBERT)
    print("\n[Prewarm] Loading Sentiment model (FinBERT)...")
    try:
        load_sentiment_models()
        if _sentiment_analyzer is not None:
            print("[Prewarm] Sentiment model ready")
    except Exception as e:
        print(f"[Prewarm] Sentiment model failed: {e}")
    
    # 5. Preload default watchlist stock data (background task)
    print("\n[Prewarm] Starting background preload of default stocks...")
    try:
        import asyncio
        asyncio.create_task(preload_default_stocks())
        # Also start periodic refresh (every 6 hours)
        asyncio.create_task(_periodic_stock_refresh())
        print("[Prewarm] Stock preload task started (refreshes every 6h)")
    except Exception as e:
        print(f"[Prewarm] Stock preload failed: {e}")
    
    print("\n" + "="*60)
    print("SERVER READY - All models prewarmed!")
    print("="*60 + "\n")


async def preload_default_stocks():
    """Background task to preload all default watchlist stocks into cache.
    
    This runs in the background and doesn't block the server startup.
    Stocks are loaded gradually with delays to avoid overwhelming APIs.
    """
    global _stock_cache, _stock_cache_time
    
    # Wait a bit before starting to let the server fully initialize
    import asyncio
    await asyncio.sleep(2)
    
    polygon_key = os.environ.get('POLYGON_API_KEY')
    if not polygon_key:
        print("[Preload] No Polygon API key, skipping stock preload")
        return
    
    # Collect all unique tickers from default watchlists
    all_tickers = set()
    for tickers in DEFAULT_WATCHLISTS.values():
        all_tickers.update(tickers)
    
    print(f"[Preload] Loading {len(all_tickers)} stocks from default watchlists...")
    
    try:
        from polygon import RESTClient
        client = RESTClient(polygon_key)
        
        loaded = 0
        enriched = 0
        for ticker in all_tickers:
            try:
                # Check if already cached and fresh
                if ticker in _stock_cache:
                    cache_age = datetime.now() - _stock_cache_time.get(ticker, datetime.min)
                    if cache_age.total_seconds() < _CACHE_TTL_MINUTES * 60:
                        # Backfill sentiment/AI if missing from disk cache
                        cached = _stock_cache[ticker]
                        if cached.get('sentiment') is None or cached.get('ai_analysis') is None:
                            try:
                                sentiment_data = get_stock_sentiment(ticker)
                                cached['sentiment'] = sentiment_data.get('sentiment')
                                cached['sentiment_score'] = sentiment_data.get('sentiment_score')
                                cached['sentiment_signal'] = sentiment_data.get('sentiment_signal')
                                cached['news_count'] = sentiment_data.get('news_count', 0)
                                analysis_info = {
                                    'price': cached.get('price', 0),
                                    'change_pct': cached.get('change_pct', 0),
                                    'trend': cached.get('trend', 'sideways'),
                                    'trend_confidence': cached.get('trend_confidence', 50),
                                    'signal': cached.get('signal', 'HOLD'),
                                    'signal_strength': cached.get('signal_strength', 50),
                                    'support': cached.get('support', 0),
                                    'resistance': cached.get('resistance', 0),
                                    'sentiment': cached['sentiment'] or 'neutral',
                                    'news_count': cached['news_count']
                                }
                                cached['ai_analysis'] = generate_ai_stock_analysis(ticker, analysis_info)
                                _stock_cache[ticker] = cached
                                enriched += 1
                                print(f"[Preload] Enriched {ticker} with sentiment/AI")
                                await asyncio.sleep(0.5)
                            except Exception as e:
                                print(f"[Preload] Failed to enrich {ticker}: {e}")
                        continue
                
                # Get 30+ days of data
                end_date = datetime.now()
                start_date = end_date - timedelta(days=45)
                
                bars = client.get_aggs(
                    ticker=ticker,
                    multiplier=1,
                    timespan="day",
                    from_=start_date.strftime('%Y-%m-%d'),
                    to=end_date.strftime('%Y-%m-%d'),
                    limit=50
                )
                
                if not bars or len(bars) < 10:
                    continue
                
                # Get last 30 days
                bars = bars[-30:] if len(bars) > 30 else bars
                
                latest = bars[-1]
                prev = bars[-2] if len(bars) > 1 else bars[-1]
                
                change = latest.close - prev.close
                change_pct = (change / prev.close) * 100 if prev.close > 0 else 0
                
                # Generate chart image
                chart_image = generate_chart_image_from_data(bars)
                
                # Get price range for S/R calculation
                price_min = min(b.low for b in bars)
                price_max = max(b.high for b in bars)
                
                # Run CV model analysis
                analysis = analyze_chart_with_models(chart_image, (price_min, price_max))
                
                # Draw analysis lines on the chart
                annotated_chart = draw_analysis_on_chart(
                    chart_image, 
                    analysis, 
                    (price_min, price_max),
                    num_bars=len(bars)
                )
                
                # Convert annotated image to base64
                buf = io.BytesIO()
                annotated_chart.save(buf, format='PNG')
                buf.seek(0)
                chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
                
                # Get support/resistance prices
                support_price = analysis['support_zones'][0]['price'] if analysis['support_zones'] else round(price_min, 2)
                resistance_price = analysis['resistance_zones'][0]['price'] if analysis['resistance_zones'] else round(price_max, 2)
                
                # Generate sentiment during preload so users get instant results
                sentiment_data = get_stock_sentiment(ticker)
                
                stock_data = {
                    'ticker': ticker,
                    'price': round(latest.close, 2),
                    'change': round(change, 2),
                    'change_pct': round(change_pct, 2),
                    'trend': analysis['trend'],
                    'trend_confidence': round(analysis['trend_confidence'] * 100, 1),
                    'signal': analysis['signal'],
                    'signal_strength': round(analysis['signal_strength'], 1),
                    'support': support_price,
                    'resistance': resistance_price,
                    'support_zones': analysis['support_zones'],
                    'resistance_zones': analysis['resistance_zones'],
                    'chart_image': chart_base64,
                    'sentiment': sentiment_data.get('sentiment'),
                    'sentiment_score': sentiment_data.get('sentiment_score'),
                    'sentiment_signal': sentiment_data.get('sentiment_signal'),
                    'news_count': sentiment_data.get('news_count', 0),
                    'ai_analysis': None  # Will be filled below
                }
                
                # Generate AI analysis text
                analysis_info = {
                    'price': stock_data['price'],
                    'change_pct': stock_data['change_pct'],
                    'trend': stock_data['trend'],
                    'trend_confidence': stock_data['trend_confidence'],
                    'signal': stock_data['signal'],
                    'signal_strength': stock_data['signal_strength'],
                    'support': stock_data['support'],
                    'resistance': stock_data['resistance'],
                    'sentiment': stock_data['sentiment'] or 'neutral',
                    'news_count': stock_data['news_count']
                }
                stock_data['ai_analysis'] = generate_ai_stock_analysis(ticker, analysis_info)
                
                _stock_cache[ticker] = stock_data
                _stock_cache_time[ticker] = datetime.now()
                loaded += 1
                
                # Small delay to avoid rate limiting
                import asyncio
                await asyncio.sleep(0.5)  # Delay between stocks for sentiment + Polygon calls
                
            except Exception as e:
                print(f"[Preload] Error loading {ticker}: {e}")
                continue
        
        print(f"[Preload] Loaded {loaded} new, enriched {enriched} cached — {len(all_tickers)} total stocks")
        # Persist to disk so next restart is instant (now with sentiment included)
        _save_screener_cache_to_file()
        
    except Exception as e:
        print(f"[Preload] Error: {e}")


async def _periodic_stock_refresh():
    """Periodically refresh the stock screener cache every 6 hours."""
    import asyncio
    while True:
        await asyncio.sleep(6 * 3600)  # Wait 6 hours
        print("[Refresh] Refreshing stock screener cache...")
        try:
            # Clear old cache so preload fetches fresh data
            _stock_cache.clear()
            _stock_cache_time.clear()
            await preload_default_stocks()  # This also saves to disk
        except Exception as e:
            print(f"[Refresh] Error: {e}")

# =============================================================================
# Request/Response Models
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    lesson_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []

class StockRequest(BaseModel):
    tickers: List[str]

class ChartAnalysisResponse(BaseModel):
    trend: str
    trend_confidence: float
    trend_probabilities: Dict[str, float]
    support_zones: List[Dict[str, Any]]
    resistance_zones: List[Dict[str, Any]]
    annotated_image: Optional[str] = None  # Base64 encoded PNG with lines drawn

# =============================================================================
# RAG Chat Endpoint
# =============================================================================

# Lazy load RAG components
_rag_loaded = False
_retriever = None
_llm = None

def load_rag():
    global _rag_loaded, _retriever, _llm
    if _rag_loaded:
        return
    
    try:
        from rag.retrieval import retrieve_with_citations
        from rag.llm_provider import chat_with_llm, check_llm_status
        
        # Check LLM status
        status = check_llm_status()
        if status.get('status') != 'online':
            print(f"[RAG] LLM not available: {status}")
        else:
            print(f"[RAG] LLM ready: {status.get('provider')}")
        
        _rag_loaded = True
        print("[RAG] Components loaded successfully")
    except Exception as e:
        print(f"[RAG] Failed to load: {e}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """RAG-powered chat endpoint."""
    load_rag()
    
    try:
        from rag.retrieval import retrieve_with_citations, format_context_with_citations
        from rag.llm_provider import chat_with_llm
        
        # Retrieve relevant context - returns RetrievalResponse object
        # Use lower confidence threshold (0.15) to allow basic questions
        retrieval_response = retrieve_with_citations(
            query=request.message,
            top_k=5,
            min_confidence=0.15,  # Lower threshold for basic questions
            current_lesson_id=request.lesson_id
        )
        
        # Build context from retrieved chunks
        context_parts = []
        sources = []
        
        # Access results from the RetrievalResponse object
        for i, result in enumerate(retrieval_response.results[:5]):
            # result is a RetrievalResult object with a .chunk attribute
            chunk = result.chunk
            # Don't include source labels in context - just the content
            context_parts.append(chunk.content[:1000])
            sources.append({
                'title': chunk.source,
                'snippet': chunk.content[:200],
                'score': result.final_score
            })
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Only refuse if we have NO results at all
        if not retrieval_response.results or len(retrieval_response.results) == 0:
            return ChatResponse(
                response="I don't have information about that topic in my knowledge base. Try asking about investing basics, stocks, bonds, ETFs, or portfolio management.",
                sources=[]
            )
        
        # Generate response with LLM
        prompt = f"""You are a helpful investing tutor for beginners. Answer the user's question based on the provided context.
Be conversational, clear, and educational. Use the context to inform your answer.

CRITICAL RULES:
- Do NOT include any source references like [Source 1], [Source 2], etc.
- Do NOT write "Sources:" or list any sources at the end
- Do NOT mention citations or references
- Just provide a clean, helpful response

Context:
{context}

User Question: {request.message}

Provide a helpful answer:"""
        
        response = chat_with_llm(prompt, stream=False)
        
        # If still a generator, consume it
        if hasattr(response, '__iter__') and not isinstance(response, str):
            response = ''.join(response)
        
        # Clean up response - remove any source references the LLM might have added
        import re
        # Remove patterns like "Sources:", "Source:", "[Source 1]", etc.
        response = re.sub(r'\n*Sources?:.*$', '', response, flags=re.IGNORECASE | re.DOTALL)
        response = re.sub(r'\[Source \d+\]', '', response)
        response = re.sub(r'\(Source \d+\)', '', response)
        response = re.sub(r'Source \d+:', '', response)
        response = response.strip()
        
        return ChatResponse(
            response=response,
            sources=sources
        )
        
    except Exception as e:
        print(f"[Chat Error] {e}")
        import traceback
        traceback.print_exc()
        # Fallback response
        return ChatResponse(
            response=f"I'm having trouble connecting to my knowledge base right now. Your question was about: {request.message}. Please try again in a moment.",
            sources=[]
        )

# =============================================================================
# Sentiment Analysis - FinBERT
# =============================================================================

def load_sentiment_models():
    """Load FinBERT sentiment model and news fetcher."""
    global _sentiment_analyzer, _news_fetcher
    
    if _sentiment_analyzer is not None:
        return
    
    try:
        # Import from chart-vision
        from models.sentiment_analyzer import SentimentAnalyzer
        from utils.news_fetcher import NewsFetcher
        
        _sentiment_analyzer = SentimentAnalyzer()
        _sentiment_analyzer.load_model()  # Preload the model
        
        polygon_key = os.environ.get('POLYGON_API_KEY')
        if polygon_key:
            _news_fetcher = NewsFetcher(polygon_key)
            print("[Sentiment] News fetcher initialized")
        else:
            print("[Sentiment] No Polygon API key - news fetching disabled")
        
    except Exception as e:
        print(f"[Sentiment] Failed to load: {e}")
        import traceback
        traceback.print_exc()


def get_stock_sentiment(ticker: str) -> Dict[str, Any]:
    """Get sentiment analysis for a stock from recent news."""
    global _sentiment_analyzer, _news_fetcher
    
    if _sentiment_analyzer is None or _news_fetcher is None:
        load_sentiment_models()
    
    if _sentiment_analyzer is None or _news_fetcher is None:
        return {
            'sentiment': None,
            'sentiment_score': None,
            'sentiment_signal': None,
            'news_count': 0
        }
    
    try:
        # Fetch recent news (last 7 days, up to 10 articles)
        articles = _news_fetcher.get_news(ticker, limit=10, days_back=7)
        
        if not articles:
            return {
                'sentiment': 'neutral',
                'sentiment_score': 0.0,
                'sentiment_signal': 'NEUTRAL',
                'news_count': 0
            }
        
        # Convert to dict format for analyzer
        article_dicts = [
            {'title': a.title, 'description': a.description}
            for a in articles
        ]
        
        # Analyze sentiment
        result = _sentiment_analyzer.analyze_stock(ticker, article_dicts)
        signal, strength = _sentiment_analyzer.get_sentiment_signal(result)
        
        return {
            'sentiment': result.overall_sentiment,
            'sentiment_score': result.overall_score,
            'sentiment_signal': signal,
            'news_count': result.num_articles
        }
        
    except Exception as e:
        print(f"[Sentiment] Error analyzing {ticker}: {e}")
        return {
            'sentiment': None,
            'sentiment_score': None,
            'sentiment_signal': None,
            'news_count': 0
        }


# =============================================================================
# Chart Analysis Endpoint
# =============================================================================

# CV model variables are declared at the top of the file (forward declarations)

def load_cv_models():
    global _cv_loaded, _sr_model, _trend_model
    if _cv_loaded:
        return
    
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        from torchvision import models
        
        # Define model architectures locally (EXACTLY matching training scripts)
        class SRZoneModel(nn.Module):
            """S/R Zone Detection Model - matches train_sr_model_v2.py exactly"""
            def __init__(self, num_zones=10):
                super().__init__()
                self.num_zones = num_zones
                
                # Use ResNet34 for better capacity
                backbone = models.resnet34(weights=None)
                
                # Remove final FC layer
                self.features = nn.Sequential(*list(backbone.children())[:-1])
                
                # Custom head for zone classification
                self.head = nn.Sequential(
                    nn.Flatten(),
                    nn.Linear(512, 256),
                    nn.BatchNorm1d(256),
                    nn.ReLU(),
                    nn.Dropout(0.4),
                    nn.Linear(256, 128),
                    nn.BatchNorm1d(128),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(128, num_zones * 2),  # Support + Resistance zones
                )
            
            def forward(self, x):
                features = self.features(x)
                return self.head(features)
        
        class TrendModelV2(nn.Module):
            """Trend Classification Model - matches train_trend_model_v2.py exactly"""
            def __init__(self, num_classes=3):
                super().__init__()
                
                # EfficientNet-B2 backbone
                try:
                    self.backbone = models.efficientnet_b2(weights=None)
                    in_features = self.backbone.classifier[1].in_features
                except:
                    self.backbone = models.resnet50(weights=None)
                    in_features = self.backbone.fc.in_features
                    self.backbone.fc = nn.Identity()
                
                # Classification head
                self.classifier = nn.Sequential(
                    nn.Dropout(0.3),
                    nn.Linear(in_features, 512),
                    nn.BatchNorm1d(512),
                    nn.SiLU(),
                    nn.Dropout(0.4),
                    nn.Linear(512, 256),
                    nn.BatchNorm1d(256),
                    nn.SiLU(),
                    nn.Dropout(0.3),
                    nn.Linear(256, num_classes)
                )
                
                # Slope regression head (for drawing line)
                self.slope_head = nn.Sequential(
                    nn.Linear(in_features, 128),
                    nn.ReLU(),
                    nn.Linear(128, 2),  # start_y, end_y (normalized 0-1)
                    nn.Sigmoid()
                )
                
                if hasattr(self.backbone, 'classifier'):
                    self.backbone.classifier = nn.Identity()
                elif hasattr(self.backbone, 'fc'):
                    self.backbone.fc = nn.Identity()
            
            def forward(self, x):
                features = self.backbone(x)
                if len(features.shape) > 2:
                    features = F.adaptive_avg_pool2d(features, 1).flatten(1)
                
                class_logits = self.classifier(features)
                slope = self.slope_head(features)
                return class_logits, slope
        
        device = torch.device('cpu')
        checkpoint_dir = Path(__file__).parent.parent / "chart-vision" / "checkpoints"
        
        print(f"[CV] Looking for models in: {checkpoint_dir}")
        
        # Load S/R model
        sr_path = checkpoint_dir / "sr_zone_model_best.pt"
        if sr_path.exists():
            _sr_model = SRZoneModel(num_zones=10)
            checkpoint = torch.load(sr_path, map_location=device, weights_only=False)
            _sr_model.load_state_dict(checkpoint['model_state_dict'])
            _sr_model.eval()
            print("[CV] S/R model loaded successfully")
        else:
            print(f"[CV] S/R model not found at {sr_path}")
        
        # Load Trend model
        trend_path = checkpoint_dir / "trend_model_v2_best.pt"
        if trend_path.exists():
            _trend_model = TrendModelV2()
            checkpoint = torch.load(trend_path, map_location=device, weights_only=False)
            _trend_model.load_state_dict(checkpoint['model_state_dict'])
            _trend_model.eval()
            print("[CV] Trend model loaded successfully")
        else:
            print(f"[CV] Trend model not found at {trend_path}")
        
        _cv_loaded = True
        
    except Exception as e:
        print(f"[CV] Failed to load models: {e}")
        import traceback
        traceback.print_exc()

@app.post("/api/analyze-chart", response_model=ChartAnalysisResponse)
async def analyze_chart(file: UploadFile = File(...)):
    """Analyze uploaded chart image with CV models."""
    load_cv_models()
    
    try:
        import torch
        import torchvision.transforms as transforms
        from PIL import Image
        import numpy as np
        
        # Read and preprocess image
        contents = await file.read()
        original_image = Image.open(io.BytesIO(contents)).convert('RGB')
        
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        img_tensor = transform(original_image).unsqueeze(0)
        
        result = {
            'trend': 'sideways',
            'trend_confidence': 0.5,
            'trend_probabilities': {'uptrend': 0.33, 'downtrend': 0.33, 'sideways': 0.34},
            'support_zones': [],
            'resistance_zones': [],
            'signal': 'HOLD'
        }
        
        # Trend prediction
        if _trend_model is not None:
            with torch.no_grad():
                class_logits, slope = _trend_model(img_tensor)
                probs = torch.softmax(class_logits, dim=1)[0].cpu().numpy()
                
                classes = ['downtrend', 'sideways', 'uptrend']
                pred_idx = np.argmax(probs)
                
                result['trend'] = classes[pred_idx]
                result['trend_confidence'] = float(probs[pred_idx])
                result['trend_probabilities'] = {
                    cls: float(probs[i]) for i, cls in enumerate(classes)
                }
        
        # S/R prediction - use normalized price range (0-100) for uploaded images
        if _sr_model is not None:
            with torch.no_grad():
                logits = _sr_model(img_tensor)
                probs = torch.sigmoid(logits)[0].cpu().numpy()
                
                num_zones = len(probs) // 2
                support_probs = probs[:num_zones]
                resistance_probs = probs[num_zones:]
                
                # Use percentage-based zones for uploaded images
                for i, prob in enumerate(support_probs):
                    if prob > 0.4:
                        # Convert zone to approximate price level (0-100 scale)
                        zone_price = (i + 0.5) / num_zones * 100
                        result['support_zones'].append({
                            'zone': i + 1,
                            'price': round(zone_price, 1),
                            'confidence': int(prob * 100)  # Convert to percentage
                        })
                
                for i, prob in enumerate(resistance_probs):
                    if prob > 0.4:
                        zone_price = (i + 0.5) / num_zones * 100
                        result['resistance_zones'].append({
                            'zone': i + 1,
                            'price': round(zone_price, 1),
                            'confidence': int(prob * 100)  # Convert to percentage
                        })
        
        # Calculate signal
        if result['trend'] == 'uptrend' and result['trend_confidence'] > 0.6:
            result['signal'] = 'BUY'
        elif result['trend'] == 'downtrend' and result['trend_confidence'] > 0.6:
            result['signal'] = 'SELL'
        else:
            result['signal'] = 'HOLD'
        
        # Draw analysis on the original image (no price labels for uploaded images)
        annotated_image = draw_analysis_on_chart(
            original_image,
            result,
            (0, 100),  # Normalized price range for uploaded images
            num_bars=30,
            show_prices=False  # Don't show price numbers for uploaded images
        )
        
        # Convert annotated image to base64
        buf = io.BytesIO()
        annotated_image.save(buf, format='PNG')
        buf.seek(0)
        result['annotated_image'] = base64.b64encode(buf.read()).decode('utf-8')
        
        return ChartAnalysisResponse(**result)
        
    except Exception as e:
        print(f"[Chart Analysis Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# XAI (Explainable AI) Endpoint - Grad-CAM Visualization
# =============================================================================

class XAIResponse(BaseModel):
    sr_heatmap: Optional[str] = None  # Base64 encoded heatmap image
    trend_heatmap: Optional[str] = None
    explanation: str = ""

@app.post("/api/xai", response_model=XAIResponse)
async def generate_xai(file: UploadFile = File(...)):
    """Generate Grad-CAM heatmap showing what the model focuses on."""
    load_cv_models()
    
    try:
        import torch
        import torch.nn.functional as F
        import torchvision.transforms as transforms
        from PIL import Image as PILImage
        import numpy as np
        import cv2
        
        # Read and preprocess image
        contents = await file.read()
        image = PILImage.open(io.BytesIO(contents)).convert('RGB')
        original_array = np.array(image)
        
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        input_tensor = transform(image).unsqueeze(0)
        
        result = XAIResponse(explanation="")
        explanations = []
        
        # Generate Grad-CAM for Trend model
        if _trend_model is not None:
            try:
                _trend_model.eval()
                
                # Get the target layer (last conv layer of backbone)
                if hasattr(_trend_model, 'backbone') and hasattr(_trend_model.backbone, 'features'):
                    target_layer = _trend_model.backbone.features[-1]
                else:
                    target_layer = None
                
                if target_layer:
                    activations = None
                    gradients = None
                    
                    def forward_hook(module, input, output):
                        nonlocal activations
                        activations = output.detach()
                    
                    def backward_hook(module, grad_input, grad_output):
                        nonlocal gradients
                        gradients = grad_output[0].detach()
                    
                    fh = target_layer.register_forward_hook(forward_hook)
                    bh = target_layer.register_full_backward_hook(backward_hook)
                    
                    # Forward pass
                    output, _ = _trend_model(input_tensor)
                    pred_class = output.argmax(dim=1).item()
                    class_names = ['downtrend', 'sideways', 'uptrend']
                    
                    # Backward pass
                    _trend_model.zero_grad()
                    one_hot = torch.zeros_like(output)
                    one_hot[0, pred_class] = 1
                    output.backward(gradient=one_hot)
                    
                    # Generate heatmap
                    weights = gradients.mean(dim=(2, 3), keepdim=True)
                    cam = (weights * activations).sum(dim=1, keepdim=True)
                    cam = F.relu(cam).squeeze().cpu().numpy()
                    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
                    
                    # Resize and colorize
                    heatmap = cv2.resize(cam, (original_array.shape[1], original_array.shape[0]))
                    heatmap_colored = cv2.applyColorMap((heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)
                    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
                    
                    # Overlay
                    overlay = (0.6 * original_array + 0.4 * heatmap_colored).astype(np.uint8)
                    
                    # Convert to base64
                    overlay_img = PILImage.fromarray(overlay)
                    buf = io.BytesIO()
                    overlay_img.save(buf, format='PNG')
                    buf.seek(0)
                    result.trend_heatmap = base64.b64encode(buf.read()).decode('utf-8')
                    
                    explanations.append(f"Trend: Model predicted {class_names[pred_class].upper()}")
                    
                    fh.remove()
                    bh.remove()
                    
            except Exception as e:
                print(f"[XAI Trend Error] {e}")
        
        # Generate Grad-CAM for S/R model
        if _sr_model is not None:
            try:
                _sr_model.eval()
                
                if hasattr(_sr_model, 'backbone') and hasattr(_sr_model.backbone, 'features'):
                    target_layer = _sr_model.backbone.features[-1]
                else:
                    target_layer = None
                
                if target_layer:
                    activations = None
                    gradients = None
                    
                    def forward_hook(module, input, output):
                        nonlocal activations
                        activations = output.detach()
                    
                    def backward_hook(module, grad_input, grad_output):
                        nonlocal gradients
                        gradients = grad_output[0].detach()
                    
                    fh = target_layer.register_forward_hook(forward_hook)
                    bh = target_layer.register_full_backward_hook(backward_hook)
                    
                    # Forward pass
                    output = _sr_model(input_tensor)
                    probs = torch.sigmoid(output)[0]
                    
                    # Find strongest zone
                    max_idx = probs.argmax().item()
                    
                    # Backward pass for that zone
                    _sr_model.zero_grad()
                    output[0, max_idx].backward()
                    
                    # Generate heatmap
                    weights = gradients.mean(dim=(2, 3), keepdim=True)
                    cam = (weights * activations).sum(dim=1, keepdim=True)
                    cam = F.relu(cam).squeeze().cpu().numpy()
                    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
                    
                    # Resize and colorize
                    heatmap = cv2.resize(cam, (original_array.shape[1], original_array.shape[0]))
                    heatmap_colored = cv2.applyColorMap((heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)
                    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
                    
                    # Overlay
                    overlay = (0.6 * original_array + 0.4 * heatmap_colored).astype(np.uint8)
                    
                    # Convert to base64
                    overlay_img = PILImage.fromarray(overlay)
                    buf = io.BytesIO()
                    overlay_img.save(buf, format='PNG')
                    buf.seek(0)
                    result.sr_heatmap = base64.b64encode(buf.read()).decode('utf-8')
                    
                    num_zones = len(probs) // 2
                    zone_type = "Support" if max_idx < num_zones else "Resistance"
                    explanations.append(f"S/R: Model focused on {zone_type} detection")
                    
                    fh.remove()
                    bh.remove()
                    
            except Exception as e:
                print(f"[XAI S/R Error] {e}")
        
        result.explanation = " | ".join(explanations) if explanations else "XAI visualization generated"
        return result
        
    except Exception as e:
        print(f"[XAI Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Stock Screener Endpoint - Real CV Model Analysis
# =============================================================================

def generate_chart_image_from_data(bars, figsize=(8, 4), dpi=120):
    """Generate a clean, minimal candlestick chart image from Polygon bars."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from PIL import Image
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Clean dark background
    fig.patch.set_facecolor('#0f0f1a')
    ax.set_facecolor('#0f0f1a')
    
    # Draw candlesticks - cleaner style
    width = 0.7
    up_color = '#10b981'    # Softer green
    down_color = '#f43f5e'  # Softer red
    
    prices = []
    for i, bar in enumerate(bars):
        o, h, l, c = bar.open, bar.high, bar.low, bar.close
        prices.extend([h, l])
        is_up = c >= o
        color = up_color if is_up else down_color
        
        # Body - slightly rounded look with edge
        body_bottom = min(o, c)
        body_height = abs(c - o) if abs(c - o) > 0.001 else 0.01
        ax.add_patch(Rectangle((i - width/2, body_bottom), width, body_height,
                               facecolor=color, edgecolor=color, linewidth=0.5))
        # Wicks - thinner
        ax.plot([i, i], [l, body_bottom], color=color, linewidth=0.8)
        ax.plot([i, i], [body_bottom + body_height, h], color=color, linewidth=0.8)
    
    # Add subtle grid
    ax.grid(True, axis='y', color='#2a2a4a', linewidth=0.3, alpha=0.5)
    
    # Set axis limits with padding
    price_min, price_max = min(prices), max(prices)
    price_padding = (price_max - price_min) * 0.1
    ax.set_ylim(price_min - price_padding, price_max + price_padding)
    ax.set_xlim(-0.5, len(bars) - 0.5)
    
    # Clean axis styling
    ax.set_xticks([])
    ax.tick_params(axis='y', colors='#6b7280', labelsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:.0f}'))
    
    # Remove spines except left
    for spine in ['top', 'right', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.spines['left'].set_color('#2a2a4a')
    ax.spines['left'].set_linewidth(0.5)
    
    plt.tight_layout()
    
    # Convert to PIL Image
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=dpi, facecolor='#0f0f1a',
                bbox_inches='tight', pad_inches=0.1)
    buf.seek(0)
    plt.close(fig)
    
    return Image.open(buf)


def analyze_chart_with_models(image, price_range):
    """Run CV models on chart image."""
    import torch
    import torchvision.transforms as transforms
    import numpy as np
    
    results = {
        'trend': 'sideways',
        'trend_confidence': 0.5,
        'support_zones': [],
        'resistance_zones': [],
        'signal': 'HOLD',
        'signal_strength': 50
    }
    
    if not _cv_loaded:
        return results
    
    # Preprocess image
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    img_tensor = transform(image.convert('RGB')).unsqueeze(0)
    
    # Trend prediction
    if _trend_model is not None:
        with torch.no_grad():
            class_logits, slope_pred = _trend_model(img_tensor)
            probs = torch.softmax(class_logits, dim=1)[0].cpu().numpy()
            
            classes = ['downtrend', 'sideways', 'uptrend']
            pred_idx = np.argmax(probs)
            
            results['trend'] = classes[pred_idx]
            results['trend_confidence'] = float(probs[pred_idx])
    
    # S/R prediction
    if _sr_model is not None:
        with torch.no_grad():
            logits = _sr_model(img_tensor)
            probs = torch.sigmoid(logits)[0].cpu().numpy()
            
            num_zones = len(probs) // 2
            support_probs = probs[:num_zones]
            resistance_probs = probs[num_zones:]
            
            price_min, price_max = price_range
            price_step = (price_max - price_min) / num_zones
            
            # Collect all zones above threshold, then sort by confidence
            support_candidates = []
            resistance_candidates = []
            
            for i, prob in enumerate(support_probs):
                if prob > 0.4:
                    price = price_min + (i + 0.5) * price_step
                    support_candidates.append({
                        'zone': i + 1,
                        'price': round(price, 2),
                        'confidence': int(prob * 100)
                    })
            
            for i, prob in enumerate(resistance_probs):
                if prob > 0.4:
                    price = price_min + (i + 0.5) * price_step
                    resistance_candidates.append({
                        'zone': i + 1,
                        'price': round(price, 2),
                        'confidence': int(prob * 100)
                    })
            
            # Sort by confidence (highest first) and take top zones
            support_candidates.sort(key=lambda x: x['confidence'], reverse=True)
            resistance_candidates.sort(key=lambda x: x['confidence'], reverse=True)
            
            results['support_zones'] = support_candidates
            results['resistance_zones'] = resistance_candidates
            
            # Debug: print all zone probabilities
            print(f"[S/R Debug] Price range: ${price_min:.2f} - ${price_max:.2f}")
            print(f"[S/R Debug] Support probs: {[f'{p:.2f}' for p in support_probs]}")
            print(f"[S/R Debug] Resistance probs: {[f'{p:.2f}' for p in resistance_probs]}")
    
    # Calculate signal - improved logic for more varied outputs
    signal_score = 0
    
    # Trend contribution (weighted by confidence)
    trend_conf = results['trend_confidence']
    if results['trend'] == 'uptrend':
        signal_score += trend_conf * 60  # Increased weight
    elif results['trend'] == 'downtrend':
        signal_score -= trend_conf * 60  # Increased weight
    else:  # sideways
        # Sideways trend contributes based on S/R balance
        pass
    
    # S/R contribution - weighted by number and confidence of zones
    support_strength = sum(z.get('confidence', 50) for z in results['support_zones'][:2]) / 100 if results['support_zones'] else 0
    resistance_strength = sum(z.get('confidence', 50) for z in results['resistance_zones'][:2]) / 100 if results['resistance_zones'] else 0
    
    # More support than resistance = bullish, vice versa
    sr_balance = (support_strength - resistance_strength) * 20
    signal_score += sr_balance
    
    # Calculate final signal with more granular thresholds
    if signal_score > 15:
        results['signal'] = 'BUY'
        # Scale confidence: 15-60 maps to 55-90%
        results['signal_strength'] = min(55 + (signal_score - 15) * 0.8, 95)
    elif signal_score < -15:
        results['signal'] = 'SELL'
        results['signal_strength'] = min(55 + (abs(signal_score) - 15) * 0.8, 95)
    else:
        results['signal'] = 'HOLD'
        # HOLD confidence varies based on how close to neutral
        # Closer to 0 = more confident HOLD, closer to ±15 = less confident
        hold_confidence = 70 - abs(signal_score) * 1.5
        results['signal_strength'] = max(40, min(hold_confidence, 75))
    
    # Round to integer
    results['signal_strength'] = int(results['signal_strength'])
    
    print(f"[Signal Debug] trend={results['trend']} ({trend_conf:.2f}), score={signal_score:.1f}, signal={results['signal']} ({results['signal_strength']}%)")
    
    return results


def draw_analysis_on_chart(image, analysis, price_range, num_bars=30, show_prices=True):
    """Draw clean, minimal S/R lines and trend indicator on the chart image.
    
    Args:
        image: PIL Image
        analysis: dict with trend, support_zones, resistance_zones
        price_range: (min, max) price tuple
        num_bars: number of bars in chart
        show_prices: whether to show price labels (False for uploaded images without real prices)
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image as PILImage
    import numpy as np
    
    # Convert PIL image to numpy array
    img_array = np.array(image)
    
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.imshow(img_array)
    
    img_height, img_width = img_array.shape[:2]
    price_min, price_max = price_range
    price_range_val = price_max - price_min
    
    # Check if we have real prices (not normalized 0-100 range)
    has_real_prices = show_prices and price_max > 100
    
    def price_to_y(price):
        """Convert price to y-coordinate (inverted because image y=0 is top)"""
        if price_range_val == 0:
            return img_height / 2
        normalized = (price - price_min) / price_range_val
        return img_height * (1 - normalized * 0.8 - 0.1)
    
    # Draw Support lines (green) - pick the LOWEST price zones (bottom of chart)
    support_zones = analysis.get('support_zones', [])
    # Sort by price ascending (lowest first) for support, take top 2
    support_to_draw = sorted(support_zones, key=lambda x: x.get('price', 0))[:2]
    for i, zone in enumerate(support_to_draw):
        y = price_to_y(zone.get('price', 50))
        ax.axhline(y=y, color='#10b981', linestyle='-', linewidth=1.5, alpha=0.8)
        if has_real_prices:
            price_label = zone.get('price', 0)
            ax.text(img_width - 8, y - 3, f'${price_label:.0f}', 
                    color='#10b981', fontsize=7, ha='right', va='bottom', fontweight='bold')
        else:
            ax.text(img_width - 8, y - 3, 'S', 
                    color='#10b981', fontsize=8, ha='right', va='bottom', fontweight='bold')
    
    # Draw Resistance lines (red) - pick the HIGHEST price zones (top of chart)
    resistance_zones = analysis.get('resistance_zones', [])
    # Sort by price descending (highest first) for resistance, take top 2
    resistance_to_draw = sorted(resistance_zones, key=lambda x: x.get('price', 0), reverse=True)[:2]
    for i, zone in enumerate(resistance_to_draw):
        y = price_to_y(zone.get('price', 50))
        ax.axhline(y=y, color='#f43f5e', linestyle='-', linewidth=1.5, alpha=0.8)
        if has_real_prices:
            price_label = zone.get('price', 0)
            ax.text(img_width - 8, y + 10, f'${price_label:.0f}', 
                    color='#f43f5e', fontsize=7, ha='right', va='top', fontweight='bold')
        else:
            ax.text(img_width - 8, y + 10, 'R', 
                    color='#f43f5e', fontsize=8, ha='right', va='top', fontweight='bold')
    
    # Draw subtle trend line
    trend = analysis.get('trend', 'sideways')
    trend_conf = analysis.get('trend_confidence', 0.5)
    
    trend_colors = {'uptrend': '#10b981', 'downtrend': '#f43f5e', 'sideways': '#f59e0b'}
    trend_color = trend_colors.get(trend, '#f59e0b')
    
    # Always draw trend line
    if trend == 'uptrend':
        ax.plot([img_width * 0.1, img_width * 0.9], [img_height * 0.65, img_height * 0.35], 
                color=trend_color, linewidth=2, alpha=0.7, linestyle='--')
    elif trend == 'downtrend':
        ax.plot([img_width * 0.1, img_width * 0.9], [img_height * 0.35, img_height * 0.65], 
                color=trend_color, linewidth=2, alpha=0.7, linestyle='--')
    else:  # sideways - draw horizontal line through middle
        ax.plot([img_width * 0.1, img_width * 0.9], [img_height * 0.5, img_height * 0.5], 
                color=trend_color, linewidth=2, alpha=0.7, linestyle='--')
    
    # Note: Signal badge and trend text removed from chart - now shown in sidebar only
    # This avoids duplicate display of the same information
    
    ax.axis('off')
    plt.tight_layout(pad=0)
    
    # Convert back to PIL Image
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, facecolor='#0f0f1a',
                bbox_inches='tight', pad_inches=0)
    buf.seek(0)
    plt.close(fig)
    
    return PILImage.open(buf)


class StockAnalysisResponse(BaseModel):
    ticker: str
    price: float
    change: float
    change_pct: float
    trend: str
    trend_confidence: float
    signal: str
    signal_strength: float
    support: Optional[float] = None
    resistance: Optional[float] = None
    support_zones: List[Dict[str, Any]] = []
    resistance_zones: List[Dict[str, Any]] = []
    chart_image: str  # Base64 encoded PNG
    # Sentiment fields
    sentiment: Optional[str] = None  # 'positive', 'negative', 'neutral'
    sentiment_score: Optional[float] = None  # -1 to +1
    sentiment_signal: Optional[str] = None  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    news_count: Optional[int] = None
    # AI-generated analysis paragraph
    ai_analysis: Optional[str] = None


def generate_ai_stock_analysis(ticker: str, data: dict) -> str:
    """Generate a short AI analysis paragraph using Gemini."""
    try:
        # Build the prompt with all available data
        prompt = f"""You are a concise financial analyst. Write a 2-3 sentence analysis of {ticker} stock based on this data:

Price: ${data.get('price', 'N/A')} ({data.get('change_pct', 0):+.2f}% today)
30-Day Trend: {data.get('trend', 'unknown')} ({data.get('trend_confidence', 0):.0f}% confidence)
AI Signal: {data.get('signal', 'HOLD')} ({data.get('signal_strength', 50):.0f}% strength)
Support Level: ${data.get('support', 'N/A')}
Resistance Level: ${data.get('resistance', 'N/A')}
News Sentiment: {data.get('sentiment', 'neutral')} ({data.get('news_count', 0)} articles)

Write a brief, actionable summary for an investor. Be specific about the numbers. No disclaimers or hedging language. Start directly with the analysis."""

        # Use the LLM provider
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'quantcademy-app'))
        from rag.llm_provider import chat_with_llm
        
        response = chat_with_llm(prompt, stream=False)
        
        # Clean up response
        if isinstance(response, str):
            return response.strip()
        return str(response).strip()
        
    except Exception as e:
        print(f"[AI Analysis Error] {ticker}: {e}")
        # Fallback to a simple template-based analysis
        trend = data.get('trend', 'sideways')
        signal = data.get('signal', 'HOLD')
        sentiment = data.get('sentiment', 'neutral')
        
        if signal == 'BUY':
            return f"{ticker} shows bullish momentum with a {trend} trend and {sentiment} news sentiment. Support at ${data.get('support', 'N/A')} provides a potential entry point."
        elif signal == 'SELL':
            return f"{ticker} displays bearish signals with a {trend} trend. Resistance at ${data.get('resistance', 'N/A')} may cap upside. News sentiment is {sentiment}."
        else:
            return f"{ticker} is consolidating in a {trend} pattern. Watch support at ${data.get('support', 'N/A')} and resistance at ${data.get('resistance', 'N/A')}. Sentiment is {sentiment}."


@app.post("/api/stocks", response_model=List[StockAnalysisResponse])
async def get_stocks(request: StockRequest):
    """Get stock data with real CV model analysis. Uses cache for default watchlist stocks."""
    global _stock_cache, _stock_cache_time
    
    polygon_key = os.environ.get('POLYGON_API_KEY')
    if not polygon_key:
        raise HTTPException(status_code=500, detail="Polygon API key not configured")
    
    # Load CV models if not already loaded
    load_cv_models()
    
    try:
        from polygon import RESTClient
        import numpy as np
        
        client = RESTClient(polygon_key)
        results = []
        
        for ticker in request.tickers:
            try:
                # Check cache first for default watchlist stocks
                if ticker in _stock_cache:
                    cache_age = datetime.now() - _stock_cache_time.get(ticker, datetime.min)
                    if cache_age.total_seconds() < _CACHE_TTL_MINUTES * 60:
                        # Use cached data
                        cached = dict(_stock_cache[ticker])  # Make a copy
                        
                        # Generate sentiment and AI analysis on-demand if missing
                        if cached.get('sentiment') is None or cached.get('ai_analysis') is None:
                            print(f"[Cache Hit] {ticker} - generating sentiment/AI analysis")
                            sentiment_data = get_stock_sentiment(ticker)
                            cached['sentiment'] = sentiment_data.get('sentiment')
                            cached['sentiment_score'] = sentiment_data.get('sentiment_score')
                            cached['sentiment_signal'] = sentiment_data.get('sentiment_signal')
                            cached['news_count'] = sentiment_data.get('news_count', 0)
                            
                            # Generate AI analysis
                            analysis_data = {
                                'price': cached['price'],
                                'change_pct': cached['change_pct'],
                                'trend': cached['trend'],
                                'trend_confidence': cached['trend_confidence'],
                                'signal': cached['signal'],
                                'signal_strength': cached['signal_strength'],
                                'support': cached['support'],
                                'resistance': cached['resistance'],
                                'sentiment': cached['sentiment'] or 'neutral',
                                'news_count': cached['news_count']
                            }
                            cached['ai_analysis'] = generate_ai_stock_analysis(ticker, analysis_data)
                            
                            # Update cache with enriched data
                            _stock_cache[ticker] = cached
                        else:
                            print(f"[Cache Hit] {ticker}")
                        
                        results.append(StockAnalysisResponse(**cached))
                        continue
                
                print(f"[Cache Miss] {ticker} - fetching fresh data")
                
                # Get 30+ days of data
                end_date = datetime.now()
                start_date = end_date - timedelta(days=45)
                
                bars = client.get_aggs(
                    ticker=ticker,
                    multiplier=1,
                    timespan="day",
                    from_=start_date.strftime('%Y-%m-%d'),
                    to=end_date.strftime('%Y-%m-%d'),
                    limit=50
                )
                
                if not bars or len(bars) < 10:
                    continue
                
                # Get last 30 days
                bars = bars[-30:] if len(bars) > 30 else bars
                
                latest = bars[-1]
                prev = bars[-2] if len(bars) > 1 else bars[-1]
                
                change = latest.close - prev.close
                change_pct = (change / prev.close) * 100 if prev.close > 0 else 0
                
                # Generate chart image
                chart_image = generate_chart_image_from_data(bars)
                
                # Get price range for S/R calculation
                price_min = min(b.low for b in bars)
                price_max = max(b.high for b in bars)
                
                # Run CV model analysis
                analysis = analyze_chart_with_models(chart_image, (price_min, price_max))
                
                # Draw analysis lines on the chart
                annotated_chart = draw_analysis_on_chart(
                    chart_image, 
                    analysis, 
                    (price_min, price_max),
                    num_bars=len(bars)
                )
                
                # Convert annotated image to base64
                buf = io.BytesIO()
                annotated_chart.save(buf, format='PNG')
                buf.seek(0)
                chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
                
                # Get support/resistance prices
                support_price = analysis['support_zones'][0]['price'] if analysis['support_zones'] else round(price_min, 2)
                resistance_price = analysis['resistance_zones'][0]['price'] if analysis['resistance_zones'] else round(price_max, 2)
                
                # Get sentiment analysis
                sentiment_data = get_stock_sentiment(ticker)
                
                # Prepare data for AI analysis
                analysis_data = {
                    'price': round(latest.close, 2),
                    'change_pct': round(change_pct, 2),
                    'trend': analysis['trend'],
                    'trend_confidence': round(analysis['trend_confidence'] * 100, 1),
                    'signal': analysis['signal'],
                    'signal_strength': round(analysis['signal_strength'], 1),
                    'support': support_price,
                    'resistance': resistance_price,
                    'sentiment': sentiment_data.get('sentiment', 'neutral'),
                    'news_count': sentiment_data.get('news_count', 0)
                }
                
                # Generate AI analysis paragraph
                ai_analysis = generate_ai_stock_analysis(ticker, analysis_data)
                
                # Build response data
                stock_data = {
                    'ticker': ticker,
                    'price': round(latest.close, 2),
                    'change': round(change, 2),
                    'change_pct': round(change_pct, 2),
                    'trend': analysis['trend'],
                    'trend_confidence': round(analysis['trend_confidence'] * 100, 1),
                    'signal': analysis['signal'],
                    'signal_strength': round(analysis['signal_strength'], 1),
                    'support': support_price,
                    'resistance': resistance_price,
                    'support_zones': analysis['support_zones'],
                    'resistance_zones': analysis['resistance_zones'],
                    'chart_image': chart_base64,
                    'sentiment': sentiment_data.get('sentiment'),
                    'sentiment_score': sentiment_data.get('sentiment_score'),
                    'sentiment_signal': sentiment_data.get('sentiment_signal'),
                    'news_count': sentiment_data.get('news_count', 0),
                    'ai_analysis': ai_analysis
                }
                
                # Update cache for this ticker
                _stock_cache[ticker] = stock_data
                _stock_cache_time[ticker] = datetime.now()
                
                results.append(StockAnalysisResponse(**stock_data))
                
            except Exception as e:
                print(f"[Stock Error] {ticker}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        return results
        
    except Exception as e:
        print(f"[Stocks Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Sentiment Analysis Endpoint (Standalone AI Tool)
# =============================================================================

class SentimentRequest(BaseModel):
    ticker: str
    
class ArticleSentiment(BaseModel):
    title: str
    sentiment: str
    confidence: float
    scores: Dict[str, float]
    
class SentimentResponse(BaseModel):
    ticker: str
    overall_sentiment: str
    overall_score: float  # -1 to +1
    signal: str  # BULLISH, BEARISH, NEUTRAL
    confidence: float
    num_articles: int
    positive_count: int
    negative_count: int
    neutral_count: int
    articles: List[ArticleSentiment]


@app.post("/api/sentiment", response_model=SentimentResponse)
async def analyze_sentiment(request: SentimentRequest):
    """Analyze sentiment for a stock based on recent news."""
    global _sentiment_analyzer, _news_fetcher
    
    load_sentiment_models()
    
    if _sentiment_analyzer is None:
        raise HTTPException(status_code=500, detail="Sentiment model not loaded")
    
    if _news_fetcher is None:
        raise HTTPException(status_code=500, detail="News fetcher not configured - check POLYGON_API_KEY")
    
    try:
        # Fetch news
        articles = _news_fetcher.get_news(request.ticker, limit=15, days_back=7)
        
        if not articles:
            return SentimentResponse(
                ticker=request.ticker,
                overall_sentiment='neutral',
                overall_score=0.0,
                signal='NEUTRAL',
                confidence=0.0,
                num_articles=0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                articles=[]
            )
        
        # Convert to dict format
        article_dicts = [
            {'title': a.title, 'description': a.description}
            for a in articles
        ]
        
        # Analyze
        result = _sentiment_analyzer.analyze_stock(request.ticker, article_dicts)
        signal, strength = _sentiment_analyzer.get_sentiment_signal(result)
        
        # Format article results
        article_results = [
            ArticleSentiment(
                title=ar.text,
                sentiment=ar.sentiment,
                confidence=round(ar.confidence, 3),
                scores={k: round(v, 3) for k, v in ar.scores.items()}
            )
            for ar in result.articles
        ]
        
        return SentimentResponse(
            ticker=request.ticker,
            overall_sentiment=result.overall_sentiment,
            overall_score=result.overall_score,
            signal=signal,
            confidence=result.confidence,
            num_articles=result.num_articles,
            positive_count=result.positive_count,
            negative_count=result.negative_count,
            neutral_count=result.neutral_count,
            articles=article_results
        )
        
    except Exception as e:
        print(f"[Sentiment Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Health Check
# =============================================================================

@app.get("/api/health")
async def health_check():
    """Check API health and component status."""
    
    status = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "rag": False,
            "cv_models": False,
            "polygon": False,
            "sentiment": False
        }
    }
    
    # Check RAG
    try:
        from rag.llm_provider import check_llm_status
        llm_status = check_llm_status()
        status["components"]["rag"] = llm_status.get('status') == 'online'
    except:
        pass
    
    # Check CV models
    status["components"]["cv_models"] = _cv_loaded and (_sr_model is not None or _trend_model is not None)
    
    # Check Polygon
    status["components"]["polygon"] = bool(os.environ.get('POLYGON_API_KEY'))
    
    # Check Sentiment
    status["components"]["sentiment"] = _sentiment_analyzer is not None
    
    return status

# =============================================================================
# Learning Progress & Leaderboard Endpoints
# =============================================================================

# Initialize Supabase client
_supabase_client = None

def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
            url = os.environ.get('SUPABASE_URL')
            # Prefer service_role key (bypasses RLS) for backend operations
            key = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY')
            if url and key:
                _supabase_client = create_client(url, key)
                print(f"[Supabase] Connected to {url}")
            else:
                print(f"[Supabase] Missing credentials: URL={'set' if url else 'MISSING'}, KEY={'set' if key else 'MISSING'}")
        except Exception as e:
            print(f"[Supabase] Failed to initialize: {e}")
            import traceback
            traceback.print_exc()
    return _supabase_client


class ProgressUpdate(BaseModel):
    user_id: str
    module_id: str
    lesson_id: str
    completed: bool = True
    display_name: Optional[str] = None


class QuizSubmission(BaseModel):
    user_id: str
    module_id: str
    lesson_id: Optional[str] = None  # None for module final quiz
    score: int
    total_questions: int
    time_taken_seconds: Optional[int] = None
    is_final_quiz: bool = False
    display_name: Optional[str] = None


class LeaderboardEntry(BaseModel):
    user_id: str
    display_name: str
    total_quiz_score: int
    avg_percentage: float
    modules_completed: int
    rank: int


def _ensure_user_profile(sb_client, user_id: str, display_name: Optional[str] = None):
    """Ensure user exists in public.users and user_profiles (creates if missing)."""
    fallback_name = display_name or f"User {user_id[:8]}"
    try:
        # Ensure public.users row (FK target for user_progress)
        existing_user = sb_client.table("users").select("id").eq("id", user_id).execute()
        if not existing_user.data:
            try:
                sb_client.table("users").insert({
                    "id": user_id,
                    "email": f"{user_id[:8]}@app.local",
                    "name": fallback_name,
                    "password_hash": "supabase_managed",
                    "password_salt": "supabase_managed",
                    "created_at": datetime.utcnow().isoformat(),
                }).execute()
                print(f"[Supabase] Auto-created public.users row for {user_id[:8]}")
            except Exception:
                pass  # May fail due to RLS; trigger should handle this
        
        # Ensure user_profiles row
        existing_profile = sb_client.table("user_profiles").select("user_id").eq("user_id", user_id).execute()
        if not existing_profile.data:
            sb_client.table("user_profiles").insert({
                "user_id": user_id,
                "display_name": fallback_name,
            }).execute()
            print(f"[Supabase] Auto-created profile for {user_id[:8]}")
    except Exception as e:
        print(f"[Supabase] Could not ensure profile: {e}")


@app.post("/api/progress")
async def update_progress(progress: ProgressUpdate):
    """Update user's lesson progress.
    
    Uses JSONB progress_data column: {module_id: {completed_lessons: [...], total_completed: N}}
    """
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        _ensure_user_profile(supabase, progress.user_id, progress.display_name)
        
        # Fetch existing progress row for this user
        existing = supabase.table("user_progress").select("*").eq("user_id", progress.user_id).execute()
        
        if existing.data:
            # Update existing JSONB progress_data
            progress_data = existing.data[0].get("progress_data") or {}
            if isinstance(progress_data, str):
                import json as _json
                progress_data = _json.loads(progress_data)
            
            mod_data = progress_data.get(progress.module_id, {"completed_lessons": [], "total_completed": 0})
            if progress.completed and progress.lesson_id not in mod_data.get("completed_lessons", []):
                mod_data.setdefault("completed_lessons", []).append(progress.lesson_id)
                mod_data["total_completed"] = len(mod_data["completed_lessons"])
            
            progress_data[progress.module_id] = mod_data
            
            result = supabase.table("user_progress").update({
                "progress_data": progress_data,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", progress.user_id).execute()
        else:
            # Create new progress row
            progress_data = {
                progress.module_id: {
                    "completed_lessons": [progress.lesson_id] if progress.completed else [],
                    "total_completed": 1 if progress.completed else 0
                }
            }
            result = supabase.table("user_progress").insert({
                "user_id": progress.user_id,
                "progress_data": progress_data,
            }).execute()
        
        # Update user_profiles stats
        total_lessons = sum(
            len(m.get("completed_lessons", []))
            for m in progress_data.values()
        )
        try:
            supabase.table("user_profiles").update({
                "total_lessons_completed": total_lessons,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", progress.user_id).execute()
        except Exception:
            pass  # Non-critical
        
        return {"success": True, "data": result.data}
    except Exception as e:
        print(f"[Progress Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/progress/{user_id}")
async def get_progress(user_id: str):
    """Get user's complete progress from JSONB progress_data column."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("user_progress").select("*").eq("user_id", user_id).execute()
        
        if result.data:
            progress_data = result.data[0].get("progress_data") or {}
            if isinstance(progress_data, str):
                import json as _json
                progress_data = _json.loads(progress_data)
            return {"user_id": user_id, "progress": progress_data}
        
        return {"user_id": user_id, "progress": {}}
    except Exception as e:
        print(f"[Progress Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quiz/submit")
async def submit_quiz(submission: QuizSubmission):
    """Submit quiz score."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        _ensure_user_profile(supabase, submission.user_id, submission.display_name)
        percentage = (submission.score / submission.total_questions) * 100 if submission.total_questions > 0 else 0
        
        if submission.is_final_quiz:
            # Module final quiz - check for existing score
            existing = supabase.table("module_quiz_scores").select("*").eq(
                "user_id", submission.user_id
            ).eq("module_id", submission.module_id).execute()
            
            if existing.data:
                # Update with best score
                old = existing.data[0]
                best_score = max(old.get("best_score", 0), submission.score)
                best_pct = max(old.get("best_percentage", 0), percentage)
                
                result = supabase.table("module_quiz_scores").update({
                    "score": submission.score,
                    "total_questions": submission.total_questions,
                    "percentage": percentage,
                    "attempts": old.get("attempts", 0) + 1,
                    "best_score": best_score,
                    "best_percentage": best_pct,
                    "time_taken_seconds": submission.time_taken_seconds,
                    "completed_at": datetime.utcnow().isoformat()
                }).eq("user_id", submission.user_id).eq("module_id", submission.module_id).execute()
            else:
                # Insert new
                result = supabase.table("module_quiz_scores").insert({
                    "user_id": submission.user_id,
                    "module_id": submission.module_id,
                    "score": submission.score,
                    "total_questions": submission.total_questions,
                    "percentage": percentage,
                    "attempts": 1,
                    "best_score": submission.score,
                    "best_percentage": percentage,
                    "time_taken_seconds": submission.time_taken_seconds
                }).execute()
        else:
            # Lesson quiz
            existing = supabase.table("lesson_quiz_scores").select("*").eq(
                "user_id", submission.user_id
            ).eq("module_id", submission.module_id).eq("lesson_id", submission.lesson_id).execute()
            
            if existing.data:
                old = existing.data[0]
                best_score = max(old.get("best_score", 0), submission.score)
                
                result = supabase.table("lesson_quiz_scores").update({
                    "score": submission.score,
                    "total_questions": submission.total_questions,
                    "percentage": percentage,
                    "attempts": old.get("attempts", 0) + 1,
                    "best_score": best_score
                }).eq("user_id", submission.user_id).eq("module_id", submission.module_id).eq("lesson_id", submission.lesson_id).execute()
            else:
                result = supabase.table("lesson_quiz_scores").insert({
                    "user_id": submission.user_id,
                    "module_id": submission.module_id,
                    "lesson_id": submission.lesson_id,
                    "score": submission.score,
                    "total_questions": submission.total_questions,
                    "percentage": percentage,
                    "best_score": submission.score
                }).execute()
        
        return {
            "success": True,
            "score": submission.score,
            "percentage": round(percentage, 1),
            "passed": percentage >= 70
        }
    except Exception as e:
        print(f"[Quiz Error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quiz/scores/{user_id}")
async def get_quiz_scores(user_id: str):
    """Get all quiz scores for a user."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        lesson_scores = supabase.table("lesson_quiz_scores").select("*").eq("user_id", user_id).execute()
        module_scores = supabase.table("module_quiz_scores").select("*").eq("user_id", user_id).execute()
        
        return {
            "user_id": user_id,
            "lesson_scores": lesson_scores.data,
            "module_scores": module_scores.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Seed community users — realistic names/emails shown on leaderboard & social
SEED_USERS = [
    {"id": "seed-01", "username": "sarah.m",       "avatar_color": "bg-violet-500",  "total_score": 58, "modules_completed": 4, "quizzes_completed": 19, "average_score": 94, "joined_date": "2025-11-02", "is_online": True,  "last_activity": "Finished Applied Investing"},
    {"id": "seed-02", "username": "jchen_99",       "avatar_color": "bg-blue-500",    "total_score": 52, "modules_completed": 3, "quizzes_completed": 16, "average_score": 91, "joined_date": "2025-11-10", "is_online": False, "last_activity": "Scored 95% on Risk Quiz"},
    {"id": "seed-03", "username": "mike.ramirez",   "avatar_color": "bg-green-500",   "total_score": 47, "modules_completed": 3, "quizzes_completed": 15, "average_score": 90, "joined_date": "2025-11-14", "is_online": True,  "last_activity": "Learning about ETFs"},
    {"id": "seed-04", "username": "priya.k",        "avatar_color": "bg-pink-500",    "total_score": 41, "modules_completed": 3, "quizzes_completed": 13, "average_score": 88, "joined_date": "2025-12-01", "is_online": True,  "last_activity": "Exploring Investor Psychology"},
    {"id": "seed-05", "username": "david.l",        "avatar_color": "bg-yellow-500",  "total_score": 35, "modules_completed": 2, "quizzes_completed": 11, "average_score": 86, "joined_date": "2025-12-08", "is_online": False, "last_activity": "Completed Foundation"},
    {"id": "seed-06", "username": "emma.w",         "avatar_color": "bg-cyan-500",    "total_score": 28, "modules_completed": 2, "quizzes_completed": 9,  "average_score": 84, "joined_date": "2025-12-15", "is_online": True,  "last_activity": "Using Stock Screener"},
    {"id": "seed-07", "username": "alex.t",         "avatar_color": "bg-orange-500",  "total_score": 22, "modules_completed": 1, "quizzes_completed": 7,  "average_score": 82, "joined_date": "2026-01-04", "is_online": False, "last_activity": "Learning Compounding"},
    {"id": "seed-08", "username": "nina.h",         "avatar_color": "bg-purple-500",  "total_score": 16, "modules_completed": 1, "quizzes_completed": 5,  "average_score": 80, "joined_date": "2026-01-12", "is_online": True,  "last_activity": "Working on Risk Management"},
    {"id": "seed-09", "username": "ryan.g",         "avatar_color": "bg-red-500",     "total_score": 10, "modules_completed": 1, "quizzes_completed": 3,  "average_score": 78, "joined_date": "2026-01-20", "is_online": False, "last_activity": "Just started Foundations"},
    {"id": "seed-10", "username": "olivia.s",       "avatar_color": "bg-teal-500",    "total_score": 5,  "modules_completed": 0, "quizzes_completed": 2,  "average_score": 75, "joined_date": "2026-02-01", "is_online": True,  "last_activity": "Signed up today"},
    {"id": "seed-11", "username": "james.p",        "avatar_color": "bg-indigo-500",  "total_score": 44, "modules_completed": 3, "quizzes_completed": 14, "average_score": 89, "joined_date": "2025-11-20", "is_online": True,  "last_activity": "Studying Tax Planning"},
    {"id": "seed-12", "username": "zoe.martinez",   "avatar_color": "bg-emerald-500", "total_score": 33, "modules_completed": 2, "quizzes_completed": 10, "average_score": 85, "joined_date": "2025-12-05", "is_online": False, "last_activity": "Completed Market Dynamics"},
]

AVATAR_COLORS = [
    "bg-yellow-500", "bg-blue-500", "bg-green-500", "bg-purple-500", "bg-pink-500",
    "bg-cyan-500", "bg-orange-500", "bg-red-500", "bg-indigo-500", "bg-teal-500",
    "bg-emerald-500", "bg-violet-500", "bg-amber-500", "bg-rose-500", "bg-lime-500"
]


@app.get("/api/leaderboard")
async def get_leaderboard(module_id: Optional[str] = None, limit: int = 50):
    """Get leaderboard — merges real Supabase users with seed community users."""
    supabase = get_supabase()
    
    # Start with seed users as the base (gives the leaderboard a populated feel)
    combined = [dict(u) for u in SEED_USERS]
    
    try:
        if supabase:
            if module_id:
                # Module-specific leaderboard
                result = supabase.table("module_quiz_scores").select(
                    "user_id, best_score, best_percentage, attempts"
                ).eq("module_id", module_id).order("best_score", desc=True).limit(limit).execute()
                
                for entry in (result.data or []):
                    uid = entry["user_id"]
                    profile = supabase.table("user_profiles").select("display_name").eq("user_id", uid).execute()
                    display_name = profile.data[0]["display_name"] if profile.data else f"User {uid[:8]}"
                    
                    combined.append({
                        "id": uid,
                        "user_id": uid,
                        "username": display_name,
                        "avatar_color": AVATAR_COLORS[len(combined) % len(AVATAR_COLORS)],
                        "total_score": entry.get("best_score", 0),
                        "quizzes_completed": entry.get("attempts", 1),
                        "modules_completed": 1,
                        "average_score": round(entry.get("best_percentage", 0)),
                        "is_real": True,
                    })
            else:
                # Global leaderboard — aggregate lesson + module quiz scores
                lesson_scores = supabase.table("lesson_quiz_scores").select("*").execute()
                module_scores = supabase.table("module_quiz_scores").select("*").execute()
                profiles = supabase.table("user_profiles").select("*").execute()
                
                profile_lookup = {p["user_id"]: p for p in (profiles.data or [])}
                
                user_data = {}
                for score in (lesson_scores.data or []):
                    uid = score["user_id"]
                    if uid not in user_data:
                        user_data[uid] = {"total_score": 0, "quizzes_completed": 0, "total_pct": 0}
                    user_data[uid]["total_score"] += score.get("score", 0)
                    user_data[uid]["quizzes_completed"] += 1
                    user_data[uid]["total_pct"] += score.get("percentage", 0)
                
                for score in (module_scores.data or []):
                    uid = score["user_id"]
                    if uid not in user_data:
                        user_data[uid] = {"total_score": 0, "quizzes_completed": 0, "total_pct": 0}
                    user_data[uid]["total_score"] += score.get("score", 0)
                    user_data[uid]["quizzes_completed"] += 1
                    user_data[uid]["total_pct"] += score.get("percentage", 0)
                
                for uid, data in user_data.items():
                    profile = profile_lookup.get(uid, {})
                    display_name = profile.get("display_name") or f"User {uid[:8]}"
                    avg_score = round(data["total_pct"] / data["quizzes_completed"]) if data["quizzes_completed"] > 0 else 0
                    
                    combined.append({
                        "id": uid,
                        "user_id": uid,
                        "username": display_name,
                        "avatar_color": AVATAR_COLORS[len(combined) % len(AVATAR_COLORS)],
                        "total_score": data["total_score"],
                        "quizzes_completed": data["quizzes_completed"],
                        "modules_completed": data["quizzes_completed"] // 5,
                        "average_score": avg_score,
                        "is_real": True,
                    })
    except Exception as e:
        print(f"[Leaderboard Error] {e}")
    
    # Sort by total_score descending, assign ranks
    combined.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    for i, entry in enumerate(combined[:limit]):
        entry["rank"] = i + 1
    
    return combined[:limit]


@app.post("/api/profile")
async def update_profile(user_id: str, display_name: str):
    """Update user profile (also ensures public.users row exists)."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        _ensure_user_profile(supabase, user_id, display_name)
        
        result = supabase.table("user_profiles").upsert({
            "user_id": user_id,
            "display_name": display_name,
            "updated_at": datetime.utcnow().isoformat()
        }, on_conflict="user_id").execute()
        
        return {"success": True, "data": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Social Endpoints (leaderboard is defined above with SEED_USERS)
# =============================================================================


@app.get("/api/users")
async def get_community_users(limit: int = 50):
    """Get community users for social page — merges real users with seed data."""
    supabase = get_supabase()
    
    # Start with seed users
    combined = [dict(u) for u in SEED_USERS]
    
    try:
        if supabase:
            profiles = supabase.table("user_profiles").select("*").limit(limit).execute()
            lesson_scores = supabase.table("lesson_quiz_scores").select("*").execute()
            module_scores = supabase.table("module_quiz_scores").select("*").execute()
            
            # Aggregate scores by user
            user_scores = {}
            for score in (lesson_scores.data or []):
                uid = score["user_id"]
                if uid not in user_scores:
                    user_scores[uid] = {"total_score": 0, "quizzes_completed": 0}
                user_scores[uid]["total_score"] += score.get("score", 0)
                user_scores[uid]["quizzes_completed"] += 1
            
            for score in (module_scores.data or []):
                uid = score["user_id"]
                if uid not in user_scores:
                    user_scores[uid] = {"total_score": 0, "quizzes_completed": 0}
                user_scores[uid]["total_score"] += score.get("score", 0)
                user_scores[uid]["quizzes_completed"] += 1
            
            for profile in (profiles.data or []):
                uid = profile["user_id"]
                scores = user_scores.get(uid, {"total_score": 0, "quizzes_completed": 0})
                
                combined.append({
                    "id": uid,
                    "username": profile.get("display_name") or f"User {uid[:8]}",
                    "avatar_color": AVATAR_COLORS[len(combined) % len(AVATAR_COLORS)],
                    "total_score": scores["total_score"],
                    "modules_completed": scores["quizzes_completed"] // 5,
                    "quizzes_completed": scores["quizzes_completed"],
                    "joined_date": profile.get("created_at", "2024-01-01")[:10],
                    "is_online": True,
                    "last_activity": "Learning on FinLearn AI",
                    "is_real": True,
                })
    except Exception as e:
        print(f"[Users Error] {e}")
    
    # Sort by score descending
    combined.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    return combined[:limit]


@app.get("/api/user-stats/{user_id}")
async def get_user_stats(user_id: str):
    """Get detailed stats for a specific user."""
    supabase = get_supabase()
    
    if not supabase:
        return {
            "rank": None,
            "total_score": 0,
            "quizzes_completed": 0,
            "average_score": 0,
            "modules_completed": 0
        }
    
    try:
        # Get user's scores
        lesson_scores = supabase.table("lesson_quiz_scores").select("*").eq("user_id", user_id).execute()
        module_scores = supabase.table("module_quiz_scores").select("*").eq("user_id", user_id).execute()
        
        total_score = 0
        total_pct = 0
        quiz_count = 0
        
        for score in (lesson_scores.data or []):
            total_score += score.get("score", 0)
            total_pct += score.get("percentage", 0)
            quiz_count += 1
        
        for score in (module_scores.data or []):
            total_score += score.get("score", 0)
            total_pct += score.get("percentage", 0)
            quiz_count += 1
        
        avg_score = round(total_pct / quiz_count) if quiz_count > 0 else 0
        
        # Get rank by comparing to all users
        all_scores = supabase.table("lesson_quiz_scores").select("user_id, score").execute()
        user_totals = {}
        for score in (all_scores.data or []):
            uid = score["user_id"]
            if uid not in user_totals:
                user_totals[uid] = 0
            user_totals[uid] += score.get("score", 0)
        
        # Add module scores
        all_module_scores = supabase.table("module_quiz_scores").select("user_id, score").execute()
        for score in (all_module_scores.data or []):
            uid = score["user_id"]
            if uid not in user_totals:
                user_totals[uid] = 0
            user_totals[uid] += score.get("score", 0)
        
        # Sort and find rank
        sorted_users = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)
        rank = None
        for i, (uid, _) in enumerate(sorted_users):
            if uid == user_id:
                rank = i + 1
                break
        
        return {
            "rank": rank,
            "total_score": total_score,
            "quizzes_completed": quiz_count,
            "average_score": avg_score,
            "modules_completed": quiz_count // 5
        }
        
    except Exception as e:
        print(f"[User Stats Error] {e}")
        return {
            "rank": None,
            "total_score": 0,
            "quizzes_completed": 0,
            "average_score": 0,
            "modules_completed": 0
        }


# =============================================================================
# AI Stock Discovery & Asset Allocation Endpoints
# =============================================================================

# Import asset allocation modules
from stock_universe_analyzer import StockUniverseAnalyzer, SP500_TICKERS
from sector_normalizer import SectorNormalizer
from stock_scorer import StockScorer
from portfolio_optimizer import PortfolioOptimizer

# Analysis job tracking
_analysis_jobs: Dict[str, Dict[str, Any]] = {}
_universe_cache: Optional[Dict[str, Any]] = None
_universe_cache_time: Optional[datetime] = None
_CACHE_TTL_HOURS = 168  # 7 days — matches weekly analysis schedule

def _load_cache_from_file():
    """Load cached analysis from file if it exists."""
    global _universe_cache, _universe_cache_time
    cache_file = Path(__file__).parent / "cache" / "sp500_analysis.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                import json
                data = json.load(f)
                _universe_cache = data
                # Parse timestamp
                if "timestamp" in data:
                    _universe_cache_time = datetime.fromisoformat(data["timestamp"])
                else:
                    # Use file modification time
                    _universe_cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                print(f"[Cache] Loaded {len(data.get('stocks', []))} stocks from cache file")
        except Exception as e:
            print(f"[Cache] Failed to load cache file: {e}")

# Load cache on module import (before endpoints are defined)
_load_cache_from_file()


class AnalyzeUniverseRequest(BaseModel):
    tickers: Optional[List[str]] = None  # If None, analyzes all S&P 500


class AnalyzeUniverseResponse(BaseModel):
    job_id: str
    estimated_time_minutes: int
    message: str


class AnalysisStatusResponse(BaseModel):
    job_id: str
    status: str  # "running", "completed", "failed"
    progress: int  # 0-100
    current_ticker: Optional[str] = None
    completed: int
    total: int
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class StockUniverseResultsResponse(BaseModel):
    stocks: List[Dict[str, Any]]
    sectors: Dict[str, Dict[str, Any]]
    stats: Dict[str, Any]
    last_updated: str
    total_analyzed: int


class OptimizePortfolioRequest(BaseModel):
    tickers: List[str]
    objective: str = "sharpe"  # "sharpe", "min_risk", "max_return"
    constraints: Optional[Dict[str, Any]] = None
    custom_weights: Optional[Dict[str, float]] = None  # If provided, uses these instead of optimizing


class PortfolioAnalysisResponse(BaseModel):
    weights: Dict[str, float]
    analysis: Dict[str, Any]
    stocks: List[Dict[str, Any]]


@app.post("/api/ai/stock-universe/analyze", response_model=AnalyzeUniverseResponse)
async def analyze_universe(request: AnalyzeUniverseRequest):
    """Trigger S&P 500 stock universe analysis."""
    global _analysis_jobs
    
    polygon_key = os.environ.get('POLYGON_API_KEY')
    if not polygon_key:
        raise HTTPException(status_code=500, detail="Polygon API key not configured")
    
    from polygon import RESTClient
    client = RESTClient(polygon_key)
    
    analyzer = StockUniverseAnalyzer(client)
    # Inject the prewarmed FinBERT model so the analyzer doesn't load it again
    if _sentiment_analyzer is not None and _news_fetcher is not None:
        analyzer.set_sentiment_models(_sentiment_analyzer, _news_fetcher)
    
    tickers = request.tickers or SP500_TICKERS
    job_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Estimate time (roughly 2-3 seconds per stock)
    estimated_minutes = len(tickers) * 3 / 60
    
    # Start analysis in background
    _analysis_jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "completed": 0,
        "total": len(tickers),
        "current_ticker": None,
        "results": None,
        "error": None
    }
    
    async def run_analysis():
        try:
            def progress_callback(current, total, ticker):
                _analysis_jobs[job_id]["progress"] = int((current / total) * 100)
                _analysis_jobs[job_id]["completed"] = current
                _analysis_jobs[job_id]["current_ticker"] = ticker
            
            # Run analysis
            results = analyzer.analyze_universe(tickers, progress_callback)
            
            # Normalize by sector
            normalized_stocks = SectorNormalizer.normalize_all_metrics(results["stocks"])
            
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
                # Get top 5 stocks in sector
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
            
            # Deduplicate by ticker (keep first occurrence)
            seen_tickers = set()
            unique_stocks = []
            for s in scored_stocks:
                if s["ticker"] not in seen_tickers:
                    seen_tickers.add(s["ticker"])
                    unique_stocks.append(s)
            scored_stocks = unique_stocks
            
            final_results = {
                "stocks": scored_stocks,
                "sectors": sectors,
                "stats": stats,
                "timestamp": datetime.now().isoformat(),
                "total_analyzed": len(scored_stocks)
            }
            
            # Update cache (both in-memory and file)
            global _universe_cache, _universe_cache_time
            _universe_cache = final_results
            _universe_cache_time = datetime.now()
            
            # Also save to file for persistence across server restarts
            cache_dir = Path(__file__).parent / "cache"
            cache_dir.mkdir(exist_ok=True)
            cache_file = cache_dir / "sp500_analysis.json"
            with open(cache_file, 'w') as f:
                import json
                json.dump(final_results, f, indent=2)
            
            _analysis_jobs[job_id]["status"] = "completed"
            _analysis_jobs[job_id]["progress"] = 100
            _analysis_jobs[job_id]["results"] = final_results
            
        except Exception as e:
            _analysis_jobs[job_id]["status"] = "failed"
            _analysis_jobs[job_id]["error"] = str(e)
            import traceback
            traceback.print_exc()
    
    # Run in background
    import asyncio
    asyncio.create_task(run_analysis())
    
    return AnalyzeUniverseResponse(
        job_id=job_id,
        estimated_time_minutes=int(estimated_minutes),
        message=f"Analysis started for {len(tickers)} stocks"
    )


@app.get("/api/ai/stock-universe/status/{job_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(job_id: str):
    """Get analysis job status."""
    if job_id not in _analysis_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = _analysis_jobs[job_id]
    
    return AnalysisStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        current_ticker=job.get("current_ticker"),
        completed=job["completed"],
        total=job["total"],
        results=job.get("results"),
        error=job.get("error")
    )


@app.get("/api/ai/stock-universe/results", response_model=StockUniverseResultsResponse)
async def get_universe_results(
    sector: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    limit: int = 500,
    sort_by: str = "composite_score"
):
    """Get cached universe analysis results with filters."""
    global _universe_cache, _universe_cache_time
    
    # Check cache
    if _universe_cache is None or _universe_cache_time is None:
        raise HTTPException(status_code=404, detail="No analysis results available. Run analysis first.")
    
    # Check cache age
    cache_age = datetime.now() - _universe_cache_time
    if cache_age.total_seconds() > _CACHE_TTL_HOURS * 3600:
        raise HTTPException(status_code=410, detail="Cache expired. Please run new analysis.")
    
    stocks = _universe_cache["stocks"].copy()
    
    # Apply filters
    if sector:
        stocks = [s for s in stocks if s.get("sector") == sector]
    
    if min_score is not None:
        stocks = [s for s in stocks if s.get("composite_score", 0) >= min_score]
    
    if max_score is not None:
        stocks = [s for s in stocks if s.get("composite_score", 100) <= max_score]
    
    # Sort
    if sort_by == "composite_score":
        stocks.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
    elif sort_by == "ticker":
        stocks.sort(key=lambda x: x.get("ticker", ""))
    elif sort_by == "sector":
        stocks.sort(key=lambda x: (x.get("sector", ""), -x.get("composite_score", 0)))
    
    # Limit
    stocks = stocks[:limit]
    
    return StockUniverseResultsResponse(
        stocks=stocks,
        sectors=_universe_cache["sectors"],
        stats=_universe_cache["stats"],
        last_updated=_universe_cache_time.isoformat(),
        total_analyzed=len(stocks)
    )


@app.get("/api/ai/stock-universe/stock/{ticker}")
async def get_stock_details(ticker: str):
    """Get detailed analysis for a single stock."""
    global _universe_cache
    
    if _universe_cache is None:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    stock = next((s for s in _universe_cache["stocks"] if s["ticker"] == ticker.upper()), None)
    
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found in analysis")
    
    return stock


@app.post("/api/ai/asset-allocation/optimize", response_model=PortfolioAnalysisResponse)
async def optimize_portfolio(request: OptimizePortfolioRequest):
    """Optimize portfolio allocation from selected stocks."""
    global _universe_cache
    
    if _universe_cache is None:
        raise HTTPException(status_code=404, detail="No universe analysis available. Run analysis first.")
    
    # Get stock data for selected tickers
    selected_stocks = []
    for ticker in request.tickers:
        stock = next((s for s in _universe_cache["stocks"] if s["ticker"] == ticker.upper()), None)
        if stock:
            selected_stocks.append(stock)
    
    if not selected_stocks:
        raise HTTPException(status_code=400, detail="No valid stocks found for selected tickers")
    
    # Use custom weights if provided, otherwise optimize
    if request.custom_weights:
        weights = {k.upper(): v / 100.0 for k, v in request.custom_weights.items()}  # Convert % to decimal
    else:
        # Optimize
        weights = PortfolioOptimizer.optimize_portfolio(
            selected_stocks,
            objective=request.objective,
            constraints=request.constraints or {}
        )
    
    # Analyze portfolio
    analysis = PortfolioOptimizer.analyze_portfolio(selected_stocks, weights)
    
    return PortfolioAnalysisResponse(
        weights={k: round(v * 100, 2) for k, v in weights.items()},  # Convert to percentage
        analysis=analysis,
        stocks=selected_stocks
    )


@app.post("/api/ai/asset-allocation/analyze")
async def analyze_portfolio(request: OptimizePortfolioRequest):
    """Analyze a portfolio with given weights (no optimization)."""
    return await optimize_portfolio(request)  # Same endpoint, just requires custom_weights


# =============================================================================
# GA-Based ETF Portfolio Optimizer
# =============================================================================

class ETFAllocationRequest(BaseModel):
    answers: Dict[str, Any]
    required_etfs: Optional[List[str]] = None
    simulate: Optional[Dict[str, Any]] = None

@app.post("/api/etf/optimize")
async def optimize_etf_allocation_endpoint(request: ETFAllocationRequest):
    """
    Endpoint for GA-based ETF portfolio optimization and optional Monte Carlo simulation.
    """
    try:
        from ga_etf_optimizer import optimize_etf_portfolio
        result = optimize_etf_portfolio(
            answers=request.answers,
            required_etfs=request.required_etfs,
            simulate=request.simulate,
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
