import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Brain, TrendingUp, TrendingDown, Minus, Newspaper, AlertCircle, Loader2 } from "lucide-react";

interface ArticleSentiment {
  title: string;
  sentiment: string;
  confidence: number;
  scores: {
    positive: number;
    negative: number;
    neutral: number;
  };
}

interface SentimentResult {
  ticker: string;
  overall_sentiment: string;
  overall_score: number;
  signal: string;
  confidence: number;
  num_articles: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  articles: ArticleSentiment[];
}

const SentimentAnalyzer = () => {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SentimentResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyzeSentiment = async () => {
    if (!ticker.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const { API_URL } = await import("@/lib/api");
      const response = await fetch(`${API_URL}/api/sentiment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: ticker.toUpperCase() })
      });
      
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Analysis failed');
      }
      
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze sentiment');
    } finally {
      setLoading(false);
    }
  };

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return <TrendingUp className="h-5 w-5 text-green-500" />;
      case 'negative': return <TrendingDown className="h-5 w-5 text-red-500" />;
      default: return <Minus className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'text-green-500';
      case 'negative': return 'text-red-500';
      default: return 'text-yellow-500';
    }
  };

  const getSignalBadge = (signal: string) => {
    const colors = {
      'BULLISH': 'bg-green-500/20 text-green-400 border-green-500/30',
      'BEARISH': 'bg-red-500/20 text-red-400 border-red-500/30',
      'NEUTRAL': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    };
    return colors[signal as keyof typeof colors] || colors.NEUTRAL;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-3">
            <Brain className="h-10 w-10 text-purple-400" />
            <h1 className="text-3xl font-bold text-white">Sentiment Analyzer</h1>
          </div>
          <p className="text-slate-400">AI-powered news sentiment analysis using FinBERT</p>
        </div>

        {/* Input Section */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-6">
            <div className="flex gap-4">
              <Input
                placeholder="Enter ticker symbol (e.g., AAPL)"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && analyzeSentiment()}
                className="bg-slate-900 border-slate-600 text-white text-lg"
              />
              <Button 
                onClick={analyzeSentiment}
                disabled={loading || !ticker.trim()}
                className="bg-purple-600 hover:bg-purple-700 px-8"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  'Analyze'
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Error */}
        {error && (
          <Card className="bg-red-500/10 border-red-500/30">
            <CardContent className="p-4 flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-400" />
              <span className="text-red-400">{error}</span>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Overall Sentiment Card */}
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="text-white">{result.ticker} Sentiment Analysis</span>
                  <span className={`px-4 py-2 rounded-full border text-sm font-bold ${getSignalBadge(result.signal)}`}>
                    {result.signal}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Score Gauge */}
                <div className="flex items-center justify-center">
                  <div className="relative w-64 h-32">
                    {/* Gauge background */}
                    <div className="absolute inset-0 flex items-end justify-center">
                      <div className="w-full h-1/2 rounded-t-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 opacity-30" />
                    </div>
                    {/* Score indicator */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className={`text-5xl font-bold ${getSentimentColor(result.overall_sentiment)}`}>
                        {result.overall_score > 0 ? '+' : ''}{(result.overall_score * 100).toFixed(0)}
                      </span>
                      <span className={`text-xl capitalize ${getSentimentColor(result.overall_sentiment)}`}>
                        {result.overall_sentiment}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="bg-slate-900/50 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-white">{result.num_articles}</div>
                    <div className="text-sm text-slate-400">Articles</div>
                  </div>
                  <div className="bg-green-500/10 rounded-lg p-4 text-center border border-green-500/20">
                    <div className="text-2xl font-bold text-green-400">{result.positive_count}</div>
                    <div className="text-sm text-slate-400">Positive</div>
                  </div>
                  <div className="bg-red-500/10 rounded-lg p-4 text-center border border-red-500/20">
                    <div className="text-2xl font-bold text-red-400">{result.negative_count}</div>
                    <div className="text-sm text-slate-400">Negative</div>
                  </div>
                  <div className="bg-yellow-500/10 rounded-lg p-4 text-center border border-yellow-500/20">
                    <div className="text-2xl font-bold text-yellow-400">{result.neutral_count}</div>
                    <div className="text-sm text-slate-400">Neutral</div>
                  </div>
                </div>

                {/* Confidence */}
                <div className="flex items-center gap-4">
                  <span className="text-slate-400">Model Confidence:</span>
                  <div className="flex-1 bg-slate-900 rounded-full h-3">
                    <div 
                      className="bg-purple-500 h-3 rounded-full transition-all"
                      style={{ width: `${result.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-white font-medium">{(result.confidence * 100).toFixed(1)}%</span>
                </div>
              </CardContent>
            </Card>

            {/* Articles List */}
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white">
                  <Newspaper className="h-5 w-5" />
                  Recent News ({result.articles.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {result.articles.map((article, idx) => (
                    <div 
                      key={idx}
                      className="bg-slate-900/50 rounded-lg p-4 border border-slate-700 hover:border-slate-600 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        {getSentimentIcon(article.sentiment)}
                        <div className="flex-1 min-w-0">
                          <p className="text-white text-sm leading-relaxed">{article.title}</p>
                          <div className="flex items-center gap-4 mt-2 text-xs">
                            <span className={`capitalize font-medium ${getSentimentColor(article.sentiment)}`}>
                              {article.sentiment}
                            </span>
                            <span className="text-slate-500">
                              Confidence: {(article.confidence * 100).toFixed(1)}%
                            </span>
                            <div className="flex gap-2 text-slate-500">
                              <span className="text-green-400">+{(article.scores.positive * 100).toFixed(0)}%</span>
                              <span className="text-red-400">-{(article.scores.negative * 100).toFixed(0)}%</span>
                              <span className="text-yellow-400">={(article.scores.neutral * 100).toFixed(0)}%</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Empty State */}
        {!result && !loading && !error && (
          <Card className="bg-slate-800/30 border-slate-700 border-dashed">
            <CardContent className="p-12 text-center">
              <Brain className="h-16 w-16 text-slate-600 mx-auto mb-4" />
              <h3 className="text-xl text-slate-400 mb-2">Enter a ticker to analyze</h3>
              <p className="text-slate-500 text-sm">
                Our AI will fetch recent news and analyze sentiment using FinBERT
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default SentimentAnalyzer;
