import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import {
  ArrowLeft,
  Users,
  Trophy,
  BookOpen,
  TrendingUp,
  Search,
  UserPlus,
  MessageCircle,
  Star,
} from "lucide-react";

interface UserProfile {
  id: string;
  username: string;
  avatar_color: string;
  total_score: number;
  modules_completed: number;
  quizzes_completed: number;
  joined_date: string;
  is_online: boolean;
  last_activity: string;
}

// Sample users data
const SAMPLE_USERS: UserProfile[] = [
  { id: "1", username: "InvestorPro", avatar_color: "bg-yellow-500", total_score: 2850, modules_completed: 3, quizzes_completed: 18, joined_date: "2024-01-15", is_online: true, last_activity: "Completed Advanced Module" },
  { id: "2", username: "WealthBuilder", avatar_color: "bg-blue-500", total_score: 2720, modules_completed: 3, quizzes_completed: 17, joined_date: "2024-02-01", is_online: true, last_activity: "Scored 95% on Risk Quiz" },
  { id: "3", username: "StockSavvy", avatar_color: "bg-green-500", total_score: 2580, modules_completed: 3, quizzes_completed: 16, joined_date: "2024-01-20", is_online: false, last_activity: "Learning about ETFs" },
  { id: "4", username: "MarketMaster", avatar_color: "bg-purple-500", total_score: 2340, modules_completed: 2, quizzes_completed: 15, joined_date: "2024-02-10", is_online: true, last_activity: "Started Investor Insight" },
  { id: "5", username: "DividendKing", avatar_color: "bg-pink-500", total_score: 2180, modules_completed: 2, quizzes_completed: 14, joined_date: "2024-01-25", is_online: false, last_activity: "Completed Foundation" },
  { id: "6", username: "IndexFundFan", avatar_color: "bg-cyan-500", total_score: 1950, modules_completed: 2, quizzes_completed: 13, joined_date: "2024-02-15", is_online: true, last_activity: "Exploring Stock Screener" },
  { id: "7", username: "CompoundKing", avatar_color: "bg-orange-500", total_score: 1820, modules_completed: 2, quizzes_completed: 12, joined_date: "2024-02-20", is_online: false, last_activity: "Learning Compounding" },
  { id: "8", username: "RetireEarly", avatar_color: "bg-red-500", total_score: 1650, modules_completed: 1, quizzes_completed: 11, joined_date: "2024-03-01", is_online: true, last_activity: "Just joined!" },
  { id: "9", username: "BudgetBoss", avatar_color: "bg-indigo-500", total_score: 1480, modules_completed: 1, quizzes_completed: 10, joined_date: "2024-02-28", is_online: false, last_activity: "Studying Risk Management" },
  { id: "10", username: "NewInvestor", avatar_color: "bg-teal-500", total_score: 1200, modules_completed: 1, quizzes_completed: 8, joined_date: "2024-03-05", is_online: true, last_activity: "Started Foundation" },
  { id: "11", username: "SavingsGuru", avatar_color: "bg-emerald-500", total_score: 980, modules_completed: 1, quizzes_completed: 6, joined_date: "2024-03-10", is_online: false, last_activity: "Learning about Stocks" },
  { id: "12", username: "FinanceFresh", avatar_color: "bg-violet-500", total_score: 450, modules_completed: 0, quizzes_completed: 3, joined_date: "2024-03-12", is_online: true, last_activity: "Taking first quiz" },
];

export default function Social() {
  const navigate = useNavigate();
  const [users, setUsers] = useState<UserProfile[]>(SAMPLE_USERS);
  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "online" | "top">("all");
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        navigate("/");
        return;
      }
      setCurrentUserId(session.user.id);
      
      // Try to fetch real users from backend
      try {
        const { API_URL } = await import("@/lib/api");
        const response = await fetch(`${API_URL}/api/users`);
        if (response.ok) {
          const data = await response.json();
          if (data.length > 0) {
            setUsers(data);
          }
        }
      } catch (error) {
        console.log("Using sample user data");
      }
    };
    
    checkAuth();
  }, [navigate]);

  const filteredUsers = users.filter((user) => {
    const matchesSearch = user.username.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = 
      filter === "all" ? true :
      filter === "online" ? user.is_online :
      filter === "top" ? user.total_score >= 2000 : true;
    return matchesSearch && matchesFilter;
  });

  const onlineCount = users.filter(u => u.is_online).length;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="max-w-4xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate("/dashboard")}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <Users className="w-4 h-4 text-primary" />
              </div>
              <span className="font-display text-sm font-semibold">Community</span>
            </div>
          </div>
          <button
            onClick={() => navigate("/leaderboard")}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-sm hover:bg-primary/20 transition-colors"
          >
            <Trophy className="w-4 h-4" />
            Leaderboard
          </button>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Hero */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
            <Users className="w-8 h-8 text-primary" />
          </div>
          <h1 className="font-display text-3xl font-bold mb-2">FinLearn Community</h1>
          <p className="text-muted-foreground">
            Connect with {users.length} learners on their investing journey
          </p>
          <div className="flex justify-center gap-4 mt-4">
            <div className="flex items-center gap-2 text-sm">
              <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
              <span className="text-muted-foreground">{onlineCount} online now</span>
            </div>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-muted rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="flex gap-2">
            {(["all", "online", "top"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filter === f
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:text-foreground"
                }`}
              >
                {f === "all" ? "All" : f === "online" ? "Online" : "Top Scorers"}
              </button>
            ))}
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="glass-card rounded-xl p-4 text-center">
            <Users className="w-6 h-6 text-primary mx-auto mb-2" />
            <div className="text-2xl font-bold">{users.length}</div>
            <div className="text-xs text-muted-foreground">Total Learners</div>
          </div>
          <div className="glass-card rounded-xl p-4 text-center">
            <BookOpen className="w-6 h-6 text-success mx-auto mb-2" />
            <div className="text-2xl font-bold">{users.reduce((acc, u) => acc + u.modules_completed, 0)}</div>
            <div className="text-xs text-muted-foreground">Modules Completed</div>
          </div>
          <div className="glass-card rounded-xl p-4 text-center">
            <Trophy className="w-6 h-6 text-warning mx-auto mb-2" />
            <div className="text-2xl font-bold">{users.reduce((acc, u) => acc + u.quizzes_completed, 0)}</div>
            <div className="text-xs text-muted-foreground">Quizzes Taken</div>
          </div>
        </div>

        {/* Users Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredUsers.map((user) => (
            <div
              key={user.id}
              className="glass-card rounded-xl p-4 hover:border-primary/30 transition-colors"
            >
              <div className="flex items-start gap-4">
                {/* Avatar */}
                <div className="relative">
                  <div className={`w-12 h-12 rounded-full ${user.avatar_color} flex items-center justify-center text-white font-bold text-lg`}>
                    {user.username[0]}
                  </div>
                  {user.is_online && (
                    <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-success rounded-full border-2 border-background"></div>
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold truncate">{user.username}</span>
                    {user.total_score >= 2500 && (
                      <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {user.last_activity}
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Trophy className="w-3 h-3" />
                      {user.total_score} pts
                    </span>
                    <span className="flex items-center gap-1">
                      <BookOpen className="w-3 h-3" />
                      {user.modules_completed} modules
                    </span>
                  </div>
                </div>

                {/* Action */}
                <button className="p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-primary">
                  <UserPlus className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {filteredUsers.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No users found matching your criteria</p>
          </div>
        )}

        {/* Join CTA */}
        <div className="glass-card rounded-xl p-6 mt-8 text-center bg-gradient-to-r from-primary/10 to-transparent">
          <h3 className="font-display font-semibold mb-2">Join the Community!</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Complete quizzes and modules to climb the leaderboard and connect with fellow learners.
          </p>
          <button
            onClick={() => navigate("/dashboard")}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity"
          >
            Start Learning
          </button>
        </div>
      </div>
    </div>
  );
}
