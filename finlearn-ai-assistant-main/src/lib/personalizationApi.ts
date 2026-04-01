/**
 * Personalization API client.
 * Wraps all calls to /api/personalization/* endpoints.
 * Silently swallows errors so the rest of the app never breaks.
 */

import { API_URL } from "./api";

// ---------------------------------------------------------------------------
// Response types (mirror backend Pydantic schemas)
// ---------------------------------------------------------------------------

export interface ReadinessStatus {
  ready_for_next_module: boolean;
  should_review_prereq: boolean;
  suggested_tool: string | null;
  readiness_score: number;
  notes: string;
}

export interface AlternativeSuggestion {
  lesson_id: string;
  title: string;
  confidence: number;
  reason: string;
}

export interface Recommendation {
  user_id: string;
  lesson_id: string;
  title: string;
  topic: string;
  difficulty: number;
  confidence: number;
  explanation: string;
  weak_topic_summary: string;
  readiness: ReadinessStatus;
  alternatives: AlternativeSuggestion[];
  generated_at: string;
}

export interface TopicMasteryResponse {
  user_id: string;
  mastery_map: Record<string, number>;
  weak_topics: string[];
  strong_topics: string[];
}

export interface UserFeaturesResponse {
  user_id: string;
  overall_avg_score: number;
  recent_avg_score: number;
  lessons_completed: number;
  pct_course_complete: number;
  engagement_score: number;
  days_since_last_session: number;
  confusion_indicator: number;
  top_weak_topics: string[];
  top_strong_topics: string[];
}

// ---------------------------------------------------------------------------
// Event ingestion payload
// ---------------------------------------------------------------------------

export interface PersonalizationEvent {
  user_id: string;
  event_type:
    | "lesson_started"
    | "lesson_completed"
    | "lesson_abandoned"
    | "quiz_submitted"
    | "tutor_question"
    | "tool_used"
    | "module_completed"
    | "session_started"
    | "session_ended";
  lesson_id?: string;
  module_id?: string;
  topic?: string;
  score?: number;           // 0–1
  attempt_num?: number;
  duration_mins?: number;
  metadata?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Topic label prettifier
// ---------------------------------------------------------------------------

export const TOPIC_LABELS: Record<string, string> = {
  financial_basics:   "Financial Basics",
  compound_interest:  "Compound Interest",
  risk_tolerance:     "Risk Tolerance",
  volatility:         "Volatility",
  diversification:    "Diversification",
  asset_allocation:   "Asset Allocation",
  etfs:               "ETFs",
  stock_analysis:     "Stock Analysis",
  rebalancing:        "Rebalancing",
  market_mechanics:   "Market Mechanics",
};

export function prettyTopic(topic: string): string {
  return TOPIC_LABELS[topic] ?? topic.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Frontend lesson → backend topic mapping
// ---------------------------------------------------------------------------

export const LESSON_TOPIC_MAP: Record<string, string> = {
  // foundations module
  what_is_investing:       "financial_basics",
  what_youre_buying:       "financial_basics",
  how_markets_work:        "market_mechanics",
  time_and_compounding:    "compound_interest",
  basics_of_risk:          "risk_tolerance",
  accounts_and_setup:      "financial_basics",
  first_time_mindset:      "financial_basics",
  // investor-insight module
  what_moves_markets:      "market_mechanics",
  investor_psychology:     "risk_tolerance",
  hype_vs_fundamentals:    "stock_analysis",
  types_of_investing:      "etfs",
  risk_portfolio_thinking: "diversification",
  reading_market_signals:  "volatility",
  // applied-investing module
  costs_fees_taxes:        "financial_basics",
  what_to_do_in_crash:     "volatility",
  setting_long_term_structure: "asset_allocation",
  realistic_expectations:  "asset_allocation",
  asset_allocation:        "asset_allocation",
  lending_home_ownership:  "financial_basics",
};

export function lessonTopic(lessonId: string): string | undefined {
  return LESSON_TOPIC_MAP[lessonId];
}

// ---------------------------------------------------------------------------
// Frontend lesson → backend lesson ID mapping
//
// The backend curriculum uses synthetic lesson IDs (L01–L20). When the
// frontend sends lesson_completed events, it must use backend IDs so the
// personalization engine's eligibility filter (get_eligible_lessons) can
// correctly exclude already-completed lessons from recommendations.
//
// Multiple frontend lessons can map to the same backend ID (the curricula
// don't align 1:1) — that's fine, it just means completing any of them
// marks the equivalent backend lesson as done.
// ---------------------------------------------------------------------------

export const FRONTEND_TO_BACKEND_LESSON_MAP: Record<string, string> = {
  // foundations module → M1 (Investment Foundations)
  what_is_investing:           "L01",  // financial_basics D1
  what_youre_buying:           "L02",  // financial_basics D1
  time_and_compounding:        "L03",  // compound_interest D1
  accounts_and_setup:          "L01",  // financial_basics (maps to L01)
  first_time_mindset:          "L02",  // financial_basics (maps to L02)
  // investor-insight module → M2 + M3 + M4
  basics_of_risk:              "L05",  // risk_tolerance D1
  reading_market_signals:      "L06",  // volatility D2
  investor_psychology:         "L07",  // risk_tolerance D2
  risk_portfolio_thinking:     "L09",  // diversification D2
  types_of_investing:          "L14",  // etfs D2
  hype_vs_fundamentals:        "L13",  // stock_analysis D2
  how_markets_work:            "L19",  // market_mechanics D3
  what_moves_markets:          "L19",  // market_mechanics D3
  // applied-investing module → M3 + M5
  setting_long_term_structure: "L11",  // asset_allocation D2
  realistic_expectations:      "L11",  // asset_allocation D2
  asset_allocation:            "L12",  // asset_allocation D3
  what_to_do_in_crash:         "L06",  // volatility D2
  costs_fees_taxes:            "L01",  // financial_basics
  lending_home_ownership:      "L02",  // financial_basics
};

/** Map a frontend lesson ID to the closest backend lesson ID for event ingestion. */
export function toBackendLessonId(frontendId: string): string {
  return FRONTEND_TO_BACKEND_LESSON_MAP[frontendId] ?? frontendId;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function pGet<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}/api/personalization${path}`);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function pPost(path: string, body: unknown): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/api/personalization${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return res.ok;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export const personalizationApi = {
  /** Fetch top-3 lesson recommendations for a user. */
  getRecommendations: (userId: string) =>
    pGet<Recommendation[]>(`/users/${userId}/recommend/top3`),

  /** Fetch per-topic mastery scores. */
  getMastery: (userId: string) =>
    pGet<TopicMasteryResponse>(`/users/${userId}/mastery`),

  /** Fetch high-level user learning features. */
  getUserFeatures: (userId: string) =>
    pGet<UserFeaturesResponse>(`/users/${userId}/features`),

  /** Fetch readiness status. */
  getReadiness: (userId: string) =>
    pGet<ReadinessStatus>(`/users/${userId}/readiness`),

  /** Ingest a single interaction event. Fire-and-forget. */
  ingestEvent: (event: PersonalizationEvent) =>
    pPost("/events", event),
};
