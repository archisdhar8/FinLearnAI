/**
 * PersonalizationCard
 *
 * Shown on the Dashboard between the hero and the module grid.
 * Displays:
 *  - Per-topic mastery bars (only topics with any activity)
 *  - Top next-lesson recommendation with explanation + confidence
 *  - Readiness status (module-ready / prereq-review / tool suggestion)
 *  - Two alternative suggestions
 *
 * Gracefully shows nothing if the personalization backend is unavailable.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Brain,
  ChevronRight,
  Lightbulb,
  Loader2,
  Sparkles,
  Target,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Wrench,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  personalizationApi,
  prettyTopic,
  Recommendation,
  TopicMasteryResponse,
  ReadinessStatus,
  UserFeaturesResponse,
} from "@/lib/personalizationApi";

// ---------------------------------------------------------------------------
// Tool ID → frontend route
// ---------------------------------------------------------------------------

const TOOL_ROUTES: Record<string, string> = {
  portfolio_simulator: "/simulator",
  etf_recommender:     "/etf-recommender",
  stock_screener:      "/screener",
  ai_tutor:            "/dashboard",
};

const TOOL_LABELS: Record<string, string> = {
  portfolio_simulator: "Portfolio Simulator",
  etf_recommender:     "ETF Recommender",
  stock_screener:      "Stock Screener",
  ai_tutor:            "AI Tutor",
};

// ---------------------------------------------------------------------------
// Mastery bar colours
// ---------------------------------------------------------------------------

function masteryColor(score: number): string {
  if (score >= 0.85) return "bg-success";
  if (score >= 0.70) return "bg-primary";
  if (score >= 0.50) return "bg-info";
  return "bg-destructive/70";
}

function masteryLabel(score: number): string {
  if (score >= 0.85) return "Strong";
  if (score >= 0.70) return "Proficient";
  if (score >= 0.50) return "Developing";
  return "Needs review";
}

// ---------------------------------------------------------------------------
// Difficulty dots
// ---------------------------------------------------------------------------

function DifficultyDots({ level }: { level: number }) {
  return (
    <span className="flex gap-0.5 items-center">
      {[1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${i <= level ? "bg-primary" : "bg-muted"}`}
        />
      ))}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface Props {
  userId: string | null;
}

export function PersonalizationCard({ userId }: Props) {
  const navigate = useNavigate();

  const [loading, setLoading]               = useState(true);
  const [recs, setRecs]                     = useState<Recommendation[] | null>(null);
  const [mastery, setMastery]               = useState<TopicMasteryResponse | null>(null);
  const [features, setFeatures]             = useState<UserFeaturesResponse | null>(null);

  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    const load = async () => {
      const [recsData, masteryData, featuresData] = await Promise.all([
        personalizationApi.getRecommendations(userId),
        personalizationApi.getMastery(userId),
        personalizationApi.getUserFeatures(userId),
      ]);
      if (cancelled) return;
      setRecs(recsData);
      setMastery(masteryData);
      setFeatures(featuresData);
      setLoading(false);
    };

    load();
    return () => { cancelled = true; };
  }, [userId]);

  // ── Nothing to show until user ID is ready ──────────────────────────────
  if (!userId) return null;

  // ── Loading state ────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="mb-8 flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading your personalized insights…
      </div>
    );
  }

  // ── No data at all (backend offline or new user with zero events) ─────────
  const hasActivity = features && features.lessons_completed > 0;
  if (!hasActivity) {
    return (
      <Card className="mb-8 border-primary/20 bg-primary/5">
        <CardContent className="flex items-start gap-3 pt-5">
          <Sparkles className="w-5 h-5 text-primary mt-0.5 shrink-0" />
          <div>
            <p className="font-medium text-foreground">Personalized learning path</p>
            <p className="text-sm text-muted-foreground mt-0.5">
              Complete your first lesson to unlock AI-powered next-step
              recommendations, topic mastery tracking, and readiness signals.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // ── Active mastery map (only topics with any score) ───────────────────────
  const activeMastery = mastery
    ? Object.entries(mastery.mastery_map)
        .filter(([, v]) => v > 0.01)
        .sort(([, a], [, b]) => b - a)
    : [];

  const topRec   = recs?.[0] ?? null;
  const altRecs  = recs?.slice(1) ?? [];
  const readiness: ReadinessStatus | null = topRec?.readiness ?? null;

  return (
    <div className="mb-8 space-y-4">
      {/* ── Header row ── */}
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-bold flex items-center gap-2">
          <Brain className="w-5 h-5 text-primary" />
          Your Learning Progress
        </h2>
        {features && (
          <span className="text-xs text-muted-foreground">
            {features.lessons_completed} lesson{features.lessons_completed !== 1 ? "s" : ""} completed
            · {Math.round(features.pct_course_complete * 100)}% of curriculum
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ── Left: Topic mastery ────────────────────────────────────────── */}
        {activeMastery.length > 0 && (
          <Card className="glass-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                Topic Mastery
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {activeMastery.map(([topic, score]) => (
                <div key={topic}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-medium text-foreground">
                      {prettyTopic(topic)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {Math.round(score * 100)}% · {masteryLabel(score)}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${masteryColor(score)}`}
                      style={{ width: `${Math.round(score * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* ── Right: Recommendation ──────────────────────────────────────── */}
        {topRec ? (
          <Card className="glass-card border-primary/20">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-primary" />
                Recommended Next Step
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Main recommendation */}
              <div className="rounded-lg bg-primary/8 border border-primary/20 p-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-foreground text-sm leading-tight">
                      {topRec.title}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-muted-foreground">
                        {prettyTopic(topRec.topic)}
                      </span>
                      <span className="text-muted-foreground/40">·</span>
                      <DifficultyDots level={topRec.difficulty} />
                    </div>
                  </div>
                  {/* Confidence badge */}
                  <span
                    className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${
                      topRec.confidence >= 0.7
                        ? "bg-success/20 text-success"
                        : topRec.confidence >= 0.4
                        ? "bg-primary/20 text-primary"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {Math.round(topRec.confidence * 100)}% match
                  </span>
                </div>

                {/* Explanation */}
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {topRec.explanation}
                </p>

                {/* Weak topic summary */}
                {topRec.weak_topic_summary && !topRec.weak_topic_summary.startsWith("No ") && (
                  <p className="text-xs text-muted-foreground/80 italic">
                    {topRec.weak_topic_summary}
                  </p>
                )}
              </div>

              {/* Alternatives */}
              {altRecs.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1.5 font-medium">Also worth considering:</p>
                  <div className="space-y-1.5">
                    {altRecs.map((alt) => (
                      <div
                        key={alt.lesson_id}
                        className="flex items-center gap-2 text-xs text-muted-foreground rounded-md bg-muted/40 px-2.5 py-1.5"
                      >
                        <ChevronRight className="w-3 h-3 shrink-0 text-primary/60" />
                        <span className="font-medium text-foreground/80">{alt.title}</span>
                        <span className="ml-auto shrink-0 text-muted-foreground/60">
                          {prettyTopic(alt.topic)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ) : (
          /* No recommendation — all lessons done or no eligible candidates */
          activeMastery.length > 0 && (
            <Card className="glass-card border-success/20 bg-success/5">
              <CardContent className="flex items-start gap-3 pt-5">
                <CheckCircle2 className="w-5 h-5 text-success mt-0.5 shrink-0" />
                <div>
                  <p className="font-medium text-foreground">Great work!</p>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    You've worked through the available curriculum. Keep practising
                    with the tools below to deepen your mastery.
                  </p>
                </div>
              </CardContent>
            </Card>
          )
        )}
      </div>

      {/* ── Readiness strip ──────────────────────────────────────────────── */}
      {readiness && (
        <div className="flex flex-wrap gap-3">
          {readiness.ready_for_next_module && (
            <div className="flex items-center gap-1.5 text-xs text-success bg-success/10 px-3 py-1.5 rounded-full">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Ready for next module
            </div>
          )}
          {readiness.should_review_prereq && (
            <div className="flex items-center gap-1.5 text-xs text-destructive bg-destructive/10 px-3 py-1.5 rounded-full">
              <AlertTriangle className="w-3.5 h-3.5" />
              Review a prerequisite first
            </div>
          )}
          {readiness.suggested_tool && (
            <button
              onClick={() => {
                const route = TOOL_ROUTES[readiness.suggested_tool!];
                if (route) navigate(route);
              }}
              className="flex items-center gap-1.5 text-xs text-primary bg-primary/10 px-3 py-1.5 rounded-full hover:bg-primary/20 transition-colors"
            >
              <Wrench className="w-3.5 h-3.5" />
              Try: {TOOL_LABELS[readiness.suggested_tool] ?? readiness.suggested_tool}
            </button>
          )}
          {readiness.notes && !readiness.ready_for_next_module && !readiness.should_review_prereq && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/50 px-3 py-1.5 rounded-full">
              <Target className="w-3.5 h-3.5" />
              {readiness.notes}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
