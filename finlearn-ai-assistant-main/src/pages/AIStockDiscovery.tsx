import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { 
  Search, 
  Filter, 
  TrendingUp, 
  TrendingDown,
  BarChart3,
  PieChart,
  Target,
  Zap,
  RefreshCw,
  CheckCircle2,
  X,
  Plus,
  Settings,
  Download,
  Save
} from "lucide-react";
import { apiCall } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface Stock {
  ticker: string;
  sector: string;
  composite_score: number;
  overall_rank: number;
  sector_rank: number;
  factor_scores: {
    valuation: number;
    fundamentals: number;
    sentiment: number;
    momentum: number;
    risk: number;
  };
  current_price: number;
  return_3m: number;
  sentiment_score: number;
  news_count: number;
}

interface PortfolioAnalysis {
  weights: Record<string, number>;
  analysis: {
    expected_return: number;
    volatility: number;
    sharpe_ratio: number;
    num_holdings: number;
    sector_allocation: Record<string, number>;
    top_holdings: Array<{ ticker: string; weight: number }>;
  };
  stocks: Stock[];
}

export default function AIStockDiscovery() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("discovery");
  const [allStocks, setAllStocks] = useState<Stock[]>([]);
  const [displayStocks, setDisplayStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [selectedStocks, setSelectedStocks] = useState<Set<string>>(new Set());
  const [portfolioAnalysis, setPortfolioAnalysis] = useState<PortfolioAnalysis | null>(null);
  const [optimizing, setOptimizing] = useState(false);
  
  // Filter inputs - use refs for text inputs to avoid stale closure issues
  const tickerRef = useRef<HTMLInputElement>(null);
  const minScoreRef = useRef<HTMLInputElement>(null);
  const maxScoreRef = useRef<HTMLInputElement>(null);
  const [sectorFilter, setSectorFilter] = useState("all");
  const [sortBy, setSortBy] = useState("composite_score");
  const [filtersActive, setFiltersActive] = useState(false);
  // Store refs for select values too (selects are controlled but we read via ref pattern)
  const sectorRef = useRef("all");
  const sortRef = useRef("composite_score");

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) navigate("/");
    });
  }, [navigate]);

  useEffect(() => {
    loadResults();
  }, []);

  const loadResults = async () => {
    try {
      setLoading(true);
      const data = await apiCall<{ stocks: Stock[]; sectors: Record<string, any>; stats: any; last_updated: string }>(
        "/api/ai/stock-universe/results?limit=500"
      );
      // Deduplicate by ticker (keep first/highest-scored occurrence)
      const seen = new Set<string>();
      const deduped = data.stocks.filter(s => {
        if (seen.has(s.ticker)) return false;
        seen.add(s.ticker);
        return true;
      });
      setAllStocks(deduped);
      // Show all stocks sorted by score initially
      const sorted = [...deduped].sort((a, b) => b.composite_score - a.composite_score);
      setDisplayStocks(sorted);
    } catch (error: any) {
      if (error.message?.includes("404") || error.message?.includes("410")) {
        console.log("No analysis results available");
      } else {
        console.error("Failed to load results:", error);
      }
      setAllStocks([]);
      setDisplayStocks([]);
    } finally {
      setLoading(false);
    }
  };

  // Read filter values directly from DOM/refs - no stale closures possible
  const doSearch = () => {
    const ticker = tickerRef.current?.value?.trim().toUpperCase() || "";
    const sector = sectorRef.current;
    const minVal = minScoreRef.current?.value?.trim() || "";
    const maxVal = maxScoreRef.current?.value?.trim() || "";
    const sort = sortRef.current;

    console.log("[doSearch] ticker:", ticker, "sector:", sector, "min:", minVal, "max:", maxVal, "sort:", sort, "allStocks:", allStocks.length);

    let results = [...allStocks];

    // 1. Filter by ticker
    if (ticker !== "") {
      results = results.filter(s => s.ticker.toUpperCase().includes(ticker));
    }

    // 2. Filter by sector
    if (sector && sector !== "all") {
      results = results.filter(s => (s.sector || "Other") === sector);
    }

    // 3. Filter by min score
    if (minVal !== "") {
      const min = parseFloat(minVal);
      if (!isNaN(min)) {
        results = results.filter(s => s.composite_score >= min);
      }
    }

    // 4. Filter by max score
    if (maxVal !== "") {
      const max = parseFloat(maxVal);
      if (!isNaN(max)) {
        results = results.filter(s => s.composite_score <= max);
      }
    }

    // 5. Sort
    if (sort === "composite_score") {
      results.sort((a, b) => b.composite_score - a.composite_score);
    } else if (sort === "ticker") {
      results.sort((a, b) => a.ticker.localeCompare(b.ticker));
    } else if (sort === "sector") {
      results.sort((a, b) => {
        const cmp = (a.sector || "").localeCompare(b.sector || "");
        return cmp !== 0 ? cmp : b.composite_score - a.composite_score;
      });
    } else if (sort === "return_3m") {
      results.sort((a, b) => (b.return_3m || 0) - (a.return_3m || 0));
    } else if (sort === "sentiment") {
      results.sort((a, b) => (b.sentiment_score || 0) - (a.sentiment_score || 0));
    }

    console.log("[doSearch] results:", results.length, results.slice(0, 3).map(s => s.ticker));
    setDisplayStocks(results);
    setFiltersActive(ticker !== "" || (sector && sector !== "all") || minVal !== "" || maxVal !== "");
  };

  const clearFilters = () => {
    if (tickerRef.current) tickerRef.current.value = "";
    if (minScoreRef.current) minScoreRef.current.value = "";
    if (maxScoreRef.current) maxScoreRef.current.value = "";
    setSectorFilter("all");
    sectorRef.current = "all";
    setSortBy("composite_score");
    sortRef.current = "composite_score";
    setFiltersActive(false);
    const sorted = [...allStocks].sort((a, b) => b.composite_score - a.composite_score);
    setDisplayStocks(sorted);
  };

  const startAnalysis = async () => {
    try {
      setAnalyzing(true);
      setAnalysisProgress(0);
      
      const response = await apiCall<{ job_id: string; estimated_time_minutes: number; message: string }>(
        "/api/ai/stock-universe/analyze",
        {
          method: "POST",
          body: JSON.stringify({ tickers: null }),
        }
      );

      const pollInterval = setInterval(async () => {
        try {
          const status = await apiCall<{
            status: string;
            progress: number;
            current_ticker: string | null;
            completed: number;
            total: number;
            results: any;
            error: string | null;
          }>(`/api/ai/stock-universe/status/${response.job_id}`);

          setAnalysisProgress(status.progress);

          if (status.status === "completed") {
            clearInterval(pollInterval);
            setAnalyzing(false);
            setAnalysisProgress(100);
            await loadResults();
          } else if (status.status === "failed") {
            clearInterval(pollInterval);
            setAnalyzing(false);
            alert(`Analysis failed: ${status.error}`);
          }
        } catch (error) {
          console.error("Error polling status:", error);
        }
      }, 2000);
    } catch (error) {
      console.error("Failed to start analysis:", error);
      setAnalyzing(false);
      alert("Failed to start analysis. Make sure backend is running.");
    }
  };

  const toggleStockSelection = (ticker: string) => {
    const newSelected = new Set(selectedStocks);
    if (newSelected.has(ticker)) {
      newSelected.delete(ticker);
    } else {
      newSelected.add(ticker);
    }
    setSelectedStocks(newSelected);
  };

  const selectTopStocks = (count: number) => {
    const top = displayStocks.slice(0, count).map(s => s.ticker);
    setSelectedStocks(new Set(top));
    setActiveTab("portfolio");
  };

  const optimizePortfolio = async () => {
    if (selectedStocks.size === 0) {
      alert("Please select at least one stock");
      return;
    }

    try {
      setOptimizing(true);
      const tickers = Array.from(selectedStocks);
      
      const analysis = await apiCall<PortfolioAnalysis>(
        "/api/ai/asset-allocation/optimize",
        {
          method: "POST",
          body: JSON.stringify({
            tickers,
            objective: "sharpe",
            constraints: {
              max_weight: 0.25,
              min_weight: 0.0
            }
          }),
        }
      );

      setPortfolioAnalysis(analysis);
    } catch (error) {
      console.error("Failed to optimize portfolio:", error);
      alert("Failed to optimize portfolio");
    } finally {
      setOptimizing(false);
    }
  };

  const sectors = Array.from(new Set(allStocks.map(s => s.sector || "Other"))).sort();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">AI Stock Discovery & Portfolio Builder</h1>
          <p className="text-slate-300">
            Deep analysis of S&P 500 stocks with sector-normalized scoring. Build your custom index.
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="discovery">Discovery</TabsTrigger>
            <TabsTrigger value="portfolio">Portfolio Builder</TabsTrigger>
            <TabsTrigger value="saved">Saved Indices</TabsTrigger>
          </TabsList>

          <TabsContent value="discovery" className="space-y-4">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>S&P 500 Stock Analysis</CardTitle>
                    <CardDescription>
                      {allStocks.length > 0 
                        ? "Select stocks to build your portfolio."
                        : "No analysis results available. Run analysis to get started."}
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={startAnalysis} disabled={analyzing} variant="outline">
                      {analyzing ? (
                        <>
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                          Analyzing... {analysisProgress}%
                        </>
                      ) : (
                        <>
                          <Zap className="mr-2 h-4 w-4" />
                          Run Analysis
                        </>
                      )}
                    </Button>
                    <Button onClick={loadResults} variant="outline">
                      <RefreshCw className="mr-2 h-4 w-4" />
                      Refresh
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {analyzing && (
                  <div className="mb-4">
                    <Progress value={analysisProgress} className="mb-2" />
                    <p className="text-sm text-slate-400">Analyzing S&P 500 stocks... This may take 15-20 minutes.</p>
                  </div>
                )}

                {allStocks.length === 0 && !analyzing && (
                  <div className="text-center py-12">
                    <BarChart3 className="mx-auto h-12 w-12 text-slate-500 mb-4" />
                    <p className="text-slate-400 mb-4">No analysis results available.</p>
                    <Button onClick={startAnalysis}>
                      <Zap className="mr-2 h-4 w-4" />
                      Start S&P 500 Analysis
                    </Button>
                  </div>
                )}

                {allStocks.length > 0 && (
                  <>
                    {/* Filter bar */}
                    <div className="flex flex-wrap items-center gap-3 mb-4">
                      <Input
                        ref={tickerRef}
                        placeholder="Ticker (e.g. AAPL)"
                        defaultValue=""
                        onKeyDown={(e) => { if (e.key === "Enter") doSearch(); }}
                        className="bg-slate-700 border-slate-600 w-40"
                      />
                      <Select value={sectorFilter} onValueChange={(val) => { setSectorFilter(val); sectorRef.current = val; }}>
                        <SelectTrigger className="bg-slate-700 border-slate-600 w-44">
                          <SelectValue placeholder="All Sectors" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Sectors</SelectItem>
                          {sectors.map(sector => (
                            <SelectItem key={sector} value={sector}>{sector}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Input
                        ref={minScoreRef}
                        type="number"
                        placeholder="Min Score"
                        defaultValue=""
                        onKeyDown={(e) => { if (e.key === "Enter") doSearch(); }}
                        className="bg-slate-700 border-slate-600 w-28"
                      />
                      <Input
                        ref={maxScoreRef}
                        type="number"
                        placeholder="Max Score"
                        defaultValue=""
                        onKeyDown={(e) => { if (e.key === "Enter") doSearch(); }}
                        className="bg-slate-700 border-slate-600 w-28"
                      />
                      <Select value={sortBy} onValueChange={(val) => { setSortBy(val); sortRef.current = val; }}>
                        <SelectTrigger className="bg-slate-700 border-slate-600 w-48">
                          <SelectValue placeholder="Sort by" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="composite_score">Score (High to Low)</SelectItem>
                          <SelectItem value="ticker">Ticker (A-Z)</SelectItem>
                          <SelectItem value="sector">Sector</SelectItem>
                          <SelectItem value="return_3m">3M Return (High to Low)</SelectItem>
                          <SelectItem value="sentiment">Sentiment (High to Low)</SelectItem>
                        </SelectContent>
                      </Select>
                      <Button onClick={doSearch} className="bg-purple-600 hover:bg-purple-700">
                        <Search className="mr-2 h-4 w-4" />
                        Search
                      </Button>
                      {filtersActive && (
                        <Button onClick={clearFilters} variant="outline" size="sm">
                          <X className="mr-2 h-4 w-4" />
                          Clear
                        </Button>
                      )}
                    </div>

                    <div className="flex gap-2 mb-4">
                      <Button onClick={() => selectTopStocks(10)} variant="outline" size="sm">
                        Select Top 10
                      </Button>
                      <Button onClick={() => selectTopStocks(20)} variant="outline" size="sm">
                        Select Top 20
                      </Button>
                      <Button onClick={() => selectTopStocks(50)} variant="outline" size="sm">
                        Select Top 50
                      </Button>
                    </div>

                    <div className="space-y-2 max-h-[600px] overflow-y-auto">
                      {displayStocks.length === 0 ? (
                        <div className="text-center py-8 text-slate-400">
                          No stocks match your filters. Try adjusting your search criteria.
                        </div>
                      ) : (
                        displayStocks.map((stock) => (
                          <Card
                            key={stock.ticker}
                            className={`bg-slate-700/50 border-slate-600 cursor-pointer hover:bg-slate-700 transition-colors ${
                              selectedStocks.has(stock.ticker) ? "ring-2 ring-purple-500" : ""
                            }`}
                            onClick={() => toggleStockSelection(stock.ticker)}
                          >
                            <CardContent className="p-4">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-4 flex-1">
                                  <div className="flex items-center gap-2">
                                    {selectedStocks.has(stock.ticker) ? (
                                      <CheckCircle2 className="h-5 w-5 text-purple-400" />
                                    ) : (
                                      <div className="h-5 w-5 border-2 border-slate-500 rounded" />
                                    )}
                                    <span className="font-bold text-lg">{stock.ticker}</span>
                                  </div>
                                  <Badge variant="outline">{stock.sector}</Badge>
                                  <div className="flex items-center gap-1">
                                    <span className="text-2xl font-bold text-purple-400">
                                      {stock.composite_score.toFixed(1)}
                                    </span>
                                    <span className="text-sm text-slate-400">/100</span>
                                  </div>
                                  <div className="text-sm text-slate-400">
                                    Rank: #{stock.overall_rank} ({stock.sector_rank} in {stock.sector})
                                  </div>
                                </div>
                                <div className="flex items-center gap-6">
                                  <div className="text-right">
                                    <div className="text-sm text-slate-400">3M Return</div>
                                    <div className={`font-semibold ${stock.return_3m >= 0 ? "text-green-400" : "text-red-400"}`}>
                                      {stock.return_3m >= 0 ? "+" : ""}{stock.return_3m.toFixed(1)}%
                                    </div>
                                  </div>
                                  <div className="text-right">
                                    <div className="text-sm text-slate-400">Sentiment</div>
                                    <div className="font-semibold">
                                      {stock.sentiment_score >= 0 ? "+" : ""}{stock.sentiment_score.toFixed(2)}
                                    </div>
                                  </div>
                                </div>
                              </div>
                              <div className="mt-3 flex gap-4 text-xs">
                                <div>Valuation: {stock.factor_scores.valuation.toFixed(1)}</div>
                                <div>Fundamentals: {stock.factor_scores.fundamentals.toFixed(1)}</div>
                                <div>Sentiment: {stock.factor_scores.sentiment.toFixed(1)}</div>
                                <div>Momentum: {stock.factor_scores.momentum.toFixed(1)}</div>
                                <div>Risk: {stock.factor_scores.risk.toFixed(1)}</div>
                              </div>
                            </CardContent>
                          </Card>
                        ))
                      )}
                    </div>
                    <div className="text-sm text-slate-400 mt-2 text-center">
                      Showing {displayStocks.length} of {allStocks.length} stocks
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="portfolio" className="space-y-4">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle>Portfolio Builder</CardTitle>
                <CardDescription>
                  {selectedStocks.size > 0
                    ? `${selectedStocks.size} stocks selected. Optimize allocation or adjust manually.`
                    : "Select stocks from Discovery tab to build your portfolio."}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {selectedStocks.size === 0 ? (
                  <div className="text-center py-12">
                    <Target className="mx-auto h-12 w-12 text-slate-500 mb-4" />
                    <p className="text-slate-400 mb-4">No stocks selected.</p>
                    <Button onClick={() => setActiveTab("discovery")} variant="outline">
                      Go to Discovery
                    </Button>
                  </div>
                ) : (
                  <>
                    <div className="mb-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-semibold">Selected Stocks ({selectedStocks.size})</h3>
                        <Button onClick={optimizePortfolio} disabled={optimizing}>
                          {optimizing ? (
                            <>
                              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                              Optimizing...
                            </>
                          ) : (
                            <>
                              <Zap className="mr-2 h-4 w-4" />
                              Optimize Portfolio
                            </>
                          )}
                        </Button>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {Array.from(selectedStocks).map(ticker => {
                          const stock = allStocks.find(s => s.ticker === ticker);
                          return (
                            <Badge key={ticker} variant="secondary" className="text-sm py-1 px-3">
                              {ticker}
                              {stock && ` (${stock.composite_score.toFixed(1)})`}
                              <X
                                className="ml-2 h-3 w-3 cursor-pointer"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleStockSelection(ticker);
                                }}
                              />
                            </Badge>
                          );
                        })}
                      </div>
                    </div>

                    {portfolioAnalysis && (
                      <div className="space-y-4">
                        <Card className="bg-slate-700/50 border-slate-600">
                          <CardHeader>
                            <CardTitle>Portfolio Analysis</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                              <div>
                                <div className="text-sm text-slate-400">Expected Return</div>
                                <div className="text-2xl font-bold text-green-400">
                                  {portfolioAnalysis.analysis.expected_return.toFixed(2)}%
                                </div>
                              </div>
                              <div>
                                <div className="text-sm text-slate-400">Volatility (Risk)</div>
                                <div className="text-2xl font-bold text-yellow-400">
                                  {portfolioAnalysis.analysis.volatility.toFixed(2)}%
                                </div>
                              </div>
                              <div>
                                <div className="text-sm text-slate-400">Sharpe Ratio</div>
                                <div className="text-2xl font-bold text-purple-400">
                                  {portfolioAnalysis.analysis.sharpe_ratio.toFixed(3)}
                                </div>
                              </div>
                              <div>
                                <div className="text-sm text-slate-400">Holdings</div>
                                <div className="text-2xl font-bold">
                                  {portfolioAnalysis.analysis.num_holdings}
                                </div>
                              </div>
                            </div>

                            <div className="mb-4">
                              <h4 className="font-semibold mb-2">Sector Allocation</h4>
                              <div className="space-y-2">
                                {Object.entries(portfolioAnalysis.analysis.sector_allocation).map(([sector, weight]) => (
                                  <div key={sector} className="flex items-center justify-between">
                                    <span className="text-sm">{sector}</span>
                                    <div className="flex items-center gap-2">
                                      <div className="w-32 bg-slate-600 rounded-full h-2">
                                        <div
                                          className="bg-purple-500 h-2 rounded-full"
                                          style={{ width: `${weight}%` }}
                                        />
                                      </div>
                                      <span className="text-sm font-semibold w-12 text-right">{weight.toFixed(1)}%</span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>

                            <div>
                              <h4 className="font-semibold mb-2">Top Holdings</h4>
                              <div className="space-y-2">
                                {portfolioAnalysis.analysis.top_holdings.map((holding, idx) => (
                                  <div key={holding.ticker} className="flex items-center justify-between">
                                    <span className="text-sm">
                                      {idx + 1}. {holding.ticker}
                                    </span>
                                    <span className="text-sm font-semibold">{holding.weight.toFixed(2)}%</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="saved">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle>Saved Indices</CardTitle>
                <CardDescription>Your custom portfolio indices</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <Save className="mx-auto h-12 w-12 text-slate-500 mb-4" />
                  <p className="text-slate-400">Save functionality coming soon</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
