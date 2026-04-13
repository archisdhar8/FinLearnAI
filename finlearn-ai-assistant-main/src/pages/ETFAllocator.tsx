import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { apiCall, API_URL } from "@/lib/api";
import {
  ArrowLeft,
  TrendingUp,
  Shield,
  Target,
  Zap,
  PieChart,
  Play,
  RefreshCw,
  Info,
  ChevronRight,
  DollarSign,
  Calendar,
  BarChart3,
  Loader2,
} from "lucide-react";

// ── Quiz questions ──────────────────────────────────────────────────────────

const QUIZ_QUESTIONS = [
  {
    id: 1,
    question: "What is your investment time horizon?",
    key: "time_horizon_years",
    options: [
      { text: "Less than 3 years", value: 2 },
      { text: "3-5 years", value: 4 },
      { text: "5-10 years", value: 7 },
      { text: "10-20 years", value: 15 },
      { text: "20+ years", value: 25 },
    ],
  },
  {
    id: 2,
    question: "If your portfolio dropped 20% in a month, you would:",
    key: "drawdown_tolerance",
    options: [
      { text: "Sell everything immediately", value: 1 },
      { text: "Sell some to reduce risk", value: 2 },
      { text: "Hold and wait it out", value: 3 },
      { text: "Buy a little more", value: 4 },
      { text: "Buy aggressively — great opportunity!", value: 5 },
    ],
  },
  {
    id: 3,
    question: "What is your primary investment goal?",
    key: "primary_goal",
    options: [
      { text: "Preserve my capital at all costs", value: "capital_preservation" },
      { text: "Generate steady income", value: "income" },
      { text: "Balanced growth and income", value: "balanced" },
      { text: "Long-term growth", value: "growth" },
      { text: "Maximum growth, I can handle volatility", value: "max_growth" },
    ],
  },
  {
    id: 4,
    question: "How would you rate your risk tolerance?",
    key: "risk_tolerance",
    options: [
      { text: "Very low — I prefer safety over returns", value: 1 },
      { text: "Low — small losses make me uncomfortable", value: 2 },
      { text: "Moderate — I accept some ups and downs", value: 3 },
      { text: "High — I'm comfortable with volatility", value: 4 },
      { text: "Very high — I chase the highest returns", value: 5 },
    ],
  },
  {
    id: 5,
    question: "How would you describe your investment knowledge?",
    key: "investment_knowledge",
    options: [
      { text: "Beginner — just starting out", value: 2 },
      { text: "Basic — understand stocks and bonds", value: 3 },
      { text: "Intermediate — familiar with ETFs and diversification", value: 4 },
      { text: "Advanced — understand market cycles and risk", value: 5 },
    ],
  },
  {
    id: 6,
    question: "How stable is your current income?",
    key: "income_stability",
    options: [
      { text: "Very unstable / between jobs", value: 1 },
      { text: "Somewhat unstable", value: 2 },
      { text: "Fairly stable", value: 3 },
      { text: "Very stable salary / pension", value: 4 },
      { text: "Multiple income streams", value: 5 },
    ],
  },
];

// ── Thematic ETF catalogue ──────────────────────────────────────────────────

const THEMATIC_ETFS = [
  { etf: "BOTZ", label: "AI & Robotics", icon: "🤖", ret: 13.5 },
  { etf: "SOXX", label: "Semiconductors", icon: "💻", ret: 18.0 },
  { etf: "ARKK", label: "Innovation", icon: "🚀", ret: 15.0 },
  { etf: "ICLN", label: "Clean Energy", icon: "🌱", ret: 11.0 },
  { etf: "TAN",  label: "Solar", icon: "☀️", ret: 12.0 },
  { etf: "LIT",  label: "EV & Batteries", icon: "🔋", ret: 14.0 },
  { etf: "VHT",  label: "Healthcare", icon: "🏥", ret: 11.5 },
  { etf: "IBB",  label: "Biotech", icon: "🧬", ret: 10.5 },
  { etf: "XLF",  label: "Financials", icon: "🏦", ret: 9.8 },
  { etf: "XLE",  label: "Energy", icon: "⛽", ret: 8.5 },
  { etf: "VNQ",  label: "Real Estate", icon: "🏠", ret: 9.0 },
  { etf: "SCHD", label: "Dividends", icon: "💰", ret: 10.8 },
  { etf: "HACK", label: "Cybersecurity", icon: "🔐", ret: 12.5 },
  { etf: "BLOK", label: "Blockchain", icon: "⛓️", ret: 11.0 },
];

// ── Colour palettes ─────────────────────────────────────────────────────────

const PIE_COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#14b8a6",
  "#a855f7", "#e11d48", "#0ea5e9", "#65a30d", "#d946ef",
];

const BG_COLORS = [
  "bg-blue-500", "bg-green-500", "bg-yellow-500", "bg-red-500",
  "bg-purple-500", "bg-pink-500", "bg-cyan-500", "bg-lime-500",
  "bg-orange-500", "bg-teal-500",
];

// ── Types ───────────────────────────────────────────────────────────────────

interface BackendResult {
  risk_score: number;
  profile: string;
  allocation: Record<string, number>;
  metrics: {
    expected_return: number;
    volatility: number;
    expense_ratio: number;
    sharpe_ratio: number;
    equity_pct: number;
    num_holdings: number;
  };
  etf_details: Record<string, {
    name: string;
    asset_class: string;
    category: string;
    exp_return: number;
    volatility: number;
    expense_ratio: number;
  }>;
  simulation?: {
    years: number[];
    percentile10: number[];
    percentile25: number[];
    median: number[];
    percentile75: number[];
    percentile90: number[];
    final_median: number;
    final_p10: number;
    final_p90: number;
    probability_500k: number;
    probability_1m: number;
  };
}

const PATH_PRESET_KEY = "dashboard.pathPreset";

// ── Component ───────────────────────────────────────────────────────────────

export default function ETFAllocator() {
  const navigate = useNavigate();
  const pathPresetConsumed = useRef(false);

  // Steps: quiz → picking themes → results → simulate
  const [step, setStep] = useState<"quiz" | "themes" | "results" | "simulate">("quiz");
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, any>>({});

  const [thematicPicks, setThematicPicks] = useState<string[]>([]);

  // Backend result
  const [result, setResult] = useState<BackendResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Simulation params
  const [initialInvestment, setInitialInvestment] = useState(10000);
  const [monthlyContribution, setMonthlyContribution] = useState(500);
  const [simYears, setSimYears] = useState(20);
  const [simLoading, setSimLoading] = useState(false);

  // Auth guard
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) navigate("/");
    });
  }, [navigate]);

  // Apply goal-based preset from dashboard "Your investing path" → Go (quiz horizon + Monte Carlo years)
  useEffect(() => {
    if (pathPresetConsumed.current) return;
    try {
      const raw = sessionStorage.getItem(PATH_PRESET_KEY);
      if (!raw) {
        pathPresetConsumed.current = true;
        return;
      }
      const p = JSON.parse(raw) as { simulatorYears?: number; etfTimeHorizon?: number };
      if (p.etfTimeHorizon != null) {
        setQuizAnswers({ time_horizon_years: p.etfTimeHorizon });
        setCurrentQuestion(1);
      }
      if (p.simulatorYears != null) {
        const y = Math.min(40, Math.max(1, Math.round(Number(p.simulatorYears))));
        setSimYears(y);
      }
      pathPresetConsumed.current = true;
      sessionStorage.removeItem(PATH_PRESET_KEY);
    } catch {
      pathPresetConsumed.current = true;
    }
  }, []);

  // ── Quiz handlers ───────────────────────────────────────────────────────

  const handleAnswer = (value: any) => {
    const q = QUIZ_QUESTIONS[currentQuestion];
    const updated = { ...quizAnswers, [q.key]: value };
    setQuizAnswers(updated);

    if (currentQuestion < QUIZ_QUESTIONS.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else {
      // Quiz done → move to theme selection
      setStep("themes");
    }
  };

  // ── Theme toggle ────────────────────────────────────────────────────────

  const toggleThematic = (etf: string) => {
    if (thematicPicks.includes(etf)) {
      setThematicPicks(thematicPicks.filter((e) => e !== etf));
    } else if (thematicPicks.length < 4) {
      setThematicPicks([...thematicPicks, etf]);
    }
  };

  // ── Call backend GA optimizer ───────────────────────────────────────────

  const runOptimization = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_URL}/api/etf/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answers: quizAnswers,
          required_etfs: thematicPicks.length > 0 ? thematicPicks : null,
        }),
      });
      if (!resp.ok) {
        const body = await resp.text();
        throw new Error(body || resp.statusText);
      }
      const data: BackendResult = await resp.json();
      setResult(data);
      setStep("results");
      try {
        sessionStorage.setItem(
          "dashboard.lastEtfAllocation",
          JSON.stringify({
            profile: data.profile,
            risk_score: data.risk_score,
            allocation: data.allocation,
            metrics: data.metrics,
            etf_details: data.etf_details,
            savedAt: new Date().toISOString(),
          })
        );
      } catch {
        // ignore
      }
    } catch (e: any) {
      setError(e.message || "Failed to optimise portfolio");
    } finally {
      setLoading(false);
    }
  };

  // ── Run Monte Carlo (via backend) ───────────────────────────────────────

  const runSimulation = async () => {
    setSimLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_URL}/api/etf/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answers: quizAnswers,
          required_etfs: thematicPicks.length > 0 ? thematicPicks : null,
          simulate: {
            initial_investment: initialInvestment,
            monthly_contribution: monthlyContribution,
            years: simYears,
          },
        }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const data: BackendResult = await resp.json();
      setResult(data);
      setStep("simulate");
      try {
        sessionStorage.setItem(
          "dashboard.lastEtfAllocation",
          JSON.stringify({
            profile: data.profile,
            risk_score: data.risk_score,
            allocation: data.allocation,
            metrics: data.metrics,
            etf_details: data.etf_details,
            savedAt: new Date().toISOString(),
          })
        );
      } catch {
        // ignore
      }
    } catch (e: any) {
      setError(e.message || "Simulation failed");
    } finally {
      setSimLoading(false);
    }
  };

  // ── Restart ─────────────────────────────────────────────────────────────

  const restart = () => {
    setStep("quiz");
    setCurrentQuestion(0);
    setQuizAnswers({});
    setThematicPicks([]);
    setResult(null);
    setError(null);
  };

  // ── Helpers ─────────────────────────────────────────────────────────────

  const formatCurrency = (value: number) => {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
  };

  const profileColor = (p: string) => {
    switch (p) {
      case "Conservative": return "text-blue-500";
      case "Moderate": return "text-green-500";
      case "Balanced": return "text-yellow-500";
      case "Growth": return "text-orange-500";
      case "Aggressive": return "text-red-500";
      default: return "text-primary";
    }
  };

  const profileIcon = (p: string) => {
    switch (p) {
      case "Conservative": return <Shield className="w-8 h-8 text-blue-500" />;
      case "Moderate": return <Shield className="w-8 h-8 text-green-500" />;
      case "Balanced": return <Target className="w-8 h-8 text-yellow-500" />;
      case "Growth": return <TrendingUp className="w-8 h-8 text-orange-500" />;
      case "Aggressive": return <Zap className="w-8 h-8 text-red-500" />;
      default: return <PieChart className="w-8 h-8 text-primary" />;
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="max-w-4xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate("/dashboard")} className="p-2 rounded-lg hover:bg-muted transition-colors">
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <PieChart className="w-4 h-4 text-primary" />
              </div>
              <span className="font-display text-sm font-semibold">Smart ETF Allocator</span>
              <span className="ml-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-primary/10 text-primary">GA</span>
            </div>
          </div>
          {step !== "quiz" && (
            <button onClick={restart} className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1">
              <RefreshCw className="w-3 h-3" />
              Start Over
            </button>
          )}
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Error banner */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* ─── Quiz Step ─────────────────────────────────────────────── */}
        {step === "quiz" && (
          <div className="max-w-xl mx-auto">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
                <Target className="w-8 h-8 text-primary" />
              </div>
              <h1 className="font-display text-3xl font-bold mb-2">Build Your Optimal Portfolio</h1>
              <p className="text-muted-foreground">
                Answer {QUIZ_QUESTIONS.length} questions. Our genetic algorithm will optimise your allocation.
              </p>
            </div>

            {/* Progress bar */}
            <div className="mb-8">
              <div className="flex justify-between text-sm text-muted-foreground mb-2">
                <span>Question {currentQuestion + 1} of {QUIZ_QUESTIONS.length}</span>
                <span>{Math.round((currentQuestion / QUIZ_QUESTIONS.length) * 100)}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-primary transition-all duration-300" style={{ width: `${(currentQuestion / QUIZ_QUESTIONS.length) * 100}%` }} />
              </div>
            </div>

            {/* Question card */}
            <div className="glass-card rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-6">{QUIZ_QUESTIONS[currentQuestion].question}</h2>
              <div className="space-y-3">
                {QUIZ_QUESTIONS[currentQuestion].options.map((opt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleAnswer(opt.value)}
                    className="w-full text-left p-4 rounded-lg border border-border hover:border-primary hover:bg-primary/5 transition-colors flex items-center justify-between group"
                  >
                    <span>{opt.text}</span>
                    <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ─── Theme Selection Step ──────────────────────────────────── */}
        {step === "themes" && (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
                <Zap className="w-8 h-8 text-primary" />
              </div>
              <h1 className="font-display text-3xl font-bold mb-2">Add Thematic Exposure</h1>
              <p className="text-muted-foreground">
                Optional: select up to 4 themes. The optimizer will integrate them holistically.
              </p>
            </div>

            <div className="glass-card rounded-xl p-6 mb-6">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {THEMATIC_ETFS.map(({ etf, label, icon, ret }) => (
                  <button
                    key={etf}
                    onClick={() => toggleThematic(etf)}
                    disabled={thematicPicks.length >= 4 && !thematicPicks.includes(etf)}
                    className={`p-3 rounded-lg border text-left transition-colors ${
                      thematicPicks.includes(etf)
                        ? "border-primary bg-primary/10"
                        : thematicPicks.length >= 4
                        ? "border-border opacity-50 cursor-not-allowed"
                        : "border-border hover:border-primary/50"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-xs truncate">{label}</div>
                        <div className="text-xs text-muted-foreground">{etf} &bull; {ret}%</div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {thematicPicks.length > 0 && (
                <div className="mt-4 pt-3 border-t border-border text-xs text-muted-foreground">
                  Selected: {thematicPicks.join(", ")} ({thematicPicks.length}/4)
                </div>
              )}
            </div>

            <button
              onClick={runOptimization}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50 text-sm font-semibold"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running Genetic Algorithm...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Optimise My Portfolio
                </>
              )}
            </button>

            <button onClick={() => { setThematicPicks([]); runOptimization(); }} disabled={loading} className="w-full mt-3 text-sm text-muted-foreground hover:text-foreground transition-colors">
              Skip — no themes
            </button>
          </div>
        )}

        {/* ─── Results Step ──────────────────────────────────────────── */}
        {step === "results" && result && (
          <div>
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
                {profileIcon(result.profile)}
              </div>
              <h1 className="font-display text-3xl font-bold mb-2">
                Your Profile: <span className={profileColor(result.profile)}>{result.profile}</span>
              </h1>
              <p className="text-muted-foreground text-sm">
                Risk score: {(result.risk_score * 100).toFixed(0)}% &bull; Optimised by genetic algorithm (120 generations)
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Left: allocation */}
              <div className="glass-card rounded-xl p-6">
                <h2 className="font-display text-lg font-semibold mb-4 flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-primary" />
                  Optimised Portfolio
                </h2>

                {/* Pie chart */}
                <div className="relative w-48 h-48 mx-auto mb-6">
                  <svg viewBox="0 0 100 100" className="transform -rotate-90">
                    {(() => {
                      let angle = 0;
                      return Object.entries(result.allocation).map(([etf, weight], i) => {
                        const sweep = (weight / 100) * 360;
                        const start = angle;
                        angle += sweep;
                        const x1 = 50 + 40 * Math.cos((start * Math.PI) / 180);
                        const y1 = 50 + 40 * Math.sin((start * Math.PI) / 180);
                        const x2 = 50 + 40 * Math.cos(((start + sweep) * Math.PI) / 180);
                        const y2 = 50 + 40 * Math.sin(((start + sweep) * Math.PI) / 180);
                        const large = sweep > 180 ? 1 : 0;
                        return (
                          <path
                            key={etf}
                            d={`M 50 50 L ${x1} ${y1} A 40 40 0 ${large} 1 ${x2} ${y2} Z`}
                            fill={PIE_COLORS[i % PIE_COLORS.length]}
                            className="hover:opacity-80 transition-opacity"
                          />
                        );
                      });
                    })()}
                  </svg>
                </div>

                {/* ETF list */}
                <div className="space-y-2 max-h-[280px] overflow-y-auto">
                  {Object.entries(result.allocation)
                    .sort(([, a], [, b]) => b - a)
                    .map(([etf, weight], i) => {
                      const detail = result.etf_details[etf];
                      return (
                        <div key={etf} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                          <div className={`w-3 h-3 rounded ${BG_COLORS[i % BG_COLORS.length]}`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-semibold text-sm">{etf}</span>
                              <span className="text-xs text-muted-foreground truncate">{detail?.name}</span>
                            </div>
                          </div>
                          <span className="font-semibold text-sm">{weight}%</span>
                        </div>
                      );
                    })}
                </div>

                {/* Metrics */}
                <div className="mt-4 pt-4 border-t border-border grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground">Expected Return</div>
                    <div className="font-semibold text-success text-lg">{result.metrics.expected_return}%</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Volatility</div>
                    <div className="font-semibold text-lg">{result.metrics.volatility}%</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Sharpe Ratio</div>
                    <div className="font-semibold text-lg">{result.metrics.sharpe_ratio}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Expense Ratio</div>
                    <div className="font-semibold text-lg">{result.metrics.expense_ratio}%</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Equity</div>
                    <div className="font-semibold text-lg">{result.metrics.equity_pct}%</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Holdings</div>
                    <div className="font-semibold text-lg">{result.metrics.num_holdings} ETFs</div>
                  </div>
                </div>
              </div>

              {/* Right: simulation panel */}
              <div className="space-y-6">
                <div className="glass-card rounded-xl p-6">
                  <h2 className="font-display text-lg font-semibold mb-4 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-primary" />
                    Monte Carlo Simulation
                  </h2>
                  <p className="text-sm text-muted-foreground mb-4">
                    1,000 simulations using the full covariance matrix — more realistic than simple volatility scaling.
                  </p>

                  <div className="space-y-4">
                    <div>
                      <label className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                        <DollarSign className="w-4 h-4" /> Initial Investment
                      </label>
                      <input
                        type="number"
                        value={initialInvestment}
                        onChange={(e) => setInitialInvestment(Number(e.target.value))}
                        className="w-full px-4 py-2 bg-muted rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>
                    <div>
                      <label className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                        <DollarSign className="w-4 h-4" /> Monthly Contribution
                      </label>
                      <input
                        type="number"
                        value={monthlyContribution}
                        onChange={(e) => setMonthlyContribution(Number(e.target.value))}
                        className="w-full px-4 py-2 bg-muted rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>
                    <div>
                      <label className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                        <Calendar className="w-4 h-4" /> Time Horizon: {simYears} years
                      </label>
                      <input type="range" min="5" max="40" value={simYears} onChange={(e) => setSimYears(Number(e.target.value))} className="w-full" />
                    </div>

                    <button
                      onClick={runSimulation}
                      disabled={simLoading}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
                    >
                      {simLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Simulating...
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4" />
                          Run Simulation
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* How it works */}
                <div className="glass-card rounded-xl p-6">
                  <h2 className="font-display text-base font-semibold mb-3 flex items-center gap-2">
                    <Info className="w-4 h-4 text-muted-foreground" />
                    How It Works
                  </h2>
                  <ul className="text-xs text-muted-foreground space-y-2">
                    <li><strong>Genetic Algorithm</strong> evolves 120 portfolios over 120 generations to maximise risk-adjusted returns.</li>
                    <li><strong>Constraints</strong> — your thematic picks are guaranteed minimum weight and optimised holistically.</li>
                    <li><strong>Covariance</strong> — uses a 25&times;25 correlation matrix (not simplified volatility sums).</li>
                    <li><strong>Fitness</strong> — balances return, risk, expense ratio, equity target, and diversification (HHI).</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ─── Simulation Results Step ───────────────────────────────── */}
        {step === "simulate" && result?.simulation && (
          <div>
            <div className="text-center mb-8">
              <h1 className="font-display text-3xl font-bold mb-2">Monte Carlo Results</h1>
              <p className="text-muted-foreground">1,000 simulated scenarios using the optimised covariance matrix</p>
            </div>

            {/* Summary cards */}
            <div className="grid grid-cols-3 gap-4 mb-8">
              <div className="glass-card rounded-xl p-4 text-center border-l-4 border-red-500">
                <div className="text-sm text-muted-foreground mb-1">Worst Case (10th %ile)</div>
                <div className="text-2xl font-bold text-red-500">{formatCurrency(result.simulation.final_p10)}</div>
              </div>
              <div className="glass-card rounded-xl p-4 text-center border-l-4 border-primary">
                <div className="text-sm text-muted-foreground mb-1">Expected (Median)</div>
                <div className="text-2xl font-bold text-primary">{formatCurrency(result.simulation.final_median)}</div>
              </div>
              <div className="glass-card rounded-xl p-4 text-center border-l-4 border-green-500">
                <div className="text-sm text-muted-foreground mb-1">Best Case (90th %ile)</div>
                <div className="text-2xl font-bold text-green-500">{formatCurrency(result.simulation.final_p90)}</div>
              </div>
            </div>

            {/* Fan chart */}
            <div className="glass-card rounded-xl p-6 mb-8">
              <h2 className="font-display text-lg font-semibold mb-4">Projected Growth Range</h2>
              <div className="relative h-64">
                <div className="absolute left-0 top-0 bottom-8 w-16 flex flex-col justify-between text-xs text-muted-foreground">
                  <span>{formatCurrency(result.simulation.final_p90)}</span>
                  <span>{formatCurrency(result.simulation.final_median)}</span>
                  <span>{formatCurrency(initialInvestment)}</span>
                </div>
                <div className="ml-16 h-full relative">
                  <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
                    {/* 10-90 band */}
                    <polygon
                      points={
                        result.simulation.years.map((_, i) => {
                          const x = (i / (result.simulation!.years.length - 1)) * 100;
                          const maxVal = result.simulation!.percentile90[result.simulation!.percentile90.length - 1];
                          const y = 100 - (result.simulation!.percentile90[i] / maxVal) * 90;
                          return `${x},${y}`;
                        }).join(" ") +
                        " " +
                        [...result.simulation.years].reverse().map((_, i) => {
                          const idx = result.simulation!.years.length - 1 - i;
                          const x = (idx / (result.simulation!.years.length - 1)) * 100;
                          const maxVal = result.simulation!.percentile90[result.simulation!.percentile90.length - 1];
                          const y = 100 - (result.simulation!.percentile10[idx] / maxVal) * 90;
                          return `${x},${y}`;
                        }).join(" ")
                      }
                      fill="rgba(59,130,246,0.1)"
                    />
                    {/* 25-75 band */}
                    <polygon
                      points={
                        result.simulation.years.map((_, i) => {
                          const x = (i / (result.simulation!.years.length - 1)) * 100;
                          const maxVal = result.simulation!.percentile90[result.simulation!.percentile90.length - 1];
                          const y = 100 - (result.simulation!.percentile75[i] / maxVal) * 90;
                          return `${x},${y}`;
                        }).join(" ") +
                        " " +
                        [...result.simulation.years].reverse().map((_, i) => {
                          const idx = result.simulation!.years.length - 1 - i;
                          const x = (idx / (result.simulation!.years.length - 1)) * 100;
                          const maxVal = result.simulation!.percentile90[result.simulation!.percentile90.length - 1];
                          const y = 100 - (result.simulation!.percentile25[idx] / maxVal) * 90;
                          return `${x},${y}`;
                        }).join(" ")
                      }
                      fill="rgba(59,130,246,0.2)"
                    />
                    {/* Median line */}
                    <polyline
                      points={result.simulation.years.map((_, i) => {
                        const x = (i / (result.simulation!.years.length - 1)) * 100;
                        const maxVal = result.simulation!.percentile90[result.simulation!.percentile90.length - 1];
                        const y = 100 - (result.simulation!.median[i] / maxVal) * 90;
                        return `${x},${y}`;
                      }).join(" ")}
                      fill="none"
                      stroke="#3b82f6"
                      strokeWidth="2"
                    />
                  </svg>
                  <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                    <span>Year 0</span>
                    <span>Year {Math.floor(simYears / 2)}</span>
                    <span>Year {simYears}</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-6 justify-center mt-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-blue-500/10 border border-blue-500/30" />
                  <span className="text-muted-foreground">10th-90th percentile</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-blue-500/20 border border-blue-500/50" />
                  <span className="text-muted-foreground">25th-75th percentile</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-1 bg-blue-500 rounded" />
                  <span className="text-muted-foreground">Median</span>
                </div>
              </div>
            </div>

            {/* Probability cards */}
            <div className="grid grid-cols-2 gap-4 mb-8">
              <div className="glass-card rounded-xl p-6 text-center">
                <div className="text-4xl font-bold text-primary mb-2">{result.simulation.probability_500k}%</div>
                <div className="text-muted-foreground">Probability of reaching $500,000</div>
                <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-primary transition-all" style={{ width: `${result.simulation.probability_500k}%` }} />
                </div>
              </div>
              <div className="glass-card rounded-xl p-6 text-center">
                <div className="text-4xl font-bold text-success mb-2">{result.simulation.probability_1m}%</div>
                <div className="text-muted-foreground">Probability of reaching $1,000,000</div>
                <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-success transition-all" style={{ width: `${result.simulation.probability_1m}%` }} />
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-4 justify-center">
              <button onClick={() => setStep("results")} className="px-6 py-3 bg-muted text-foreground rounded-lg hover:bg-muted/80 flex items-center gap-2">
                <ArrowLeft className="w-4 h-4" />
                Adjust Portfolio
              </button>
              <button onClick={runSimulation} disabled={simLoading} className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:opacity-90 flex items-center gap-2 disabled:opacity-50">
                <RefreshCw className="w-4 h-4" />
                Run Again
              </button>
            </div>

            <div className="mt-8 p-4 rounded-lg bg-muted/50 text-center">
              <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                <Info className="w-4 h-4" />
                <span>
                  Simulations use a log-normal model with the full covariance matrix. Past performance does not guarantee future results. This is for educational purposes only.
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
