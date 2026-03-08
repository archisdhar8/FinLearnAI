import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import {
  ArrowLeft,
  Trophy,
  Medal,
  Award,
  TrendingUp,
  Crown,
  Star,
  Users,
} from "lucide-react";

interface LeaderboardEntry {
  rank: number;
  user_id: string;
  username: string;
  avatar_color: string;
  total_score: number;
  quizzes_completed: number;
  modules_completed: number;
  average_score: number;
}

interface UserStats {
  rank: number | null;
  total_score: number;
  quizzes_completed: number;
  average_score: number;
  modules_completed: number;
}

// Fallback seed data (backend returns the authoritative list)
const SAMPLE_LEADERBOARD: LeaderboardEntry[] = [
  { rank: 1, user_id: "seed-01", username: "sarah.m",       avatar_color: "bg-violet-500",  total_score: 58, quizzes_completed: 19, modules_completed: 4, average_score: 94 },
  { rank: 2, user_id: "seed-02", username: "jchen_99",      avatar_color: "bg-blue-500",    total_score: 52, quizzes_completed: 16, modules_completed: 3, average_score: 91 },
  { rank: 3, user_id: "seed-03", username: "mike.ramirez",  avatar_color: "bg-green-500",   total_score: 47, quizzes_completed: 15, modules_completed: 3, average_score: 90 },
  { rank: 4, user_id: "seed-11", username: "james.p",       avatar_color: "bg-indigo-500",  total_score: 44, quizzes_completed: 14, modules_completed: 3, average_score: 89 },
  { rank: 5, user_id: "seed-04", username: "priya.k",       avatar_color: "bg-pink-500",    total_score: 41, quizzes_completed: 13, modules_completed: 3, average_score: 88 },
  { rank: 6, user_id: "seed-05", username: "david.l",       avatar_color: "bg-yellow-500",  total_score: 35, quizzes_completed: 11, modules_completed: 2, average_score: 86 },
  { rank: 7, user_id: "seed-12", username: "zoe.martinez",  avatar_color: "bg-emerald-500", total_score: 33, quizzes_completed: 10, modules_completed: 2, average_score: 85 },
  { rank: 8, user_id: "seed-06", username: "emma.w",        avatar_color: "bg-cyan-500",    total_score: 28, quizzes_completed: 9,  modules_completed: 2, average_score: 84 },
  { rank: 9, user_id: "seed-07", username: "alex.t",        avatar_color: "bg-orange-500",  total_score: 22, quizzes_completed: 7,  modules_completed: 1, average_score: 82 },
  { rank: 10, user_id: "seed-08", username: "nina.h",       avatar_color: "bg-purple-500",  total_score: 16, quizzes_completed: 5,  modules_completed: 1, average_score: 80 },
];

export default function Leaderboard() {
  const navigate = useNavigate();
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>(SAMPLE_LEADERBOARD);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "weekly" | "monthly">("all");

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        navigate("/");
        return;
      }
      const userId = session.user.id;
      setCurrentUserId(userId);
      
      // Try to fetch real leaderboard data
      try {
        const { API_URL } = await import("@/lib/api");
        const response = await fetch(`${API_URL}/api/leaderboard`);
        if (response.ok) {
          const data = await response.json();
          if (data.length > 0) {
            setLeaderboard(data);
          }
        }
      } catch (error) {
        console.log("Using sample leaderboard data");
      }
      
      // Fetch user's own stats
      try {
        const statsResponse = await fetch(`${API_URL}/api/user-stats/${userId}`);
        if (statsResponse.ok) {
          const stats = await statsResponse.json();
          setUserStats(stats);
        }
      } catch (error) {
        console.log("Could not fetch user stats");
      }
      
      setLoading(false);
    };
    
    checkAuth();
  }, [navigate]);

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <Crown className="w-5 h-5 text-yellow-400" />;
      case 2:
        return <Medal className="w-5 h-5 text-gray-300" />;
      case 3:
        return <Medal className="w-5 h-5 text-amber-600" />;
      default:
        return <span className="text-muted-foreground font-mono">#{rank}</span>;
    }
  };

  const getRankStyle = (rank: number) => {
    switch (rank) {
      case 1:
        return "bg-gradient-to-r from-yellow-500/20 to-yellow-500/5 border-yellow-500/30";
      case 2:
        return "bg-gradient-to-r from-gray-400/20 to-gray-400/5 border-gray-400/30";
      case 3:
        return "bg-gradient-to-r from-amber-600/20 to-amber-600/5 border-amber-600/30";
      default:
        return "";
    }
  };

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
                <Trophy className="w-4 h-4 text-primary" />
              </div>
              <span className="font-display text-sm font-semibold">Leaderboard</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Hero */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
            <Trophy className="w-8 h-8 text-primary" />
          </div>
          <h1 className="font-display text-3xl font-bold mb-2">Quiz Leaderboard</h1>
          <p className="text-muted-foreground">
            See how you stack up against other learners
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex justify-center gap-2 mb-8">
          {(["all", "weekly", "monthly"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === f
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              {f === "all" ? "All Time" : f === "weekly" ? "This Week" : "This Month"}
            </button>
          ))}
        </div>

        {/* Top 3 Podium */}
        <div className="flex justify-center items-end gap-4 mb-8">
          {/* 2nd Place */}
          {leaderboard[1] && (
            <div className="text-center">
              <div className={`w-16 h-16 rounded-full ${leaderboard[1].avatar_color} flex items-center justify-center text-white font-bold text-xl mb-2 mx-auto`}>
                {leaderboard[1].username[0]}
              </div>
              <Medal className="w-6 h-6 text-gray-300 mx-auto mb-1" />
              <p className="font-semibold text-sm">{leaderboard[1].username}</p>
              <p className="text-xs text-muted-foreground">{leaderboard[1].total_score} pts</p>
              <div className="h-20 w-24 bg-gray-400/20 rounded-t-lg mt-2 flex items-center justify-center">
                <span className="text-2xl font-bold text-gray-400">2</span>
              </div>
            </div>
          )}
          
          {/* 1st Place */}
          {leaderboard[0] && (
            <div className="text-center">
              <div className={`w-20 h-20 rounded-full ${leaderboard[0].avatar_color} flex items-center justify-center text-white font-bold text-2xl mb-2 mx-auto ring-4 ring-yellow-400/50`}>
                {leaderboard[0].username[0]}
              </div>
              <Crown className="w-8 h-8 text-yellow-400 mx-auto mb-1" />
              <p className="font-bold">{leaderboard[0].username}</p>
              <p className="text-sm text-primary font-semibold">{leaderboard[0].total_score} pts</p>
              <div className="h-28 w-28 bg-yellow-500/20 rounded-t-lg mt-2 flex items-center justify-center">
                <span className="text-3xl font-bold text-yellow-400">1</span>
              </div>
            </div>
          )}
          
          {/* 3rd Place */}
          {leaderboard[2] && (
            <div className="text-center">
              <div className={`w-16 h-16 rounded-full ${leaderboard[2].avatar_color} flex items-center justify-center text-white font-bold text-xl mb-2 mx-auto`}>
                {leaderboard[2].username[0]}
              </div>
              <Medal className="w-6 h-6 text-amber-600 mx-auto mb-1" />
              <p className="font-semibold text-sm">{leaderboard[2].username}</p>
              <p className="text-xs text-muted-foreground">{leaderboard[2].total_score} pts</p>
              <div className="h-16 w-24 bg-amber-600/20 rounded-t-lg mt-2 flex items-center justify-center">
                <span className="text-2xl font-bold text-amber-600">3</span>
              </div>
            </div>
          )}
        </div>

        {/* Full Leaderboard */}
        <div className="glass-card rounded-xl overflow-hidden">
          <div className="p-4 border-b border-border">
            <h2 className="font-display font-semibold">Full Rankings</h2>
          </div>
          <div className="divide-y divide-border">
            {leaderboard.map((entry, index) => (
              <div
                key={entry.user_id}
                className={`flex items-center gap-4 p-4 hover:bg-muted/50 transition-colors ${getRankStyle(entry.rank)} ${
                  entry.user_id === currentUserId ? "bg-primary/10" : ""
                }`}
              >
                {/* Rank */}
                <div className="w-10 flex justify-center">
                  {getRankIcon(entry.rank)}
                </div>

                {/* Avatar */}
                <div className={`w-10 h-10 rounded-full ${entry.avatar_color} flex items-center justify-center text-white font-semibold`}>
                  {entry.username[0]}
                </div>

                {/* User Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{entry.username}</span>
                    {entry.user_id === currentUserId && (
                      <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">You</span>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {entry.quizzes_completed} quizzes • {entry.modules_completed} modules
                  </div>
                </div>

                {/* Stats */}
                <div className="text-right">
                  <div className="font-bold text-lg">{entry.total_score}</div>
                  <div className="text-xs text-muted-foreground">
                    {entry.average_score}% avg
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Your Stats Card */}
        <div className="glass-card rounded-xl p-6 mt-8">
          <h3 className="font-display font-semibold mb-4 flex items-center gap-2">
            <Star className="w-5 h-5 text-primary" />
            Your Progress
          </h3>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-primary">
                {userStats?.rank ? `#${userStats.rank}` : "--"}
              </div>
              <div className="text-xs text-muted-foreground">Your Rank</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{userStats?.total_score || 0}</div>
              <div className="text-xs text-muted-foreground">Total Points</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{userStats?.quizzes_completed || 0}</div>
              <div className="text-xs text-muted-foreground">Quizzes</div>
            </div>
            <div>
              <div className="text-2xl font-bold">{userStats?.average_score || 0}%</div>
              <div className="text-xs text-muted-foreground">Avg Score</div>
            </div>
          </div>
          {(!userStats || userStats.quizzes_completed === 0) && (
            <p className="text-sm text-muted-foreground text-center mt-4">
              Complete quizzes in the learning modules to appear on the leaderboard!
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
