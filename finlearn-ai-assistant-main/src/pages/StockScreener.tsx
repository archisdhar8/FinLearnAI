import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  RefreshCw, 
  Search,
  ArrowLeft,
  BarChart3,
  Target,
  Zap,
  AlertCircle
} from "lucide-react";

// Simple markdown parser for AI analysis text
function parseMarkdown(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Bold: **text**
    const boldMatch = remaining.match(/^\*\*(.+?)\*\*/);
    if (boldMatch) {
      parts.push(<strong key={key++} className="font-semibold text-foreground">{boldMatch[1]}</strong>);
      remaining = remaining.slice(boldMatch[0].length);
      continue;
    }

    // Italic: *text*
    const italicMatch = remaining.match(/^\*(.+?)\*/);
    if (italicMatch) {
      parts.push(<em key={key++}>{italicMatch[1]}</em>);
      remaining = remaining.slice(italicMatch[0].length);
      continue;
    }

    // Line breaks
    if (remaining.startsWith('\n\n')) {
      parts.push(<span key={key++} className="block h-2" />);
      remaining = remaining.slice(2);
      continue;
    }
    if (remaining.startsWith('\n')) {
      parts.push(<br key={key++} />);
      remaining = remaining.slice(1);
      continue;
    }

    // Regular text - take until next special character
    const nextSpecial = remaining.search(/[\*\n]/);
    if (nextSpecial === -1) {
      parts.push(remaining);
      break;
    } else if (nextSpecial === 0) {
      parts.push(remaining[0]);
      remaining = remaining.slice(1);
    } else {
      parts.push(remaining.slice(0, nextSpecial));
      remaining = remaining.slice(nextSpecial);
    }
  }

  return parts;
}

// Stock categories - matching Streamlit app
const WATCHLISTS: Record<string, string[]> = {
  "Tech Giants": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA"],
  "Finance": ["JPM", "BAC", "GS", "V", "MA", "AXP"],
  "Consumer": ["WMT", "HD", "NKE", "SBUX", "MCD", "COST"],
  "Healthcare": ["JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY"],
  "ETFs": ["SPY", "QQQ", "IWM", "DIA", "XLF", "XLE"],
  "Growth": ["TSLA", "NFLX", "CRM", "ADBE", "SQ", "SHOP"],
};

interface StockData {
  ticker: string;
  price: number;
  change: number;
  change_pct: number;
  trend: string;
  trend_confidence: number;
  signal: string;
  signal_strength: number;
  support: number | null;
  resistance: number | null;
  support_zones: Array<{ price: number; confidence: number }>;
  resistance_zones: Array<{ price: number; confidence: number }>;
  chart_image: string; // Base64 encoded PNG
  // Sentiment fields
  sentiment: string | null;
  sentiment_score: number | null;
  sentiment_signal: string | null;
  news_count: number | null;
  // AI Analysis
  ai_analysis: string | null;
}

// Fetch real stock data from backend with CV analysis
const fetchStockData = async (tickers: string[]): Promise<StockData[]> => {
  try {
    const { API_URL } = await import("@/lib/api");
    const response = await fetch(`${API_URL}/api/stocks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tickers }),
    });
    
    if (response.ok) {
      return await response.json();
    }
    throw new Error("API request failed");
  } catch (error) {
    console.error("Failed to fetch stocks:", error);
    return [];
  }
};

export default function StockScreener() {
  const navigate = useNavigate();
  const [selectedCategory, setSelectedCategory] = useState("Tech Giants");
  const [stocks, setStocks] = useState<StockData[]>([]);
  const [loading, setLoading] = useState(false);
  const [customTicker, setCustomTicker] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check auth
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) navigate("/");
    });
  }, [navigate]);

  useEffect(() => {
    loadStocks();
  }, [selectedCategory]);

  const loadStocks = async () => {
    setLoading(true);
    setError(null);
    const tickers = WATCHLISTS[selectedCategory];
    const data = await fetchStockData(tickers);
    if (data.length === 0) {
      setError("Could not fetch stock data. Make sure the backend is running.");
    }
    setStocks(data);
    setLoading(false);
  };

  const addCustomTicker = async () => {
    if (customTicker && !stocks.find(s => s.ticker === customTicker.toUpperCase())) {
      setLoading(true);
      const data = await fetchStockData([customTicker.toUpperCase()]);
      if (data.length > 0) {
        setStocks([...stocks, data[0]]);
      }
      setCustomTicker("");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate("/dashboard")}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <BarChart3 className="w-4 h-4 text-primary" />
              </div>
              <span className="font-display text-sm font-semibold">AI Stock Screener</span>
            </div>
          </div>
          <button
            onClick={loadStocks}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-sm hover:bg-primary/20 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Hero */}
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold mb-2">AI Stock Screener</h1>
          <p className="text-muted-foreground">
            Real-time analysis with Computer Vision models (S/R + Trend detection)
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-destructive/10 border border-destructive/30 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-destructive" />
            <span className="text-destructive">{error}</span>
          </div>
        )}

        {/* Controls */}
        <div className="flex flex-wrap gap-4 mb-8">
          {/* Category selector */}
          <div className="flex gap-2 flex-wrap">
            {Object.keys(WATCHLISTS).map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  selectedCategory === cat
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted hover:bg-muted/80"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Custom ticker input */}
          <div className="flex gap-2 ml-auto">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                value={customTicker}
                onChange={(e) => setCustomTicker(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === "Enter" && addCustomTicker()}
                placeholder="Add ticker..."
                className="pl-9 pr-4 py-2 bg-muted rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary w-32"
              />
            </div>
            <button
              onClick={addCustomTicker}
              className="px-3 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:opacity-90"
            >
              Add
            </button>
          </div>
        </div>

        {/* Stock Cards */}
        <div className="space-y-6">
          {loading ? (
            <div className="text-center py-12 text-muted-foreground">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4" />
              <p>Fetching real stock data and running CV analysis...</p>
              <p className="text-sm mt-2">This may take a moment</p>
            </div>
          ) : stocks.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No stock data available</p>
              <p className="text-sm mt-2">Make sure the backend server is running on port 8000</p>
            </div>
          ) : (
            stocks.map((stock) => (
              <div key={stock.ticker} className="glass-card rounded-xl p-6">
                <div className="flex items-start justify-between gap-6">
                  {/* Stock Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-4">
                      <h3 className="text-2xl font-bold">{stock.ticker}</h3>
                      <span className={`text-lg ${stock.change >= 0 ? "text-success" : "text-destructive"}`}>
                        ${stock.price.toFixed(2)}
                      </span>
                      <span className={`text-sm ${stock.change >= 0 ? "text-success" : "text-destructive"}`}>
                        {stock.change >= 0 ? "+" : ""}{stock.change_pct.toFixed(2)}%
                      </span>
                    </div>

                    {/* Real Chart Image from CV Analysis */}
                    {stock.chart_image ? (
                      <div className="rounded-lg overflow-hidden mb-4 border border-border/30">
                        <img 
                          src={`data:image/png;base64,${stock.chart_image}`}
                          alt={`${stock.ticker} 30-day chart`}
                          className="w-full h-auto"
                        />
                      </div>
                    ) : (
                      <div className="h-32 bg-muted/50 rounded-lg flex items-center justify-center mb-4">
                        <span className="text-muted-foreground text-sm">Chart unavailable</span>
                      </div>
                    )}

                    {/* AI Analysis Paragraph */}
                    {stock.ai_analysis && (
                      <div className="p-3 rounded-lg bg-muted/30 border border-border/30">
                        <div className="flex items-center gap-2 mb-2">
                          <Zap className="w-4 h-4 text-primary" />
                          <span className="text-xs font-semibold text-primary">AI Analysis</span>
                        </div>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {parseMarkdown(stock.ai_analysis)}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* AI Analysis */}
                  <div className="w-52 space-y-3">
                    {/* Trend-based Signal Card */}
                    {(() => {
                      // Derive signal from trend
                      const trend = stock.trend;
                      const confidence = stock.trend_confidence;
                      
                      let displaySignal: string;
                      let bgClass: string;
                      let textClass: string;
                      
                      if (trend === 'uptrend') {
                        displaySignal = 'BUY';
                        bgClass = 'bg-success/10 border-success/30';
                        textClass = 'text-success';
                      } else if (trend === 'downtrend') {
                        displaySignal = 'SELL';
                        bgClass = 'bg-destructive/10 border-destructive/30';
                        textClass = 'text-destructive';
                      } else {
                        displaySignal = 'HOLD';
                        bgClass = 'bg-muted/50';
                        textClass = 'text-muted-foreground';
                      }
                      
                      return (
                        <div className={`glass-card rounded-lg p-4 text-center ${bgClass}`}>
                          <div className={`text-2xl font-bold ${textClass}`}>
                            {displaySignal}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {confidence.toFixed(0)}% confidence
                          </div>
                        </div>
                      );
                    })()}

                    <div className="space-y-2">
                      {/* Support Zones */}
                      {stock.support_zones && stock.support_zones.length > 0 ? (
                        stock.support_zones.slice(0, 2).map((zone, i) => (
                          <div key={`support-${i}`} className="flex items-center justify-between text-sm bg-success/10 rounded-lg px-2 py-1">
                            <span className="text-success flex items-center gap-1">
                              <Target className="w-3 h-3" /> Support
                            </span>
                            <span className="text-success font-medium">${zone.price.toFixed(2)}</span>
                          </div>
                        ))
                      ) : stock.support && (
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-success flex items-center gap-1">
                            <Target className="w-3 h-3" /> Support
                          </span>
                          <span>${stock.support.toFixed(2)}</span>
                        </div>
                      )}
                      
                      {/* Resistance Zones */}
                      {stock.resistance_zones && stock.resistance_zones.length > 0 ? (
                        stock.resistance_zones.slice(0, 2).map((zone, i) => (
                          <div key={`resistance-${i}`} className="flex items-center justify-between text-sm bg-destructive/10 rounded-lg px-2 py-1">
                            <span className="text-destructive flex items-center gap-1">
                              <Target className="w-3 h-3" /> Resistance
                            </span>
                            <span className="text-destructive font-medium">${zone.price.toFixed(2)}</span>
                          </div>
                        ))
                      ) : stock.resistance && (
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-destructive flex items-center gap-1">
                            <Target className="w-3 h-3" /> Resistance
                          </span>
                          <span>${stock.resistance.toFixed(2)}</span>
                        </div>
                      )}
                    </div>

                    {/* Sentiment Section */}
                    <div className="pt-2 border-t border-border/30">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground flex items-center gap-1">
                          <Zap className="w-3 h-3" /> Sentiment
                        </span>
                        {(() => {
                          const signal = (stock.sentiment_signal || '').toUpperCase();
                          const sentiment = stock.sentiment || '';
                          const isBullish = signal === 'BULLISH' || sentiment === 'positive';
                          const isBearish = signal === 'BEARISH' || sentiment === 'negative';
                          
                          // If no sentiment data yet, show loading
                          if (!stock.sentiment && !stock.sentiment_signal) {
                            return <span className="text-muted-foreground">Loading...</span>;
                          }
                          
                          if (isBullish) {
                            return <span className="font-medium text-green-500">Bullish</span>;
                          } else if (isBearish) {
                            return <span className="font-medium text-red-500">Bearish</span>;
                          } else {
                            return <span className="font-medium text-yellow-500">Neutral</span>;
                          }
                        })()}
                      </div>
                      {stock.sentiment_score !== null && stock.sentiment_score !== undefined && (
                        <div className="mt-1">
                          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                            <div 
                              className={`h-full transition-all ${
                                stock.sentiment_score > 0 ? 'bg-success' :
                                stock.sentiment_score < 0 ? 'bg-destructive' :
                                'bg-warning'
                              }`}
                              style={{ 
                                width: `${Math.min(Math.abs(stock.sentiment_score) * 100, 100)}%`,
                                marginLeft: stock.sentiment_score < 0 ? 'auto' : 0
                              }}
                            />
                          </div>
                          <div className="flex justify-between text-[10px] text-muted-foreground mt-0.5">
                            <span>{stock.news_count || 0} articles</span>
                            <span>{(stock.sentiment_score * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Disclaimer */}
        <div className="mt-8 text-center text-xs text-muted-foreground">
          <p>AI signals are for educational purposes only. Not financial advice.</p>
          <p className="mt-1">Data: Polygon.io | Models: Trained CV for S/R and Trend detection</p>
        </div>
      </div>
    </div>
  );
}
