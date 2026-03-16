import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { HeroSection } from "@/components/HeroSection";
import { LessonGrid } from "@/components/LessonGrid";
import { ChatPanel } from "@/components/ChatPanel";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LogOut, TrendingUp, BarChart3, Eye, LineChart, Brain, Trophy, Users, PieChart, Zap, Target, Info, ArrowRight, Wallet, Download, MessageCircle } from "lucide-react";

function StepRow({ step, label, desc, onGo, icon }: { step: number; label: string; desc: string; onGo?: () => void; icon?: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border/50 bg-background/50 p-3">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/20 text-sm font-medium text-primary">
        {step}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-foreground">{label}</span>
          {onGo && (
            <button
              type="button"
              onClick={onGo}
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              Go <ArrowRight className="w-3 h-3" />
            </button>
          )}
          {icon && <span className="text-muted-foreground">{icon}</span>}
        </div>
        <p className="text-sm text-muted-foreground mt-0.5">{desc}</p>
      </div>
    </div>
  );
}

const ETF_ALLOCATION_KEY = "dashboard.lastEtfAllocation";

interface SavedEtfAllocation {
  profile: string;
  risk_score: number;
  allocation: Record<string, number>;
  metrics: { expected_return: number; volatility: number; sharpe_ratio: number; num_holdings: number };
  etf_details: Record<string, { name: string }>;
  savedAt: string;
}

function parseSavedAllocation(): SavedEtfAllocation | null {
  try {
    const raw = sessionStorage.getItem(ETF_ALLOCATION_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as SavedEtfAllocation;
    return data?.allocation && data?.metrics ? data : null;
  } catch {
    return null;
  }
}

const Dashboard = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [userEmail, setUserEmail] = useState("");
  const [selectedGoal, setSelectedGoal] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem("dashboard.selectedGoal");
    } catch {
      return null;
    }
  });
  const [savedAllocation, setSavedAllocation] = useState<SavedEtfAllocation | null>(parseSavedAllocation);

  useEffect(() => {
    if (selectedGoal) {
      try {
        sessionStorage.setItem("dashboard.selectedGoal", selectedGoal);
      } catch {
        // ignore
      }
    }
  }, [selectedGoal]);

  // Re-read saved ETF allocation when viewing dashboard (so we show latest after returning from ETF Allocator)
  useEffect(() => {
    if (location.pathname === "/dashboard") {
      setSavedAllocation(parseSavedAllocation());
    }
  }, [location.pathname]);

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (!session) {
        navigate("/");
      } else {
        setUserEmail(session.user.email || "");
      }
    });

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        navigate("/");
      } else {
        setUserEmail(session.user.email || "");
      }
    });

    return () => subscription.unsubscribe();
  }, [navigate]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate("/");
  };

  return (
    <div className="flex min-h-screen">
      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Top Bar */}
        <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-md">
          <div className="max-w-6xl mx-auto px-6 lg:px-12 h-14 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <TrendingUp className="w-4 h-4 text-primary" />
              </div>
              <span className="font-display text-sm font-semibold">FinLearn AI</span>
            </div>
            <div className="flex items-center gap-4">
              {/* Social & Leaderboard Links */}
              <button
                onClick={() => navigate("/leaderboard")}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors"
                title="Leaderboard"
              >
                <Trophy className="w-4 h-4" />
                <span className="hidden md:inline">Leaderboard</span>
              </button>
              <button
                onClick={() => navigate("/social")}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors"
                title="Community"
              >
                <Users className="w-4 h-4" />
                <span className="hidden md:inline">Community</span>
              </button>
              <button
                onClick={() => navigate("/messages")}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors"
                title="Messages"
              >
                <MessageCircle className="w-4 h-4" />
                <span className="hidden md:inline">Messages</span>
              </button>
              <div className="h-4 w-px bg-border hidden sm:block" />
              <span className="text-xs text-muted-foreground hidden sm:block">{userEmail}</span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign out
              </button>
            </div>
          </div>
        </header>

        <div className="max-w-6xl mx-auto px-6 lg:px-12 pb-16">
          <HeroSection />

          {/* Learning Modules Section */}
          <LessonGrid />
          
          {/* How to use FinLearn after modules — main goal path */}
          <Alert className="mb-6 mt-8 border-primary/30 bg-primary/5">
            <Info className="h-4 w-4 text-primary" />
            <AlertTitle className="text-base">How to turn learning into action</AlertTitle>
            <AlertDescription className="mt-1 text-sm text-muted-foreground">
              After the modules, use the tools in order:{" "}
              <strong className="text-foreground">Portfolio Simulator</strong> → see how much you need to save and for how long;{" "}
              <strong className="text-foreground">Smart ETF Allocator</strong> → get a personalised portfolio based on your risk and goals;{" "}
              then track your plan with a <strong className="text-foreground">virtual portfolio</strong> (no real money). Pick a goal below to see your path.
            </AlertDescription>
          </Alert>

          {/* Your investing path — goals-based flow (below Learning Modules) */}
          <section className="py-8">
            <h2 className="font-display text-2xl font-bold mb-2 flex items-center gap-2">
              <Target className="w-6 h-6 text-primary" />
              Your investing path
            </h2>
            <p className="text-muted-foreground mb-6">
              Choose a goal to see which tools to use and in what order. This keeps you focused on one main outcome.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {[
                { id: "house", label: "Save for a house", years: "~5 years", horizon: 5 },
                { id: "retirement", label: "Retirement", years: "15–30 years", horizon: 20 },
                { id: "wealth", label: "Build long-term wealth", years: "10+ years", horizon: 15 },
                { id: "learning", label: "Just learning", years: "Exploring", horizon: null },
              ].map((goal) => (
                <Card
                  key={goal.id}
                  className={`cursor-pointer transition-all hover:border-primary/50 hover:shadow-md ${selectedGoal === goal.id ? "border-primary/50 ring-1 ring-primary/20" : ""}`}
                  onClick={() => setSelectedGoal(goal.id)}
                >
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">{goal.label}</CardTitle>
                    <CardDescription>{goal.years}</CardDescription>
                  </CardHeader>
                </Card>
              ))}
            </div>
            {selectedGoal && (
              <Card className="border-primary/20 bg-muted/30">
                <CardHeader>
                  <CardTitle className="text-lg">Use these tools in order</CardTitle>
                  <CardDescription>
                    {selectedGoal === "house" && "Short horizon: focus on Simulator + ETF Allocator, then track with a virtual portfolio."}
                    {selectedGoal === "retirement" && "Long horizon: Simulator for savings targets, ETF Allocator for allocation, Monte Carlo for outcome ranges."}
                    {selectedGoal === "wealth" && "Simulator to set contributions, ETF Allocator for a risk-matched portfolio, then monitor with a virtual portfolio."}
                    {selectedGoal === "learning" && "Start with the Simulator to see compound growth, then try the ETF Allocator to see how risk affects your portfolio."}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <StepRow step={1} label="Portfolio Simulator" desc="Set your horizon and monthly contribution; see how much you could have." onGo={() => navigate("/simulator")} />
                  <StepRow step={2} label="Smart ETF Allocator" desc="Answer the quiz; get a personalised ETF mix and optional Monte Carlo outcomes." onGo={() => navigate("/etf-allocator")} />
                  {/* Step 3: show saved portfolio from ETF Allocator or "coming soon" */}
                  <div className="flex items-start gap-3 rounded-lg border border-border/50 bg-background/50 p-3">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/20 text-sm font-medium text-primary">
                      3
                    </span>
                    <div className="flex-1 min-w-0">
                      {savedAllocation ? (
                        <>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-foreground">Your optimized portfolio</span>
                            <span className="text-xs text-muted-foreground">
                              {savedAllocation.profile} · {savedAllocation.metrics.num_holdings} ETFs · E[R] {savedAllocation.metrics.expected_return}%
                            </span>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">
                            From Smart ETF Allocator. Download to keep or share. Virtual tracking coming soon.
                          </p>
                          <div className="flex flex-wrap gap-2 mt-3">
                            <button
                              type="button"
                              onClick={() => {
                                const blob = new Blob([JSON.stringify(savedAllocation, null, 2)], { type: "application/json" });
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement("a");
                                a.href = url;
                                a.download = `finlearn-etf-allocation-${savedAllocation.savedAt.slice(0, 10)}.json`;
                                a.click();
                                URL.revokeObjectURL(url);
                              }}
                              className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md bg-primary/15 text-primary hover:bg-primary/25"
                            >
                              <Download className="w-3.5 h-3.5" />
                              Download JSON
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                const headers = "ETF,Weight %,Name\n";
                                const rows = Object.entries(savedAllocation.allocation)
                                  .map(([etf, w]) => `${etf},${w},${(savedAllocation.etf_details && savedAllocation.etf_details[etf]?.name) || etf}`)
                                  .join("\n");
                                const blob = new Blob([headers + rows], { type: "text/csv" });
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement("a");
                                a.href = url;
                                a.download = `finlearn-etf-allocation-${savedAllocation.savedAt.slice(0, 10)}.csv`;
                                a.click();
                                URL.revokeObjectURL(url);
                              }}
                              className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md bg-muted text-muted-foreground hover:bg-muted/80"
                            >
                              <Download className="w-3.5 h-3.5" />
                              Download CSV
                            </button>
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-foreground">Virtual portfolio (coming soon)</span>
                            <Wallet className="w-4 h-4 text-muted-foreground" />
                          </div>
                          <p className="text-sm text-muted-foreground mt-0.5">
                            Track your chosen allocation with real prices—no real money. Run the ETF Allocator first to see your portfolio here.
                          </p>
                        </>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </section>
          
          {/* AI Tools Section - Now below */}
          <section className="py-8">
            <h2 className="font-display text-2xl font-bold mb-2">AI Tools</h2>
            <p className="text-muted-foreground mb-2">Powerful analysis tools powered by machine learning.</p>
            <p className="text-sm text-muted-foreground mb-6">
              For your main goal (e.g. retirement or a house), start with <strong>Simulator</strong> and <strong>ETF Allocator</strong> (first row). Use <strong>Stock Screener</strong> and <strong>AI Stock Discovery</strong> when you want to explore individual stocks or build a custom index.
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Row 1: Simulator, ETF Allocator */}
              <button
                onClick={() => navigate("/simulator")}
                className="glass-card rounded-xl p-6 text-left hover:border-primary/40 transition-all group"
              >
                <div className="p-2.5 rounded-lg bg-primary/10 text-primary w-fit mb-4 group-hover:glow-gold transition-all">
                  <LineChart className="w-5 h-5" />
                </div>
                <h3 className="font-display text-lg font-semibold mb-2 group-hover:text-primary transition-colors">
                  Portfolio Simulator
                </h3>
                <p className="text-sm text-muted-foreground">
                  See how your investments grow over time
                </p>
              </button>

              <button
                onClick={() => navigate("/etf-allocator")}
                className="glass-card rounded-xl p-6 text-left hover:border-green-400/40 transition-all group"
              >
                <div className="p-2.5 rounded-lg bg-green-500/10 text-green-400 w-fit mb-4 group-hover:shadow-lg group-hover:shadow-green-500/20 transition-all">
                  <PieChart className="w-5 h-5" />
                </div>
                <h3 className="font-display text-lg font-semibold mb-2 group-hover:text-green-400 transition-colors">
                  Smart ETF Allocator
                </h3>
                <p className="text-sm text-muted-foreground">
                  GA-optimised ETF portfolios with thematic constraints and Monte Carlo simulation
                </p>
              </button>

              {/* Row 2: Stock Screener, Chart Analyzer */}
              <button
                onClick={() => navigate("/screener")}
                className="glass-card rounded-xl p-6 text-left hover:border-primary/40 transition-all group"
              >
                <div className="p-2.5 rounded-lg bg-primary/10 text-primary w-fit mb-4 group-hover:glow-gold transition-all">
                  <BarChart3 className="w-5 h-5" />
                </div>
                <h3 className="font-display text-lg font-semibold mb-2 group-hover:text-primary transition-colors">
                  Stock Screener
                </h3>
                <p className="text-sm text-muted-foreground">
                  Real-time AI analysis with BUY/HOLD/SELL signals
                </p>
              </button>

              <button
                onClick={() => navigate("/analyzer")}
                className="glass-card rounded-xl p-6 text-left hover:border-primary/40 transition-all group"
              >
                <div className="p-2.5 rounded-lg bg-primary/10 text-primary w-fit mb-4 group-hover:glow-gold transition-all">
                  <Eye className="w-5 h-5" />
                </div>
                <h3 className="font-display text-lg font-semibold mb-2 group-hover:text-primary transition-colors">
                  Chart Analyzer
                </h3>
                <p className="text-sm text-muted-foreground">
                  Upload charts to detect S/R levels and trends
                </p>
              </button>

              {/* Row 3: Sentiment, AI Stock Discovery */}
              <button
                onClick={() => navigate("/sentiment")}
                className="glass-card rounded-xl p-6 text-left hover:border-purple-400/40 transition-all group"
              >
                <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-400 w-fit mb-4 group-hover:shadow-lg group-hover:shadow-purple-500/20 transition-all">
                  <Brain className="w-5 h-5" />
                </div>
                <h3 className="font-display text-lg font-semibold mb-2 group-hover:text-purple-400 transition-colors">
                  Sentiment Analyzer
                </h3>
                <p className="text-sm text-muted-foreground">
                  AI-powered news sentiment analysis with FinBERT
                </p>
              </button>

              <button
                onClick={() => navigate("/ai-discovery")}
                className="glass-card rounded-xl p-6 text-left hover:border-purple-400/40 transition-all group"
              >
                <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-400 w-fit mb-4 group-hover:shadow-lg group-hover:shadow-purple-500/20 transition-all">
                  <Zap className="w-5 h-5" />
                </div>
                <h3 className="font-display text-lg font-semibold mb-2 group-hover:text-purple-400 transition-colors">
                  AI Stock Discovery
                </h3>
                <p className="text-sm text-muted-foreground">
                  Deep S&P 500 analysis with sector-normalized scoring. Build custom indices.
                </p>
              </button>
            </div>
          </section>
        </div>
      </div>

      {/* AI Chat Panel - collapsed by default on dashboard */}
      <div className="hidden md:flex w-[380px] flex-shrink-0 h-screen sticky top-0">
        <ChatPanel defaultOpen={false} />
      </div>

      {/* Mobile chat toggle */}
      <div className="md:hidden">
        <ChatPanel defaultOpen={false} />
      </div>
    </div>
  );
};

export default Dashboard;
