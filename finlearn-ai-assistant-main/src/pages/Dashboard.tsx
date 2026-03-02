import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { HeroSection } from "@/components/HeroSection";
import { LessonGrid } from "@/components/LessonGrid";
import { ChatPanel } from "@/components/ChatPanel";
import { LogOut, TrendingUp, BarChart3, Eye, LineChart, Brain, Trophy, Users, PieChart, Zap } from "lucide-react";

const Dashboard = () => {
  const navigate = useNavigate();
  const [userEmail, setUserEmail] = useState("");

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
          
          {/* Learning Modules Section - Now on top */}
          <LessonGrid />
          
          {/* AI Tools Section - Now below */}
          <section className="py-8">
            <h2 className="font-display text-2xl font-bold mb-2">AI Tools</h2>
            <p className="text-muted-foreground mb-6">Powerful analysis tools powered by machine learning</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

              <button
                onClick={() => navigate("/etf-recommender")}
                className="glass-card rounded-xl p-6 text-left hover:border-green-400/40 transition-all group"
              >
                <div className="p-2.5 rounded-lg bg-green-500/10 text-green-400 w-fit mb-4 group-hover:shadow-lg group-hover:shadow-green-500/20 transition-all">
                  <PieChart className="w-5 h-5" />
                </div>
                <h3 className="font-display text-lg font-semibold mb-2 group-hover:text-green-400 transition-colors">
                  ETF Recommender
                </h3>
                <p className="text-sm text-muted-foreground">
                  Take a risk quiz, get personalized ETF recommendations, and run Monte Carlo simulations
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
