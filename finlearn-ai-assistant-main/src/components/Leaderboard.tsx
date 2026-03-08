import { useState, useEffect } from 'react';
import { Trophy, Medal, Award, Crown, Loader2 } from 'lucide-react';

interface LeaderboardEntry {
  rank: number;
  user_id: string;
  display_name?: string;
  username?: string;
  total_score?: number;
  score?: number;
  percentage?: number;
  avg_percentage?: number;
  average_score?: number;
  modules_completed?: number;
  quizzes_completed?: number;
  attempts?: number;
}

interface LeaderboardProps {
  moduleId?: string;
  currentUserId?: string;
}

export const Leaderboard = ({ moduleId, currentUserId }: LeaderboardProps) => {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLeaderboard();
  }, [moduleId]);

  const fetchLeaderboard = async () => {
    setLoading(true);
    const { API_URL } = await import("@/lib/api");
    try {
      const url = moduleId 
        ? `${API_URL}/api/leaderboard?module_id=${moduleId}`
        : `${API_URL}/api/leaderboard`;
      
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch leaderboard');
      
      const data = await response.json();
      // Backend returns a list directly (or {leaderboard: [...]})
      const entries = Array.isArray(data) ? data : (data.leaderboard || []);
      setEntries(entries);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  };

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1: return <Crown className="w-5 h-5 text-yellow-400" />;
      case 2: return <Medal className="w-5 h-5 text-slate-300" />;
      case 3: return <Award className="w-5 h-5 text-amber-600" />;
      default: return <span className="w-5 h-5 flex items-center justify-center text-sm text-slate-400">{rank}</span>;
    }
  };

  const getRankBg = (rank: number) => {
    switch (rank) {
      case 1: return 'bg-yellow-500/10 border-yellow-500/30';
      case 2: return 'bg-slate-400/10 border-slate-400/30';
      case 3: return 'bg-amber-600/10 border-amber-600/30';
      default: return 'bg-slate-800/50 border-slate-700';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center p-8 text-red-400">
        {error}
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="text-center p-8">
        <Trophy className="w-12 h-12 text-slate-600 mx-auto mb-4" />
        <p className="text-slate-400">No scores yet. Be the first!</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-4">
        <Trophy className="w-5 h-5 text-primary" />
        <h3 className="font-semibold text-white">
          {moduleId ? 'Module Leaderboard' : 'Global Leaderboard'}
        </h3>
      </div>
      
      {entries.map((entry) => {
        const isCurrentUser = entry.user_id === currentUserId;
        const displayName = entry.display_name || entry.username || `User`;
        const score = entry.total_score ?? entry.score ?? 0;
        const pct = entry.avg_percentage ?? entry.average_score ?? entry.percentage ?? 0;
        
        return (
          <div
            key={entry.user_id}
            className={`flex items-center gap-4 p-3 rounded-lg border transition-all ${getRankBg(entry.rank)} ${
              isCurrentUser ? 'ring-2 ring-primary' : ''
            }`}
          >
            <div className="w-8 flex justify-center">
              {getRankIcon(entry.rank)}
            </div>
            
            <div className="flex-1 min-w-0">
              <p className={`font-medium truncate ${isCurrentUser ? 'text-primary' : 'text-white'}`}>
                {displayName}
                {isCurrentUser && <span className="text-xs ml-2 text-primary">(You)</span>}
              </p>
              {entry.modules_completed !== undefined && (
                <p className="text-xs text-slate-400">
                  {entry.modules_completed} modules completed
                </p>
              )}
            </div>
            
            <div className="text-right">
              <p className="font-bold text-white">{score} pts</p>
              <p className="text-xs text-slate-400">{pct.toFixed(1)}%</p>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default Leaderboard;
