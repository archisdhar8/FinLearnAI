import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import {
  ArrowLeft,
  TrendingUp,
  DollarSign,
  Calendar,
  PieChart,
  Play,
  RefreshCw,
} from "lucide-react";

interface SimulationResult {
  years: number[];
  portfolio: number[];
  contributions: number[];
  finalValue: number;
  totalContributed: number;
  totalGrowth: number;
}

const PATH_PRESET_KEY = "dashboard.pathPreset";

export default function Simulator() {
  const navigate = useNavigate();
  const presetConsumed = useRef(false);
  const [initialInvestment, setInitialInvestment] = useState(10000);
  const [monthlyContribution, setMonthlyContribution] = useState(500);
  const [years, setYears] = useState(20);
  const [expectedReturn, setExpectedReturn] = useState(7);
  const [allocation, setAllocation] = useState({ stocks: 70, bonds: 30 });
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) navigate("/");
    });
  }, [navigate]);

  // Apply goal-based preset from dashboard "Your investing path" → Go
  useEffect(() => {
    if (presetConsumed.current) return;
    try {
      const raw = sessionStorage.getItem(PATH_PRESET_KEY);
      if (!raw) return;
      const p = JSON.parse(raw) as { simulatorYears?: number; etfTimeHorizon?: number };
      const next = { ...p };
      if (p.simulatorYears != null) {
        const y = Math.min(40, Math.max(1, Math.round(Number(p.simulatorYears))));
        setYears(y);
        delete next.simulatorYears;
      }
      presetConsumed.current = true;
      if (Object.keys(next).length === 0) {
        sessionStorage.removeItem(PATH_PRESET_KEY);
      } else {
        sessionStorage.setItem(PATH_PRESET_KEY, JSON.stringify(next));
      }
    } catch {
      // invalid JSON — leave sessionStorage as-is for ETF page
    }
  }, []);

  const runSimulation = () => {
    setIsRunning(true);
    
    // Simple compound growth simulation
    const yearlyData: number[] = [];
    const contributionData: number[] = [];
    const yearsArray: number[] = [];
    
    let currentValue = initialInvestment;
    let totalContributed = initialInvestment;
    const monthlyReturn = expectedReturn / 100 / 12;
    
    for (let year = 0; year <= years; year++) {
      yearsArray.push(year);
      yearlyData.push(Math.round(currentValue));
      contributionData.push(Math.round(totalContributed));
      
      // Simulate 12 months of growth
      for (let month = 0; month < 12; month++) {
        currentValue = currentValue * (1 + monthlyReturn) + monthlyContribution;
        totalContributed += monthlyContribution;
      }
    }
    
    setTimeout(() => {
      setResult({
        years: yearsArray,
        portfolio: yearlyData,
        contributions: contributionData,
        finalValue: Math.round(currentValue),
        totalContributed: Math.round(totalContributed),
        totalGrowth: Math.round(currentValue - totalContributed),
      });
      setIsRunning(false);
    }, 800);
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value);
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
                <TrendingUp className="w-4 h-4 text-primary" />
              </div>
              <span className="font-display text-sm font-semibold">Portfolio Simulator</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Hero */}
        <div className="mb-8">
          <h1 className="font-display text-3xl font-bold mb-2">Portfolio Simulator</h1>
          <p className="text-muted-foreground">
            See how your investments could grow over time
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Input Panel */}
          <div className="glass-card rounded-xl p-6 space-y-6">
            <h2 className="font-display text-lg font-semibold">Parameters</h2>

            {/* Initial Investment */}
            <div>
              <label className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                <DollarSign className="w-4 h-4" />
                Initial Investment
              </label>
              <input
                type="number"
                value={initialInvestment}
                onChange={(e) => setInitialInvestment(Number(e.target.value))}
                className="w-full px-4 py-2 bg-muted rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* Monthly Contribution */}
            <div>
              <label className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                <DollarSign className="w-4 h-4" />
                Monthly Contribution
              </label>
              <input
                type="number"
                value={monthlyContribution}
                onChange={(e) => setMonthlyContribution(Number(e.target.value))}
                className="w-full px-4 py-2 bg-muted rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* Time Horizon */}
            <div>
              <label className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                <Calendar className="w-4 h-4" />
                Time Horizon (Years): {years}
              </label>
              <input
                type="range"
                min="5"
                max="40"
                value={years}
                onChange={(e) => setYears(Number(e.target.value))}
                className="w-full"
              />
            </div>

            {/* Expected Return */}
            <div>
              <label className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                <TrendingUp className="w-4 h-4" />
                Expected Return (%): {expectedReturn}%
              </label>
              <input
                type="range"
                min="1"
                max="12"
                step="0.5"
                value={expectedReturn}
                onChange={(e) => setExpectedReturn(Number(e.target.value))}
                className="w-full"
              />
            </div>

            {/* Allocation */}
            <div>
              <label className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                <PieChart className="w-4 h-4" />
                Allocation
              </label>
              <div className="flex gap-4">
                <div className="flex-1">
                  <div className="text-xs text-muted-foreground mb-1">Stocks: {allocation.stocks}%</div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={allocation.stocks}
                    onChange={(e) => setAllocation({
                      stocks: Number(e.target.value),
                      bonds: 100 - Number(e.target.value),
                    })}
                    className="w-full"
                  />
                </div>
              </div>
              <div className="flex gap-2 mt-2">
                <div className="flex items-center gap-1 text-xs">
                  <div className="w-3 h-3 rounded bg-primary"></div>
                  Stocks {allocation.stocks}%
                </div>
                <div className="flex items-center gap-1 text-xs">
                  <div className="w-3 h-3 rounded bg-info"></div>
                  Bonds {allocation.bonds}%
                </div>
              </div>
            </div>

            {/* Run Button */}
            <button
              onClick={runSimulation}
              disabled={isRunning}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50"
            >
              {isRunning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
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

          {/* Results Panel */}
          <div className="lg:col-span-2 space-y-6">
            {result ? (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="glass-card rounded-xl p-4 text-center">
                    <div className="text-sm text-muted-foreground mb-1">Final Value</div>
                    <div className="text-2xl font-bold text-success">
                      {formatCurrency(result.finalValue)}
                    </div>
                  </div>
                  <div className="glass-card rounded-xl p-4 text-center">
                    <div className="text-sm text-muted-foreground mb-1">Total Contributed</div>
                    <div className="text-2xl font-bold">
                      {formatCurrency(result.totalContributed)}
                    </div>
                  </div>
                  <div className="glass-card rounded-xl p-4 text-center">
                    <div className="text-sm text-muted-foreground mb-1">Investment Growth</div>
                    <div className="text-2xl font-bold text-primary">
                      {formatCurrency(result.totalGrowth)}
                    </div>
                  </div>
                </div>

                {/* Chart */}
                <div className="glass-card rounded-xl p-6">
                  <h3 className="font-display text-lg font-semibold mb-4">Growth Over Time</h3>
                  <div className="relative">
                    {/* Chart bars */}
                    <div className="h-48 flex items-end gap-0.5">
                      {result.years.map((year, index) => {
                        const maxValue = Math.max(...result.portfolio);
                        const portfolioHeight = maxValue > 0 ? (result.portfolio[index] / maxValue) * 100 : 0;
                        const contributionHeight = maxValue > 0 ? (result.contributions[index] / maxValue) * 100 : 0;
                        
                        return (
                          <div 
                            key={year} 
                            className="flex-1 flex flex-col justify-end h-full"
                          >
                            <div
                              className="w-full bg-primary/30 rounded-t relative min-h-[2px]"
                              style={{ height: `${Math.max(portfolioHeight, 1)}%` }}
                            >
                              <div
                                className="absolute bottom-0 w-full bg-primary rounded-t"
                                style={{ 
                                  height: portfolioHeight > 0 
                                    ? `${(contributionHeight / portfolioHeight) * 100}%` 
                                    : '0%' 
                                }}
                              ></div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    {/* X-axis labels - all on same baseline */}
                    <div className="flex gap-0.5 mt-2">
                      {result.years.map((year, index) => (
                        <div key={year} className="flex-1 text-center">
                          {index % 5 === 0 && (
                            <span className="text-xs text-muted-foreground">Y{year}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-4 mt-4 justify-center">
                    <div className="flex items-center gap-2 text-sm">
                      <div className="w-3 h-3 rounded bg-primary"></div>
                      Contributions
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <div className="w-3 h-3 rounded bg-primary/30"></div>
                      Growth
                    </div>
                  </div>
                </div>

                {/* Insights */}
                <div className="glass-card rounded-xl p-6">
                  <h3 className="font-display text-lg font-semibold mb-4">Insights</h3>
                  <div className="space-y-3 text-sm text-muted-foreground">
                    <p>
                      With {formatCurrency(initialInvestment)} initial investment and{" "}
                      {formatCurrency(monthlyContribution)}/month contributions at {expectedReturn}% return:
                    </p>
                    <ul className="list-disc list-inside space-y-2">
                      <li>
                        Your money will grow to <span className="text-success font-semibold">{formatCurrency(result.finalValue)}</span> in {years} years
                      </li>
                      <li>
                        You'll contribute {formatCurrency(result.totalContributed)} total
                      </li>
                      <li>
                        Investment growth adds {formatCurrency(result.totalGrowth)} ({Math.round((result.totalGrowth / result.totalContributed) * 100)}% of contributions)
                      </li>
                      <li>
                        That's the power of compound interest!
                      </li>
                    </ul>
                  </div>
                </div>
              </>
            ) : (
              <div className="glass-card rounded-xl p-12 text-center">
                <TrendingUp className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                <h3 className="font-display text-lg font-semibold mb-2">Ready to Simulate</h3>
                <p className="text-muted-foreground">
                  Adjust the parameters and click "Run Simulation" to see how your investments could grow.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="mt-8 text-center text-xs text-muted-foreground">
          This is a simplified simulation for educational purposes. Actual returns will vary. Past performance does not guarantee future results.
        </div>
      </div>
    </div>
  );
}
