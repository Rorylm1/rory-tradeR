export type Overview = {
  journal_events: number;
  executed_positions: number;
  open_positions: number;
  closed_positions: number;
  won_positions: number;
  lost_positions: number;
  void_positions: number;
  marked_open_positions: number;
  total_stake: number;
  total_commission_paid: number;
  total_realized_pnl: number;
  total_unrealized_pnl: number;
  total_net_pnl: number;
  latest_strategy_decisions: number;
  latest_strategy_acceptances: number;
  latest_strategy_rejections: number;
  latest_strategy_snapshots_seen: number;
};

export type Position = {
  proposal_id: string;
  created_at: string | null;
  market_title: string;
  selection_name: string;
  event_name: string | null;
  competition_name: string | null;
  side: string;
  stake: number;
  fill_price: number;
  mark_price: number | null;
  mark_source: string | null;
  unrealized_pnl: number | null;
  realized_pnl: number | null;
  resolved_outcome: string | null;
  event_start: string | null;
  signal_confidence: number | null;
  reason: string | null;
  live_review?: {
    status: string;
    note: string;
    recorded_at: string;
  } | null;
};

export type RecentEvent = {
  event_type: string;
  recorded_at: string;
  payload: Record<string, unknown>;
};

export type MarketRow = {
  captured_at: string | null;
  exchange: string;
  market_id: string;
  market_title: string;
  selection_id: string;
  selection_name: string;
  category: string;
  subcategory: string;
  event_start: string | null;
  event_name: string | null;
  competition_name: string | null;
  status: string;
  best_back: number | null;
  best_lay: number | null;
  last_traded: number | null;
  implied_probability: number | null;
  best_back_size: number | null;
  best_lay_size: number | null;
  traded_volume: number | null;
  selection_total_matched: number | null;
  market_total_matched: number | null;
  market_total_available: number | null;
  in_play: boolean | null;
  is_market_data_delayed: boolean | null;
};

export type DataQuality = {
  market_count: number;
  selection_count: number;
  priced_selection_count: number;
  missing_price_count: number;
  liquid_selection_count: number;
  tradeable_selection_count: number;
  delayed_market_data_count: number;
  in_play_market_count: number;
  min_available_size: number;
  min_market_total_matched: number;
  price_missing_kill_switch: boolean;
  liquidity_kill_switch: boolean;
  delayed_data_kill_switch: boolean;
  in_play_kill_switch: boolean;
};

export type LatestMarkets = {
  snapshot_path: string | null;
  captured_at: string | null;
  market_count: number;
  selection_count: number;
  data_quality: DataQuality;
  markets: MarketRow[];
};

export type LiveOdds = {
  mode: "live";
  read_only: boolean;
  fetched_at: string;
  category: string;
  max_results: number;
  betfair: {
    ok: boolean | null;
    approval_status: string;
    message: string;
  };
  market_count: number;
  selection_count: number;
  data_quality: DataQuality;
  markets: MarketRow[];
  error: string | null;
  live_execution_available: boolean;
};

export type PaperSessionRun = {
  status: "completed" | "failed" | "timeout" | "rejected";
  started_at: string;
  finished_at: string;
  category: string;
  max_results: number;
  returncode: number | null;
  stdout: string;
  stderr: string;
  summary: {
    snapshot_path?: string;
    snapshots_collected?: number;
    strategy?: string;
    strategy_focus?: string;
    strategy_decisions?: number;
    strategy_acceptances?: number;
    strategy_rejections?: number;
    top_rejections?: string;
    proposals_created?: number;
    duplicate_proposals_skipped?: number;
    paper_fills_created?: number;
    journal_path?: string;
  };
  live_execution_available: boolean;
};

export type PnlPoint = {
  recorded_at: string;
  event_type: string;
  cumulative_realized_pnl: number;
  cumulative_stake: number;
};

export type PerformanceRow = {
  strategy_name?: string | null;
  strategy_version?: string | null;
  price_bucket?: string | null;
  time_window?: string | null;
  executed_positions: number;
  open_positions: number;
  closed_positions: number;
  won_positions: number;
  avg_confidence: number | null;
  total_stake: number;
  total_commission_paid: number;
  total_realized_pnl: number;
  total_unrealized_pnl: number;
  win_rate: number | null;
  total_net_pnl: number;
};

export type PerformanceBreakdown = {
  strategy: PerformanceRow[];
  price_bucket: PerformanceRow[];
  time_window: PerformanceRow[];
};

export type StrategyRule = {
  label: string;
  value: string;
  detail: string;
};

export type SnapshotCollection = {
  snapshot_path?: string;
  snapshot_count?: number;
  category?: string;
  recorded_at: string;
};

export type StrategyContext = {
  category: string;
  definition: {
    name: string;
    version: string;
    description: string;
    fixed_stake: number;
    min_hours_to_event: number;
    max_hours_to_event: number;
    min_back_price: number;
    max_back_price: number;
    max_spread: number;
    max_snapshot_age_seconds: number;
    min_market_total_matched: number;
    min_best_back_size: number;
    allowed_categories: string[];
    allowed_subcategories: string[];
    holding_period_hours: number;
    kill_conditions: string[];
    acceptance_min_trades: number;
    acceptance_min_roi: number;
    tags: string[];
  };
  rules: StrategyRule[];
  recent_snapshot_collections: SnapshotCollection[];
};

export type StrategyEvaluation = {
  strategy_name: string;
  strategy_version: string;
  snapshots_seen: number;
  decisions_count: number;
  accepted_count: number;
  rejected_count: number;
  rejection_counts: Record<string, number>;
  recorded_at: string;
} | null;

export type StrategyDecision = {
  recorded_at: string;
  market_id: string;
  market_title: string;
  selection_id: string | null;
  selection_name: string | null;
  category: string;
  subcategory: string;
  event_start: string | null;
  accepted: boolean;
  reason_code: string;
  reason: string;
  requested_price: number | null;
  best_back: number | null;
  best_lay: number | null;
  spread: number | null;
  confidence: number;
};

export type Health = {
  status: string;
  checked_at: string;
  betfair: {
    ok: boolean | null;
    approval_status: string;
    message: string;
  };
  snapshots: {
    latest_snapshot_modified_at: string | null;
    snapshot_age_seconds: number | null;
    stale: boolean;
    stale_after_seconds: number;
  };
  data_quality: DataQuality;
  supports_live_execution: boolean;
  live_enabled: boolean;
  live_execution_available: boolean;
};

export type BackendFetchIssue = {
  path: string;
  message: string;
};

export type DashboardSummary = {
  overview?: Partial<Overview>;
  open_positions?: Position[];
  closed_positions?: Position[];
  recent_events?: RecentEvent[];
  strategy_evaluation?: StrategyEvaluation;
  strategy_decisions?: StrategyDecision[];
  performance?: Partial<PerformanceBreakdown>;
};

const emptyDataQuality: DataQuality = {
  market_count: 0,
  selection_count: 0,
  priced_selection_count: 0,
  missing_price_count: 0,
  liquid_selection_count: 0,
  tradeable_selection_count: 0,
  delayed_market_data_count: 0,
  in_play_market_count: 0,
  min_available_size: 2,
  min_market_total_matched: 100,
  price_missing_kill_switch: true,
  liquidity_kill_switch: true,
  delayed_data_kill_switch: false,
  in_play_kill_switch: false,
};

const emptyLatestMarkets: LatestMarkets = {
  snapshot_path: null,
  captured_at: null,
  market_count: 0,
  selection_count: 0,
  data_quality: emptyDataQuality,
  markets: [],
};

const emptyPerformance: PerformanceBreakdown = {
  strategy: [],
  price_bucket: [],
  time_window: [],
};

const emptyStrategyContext: StrategyContext = {
  category: "tennis",
  definition: {
    name: "unknown",
    version: "unknown",
    description: "Strategy context is unavailable.",
    fixed_stake: 0,
    min_hours_to_event: 0,
    max_hours_to_event: 0,
    min_back_price: 0,
    max_back_price: 0,
    max_spread: 0,
    max_snapshot_age_seconds: 0,
    min_market_total_matched: 0,
    min_best_back_size: 0,
    allowed_categories: [],
    allowed_subcategories: [],
    holding_period_hours: 0,
    kill_conditions: [],
    acceptance_min_trades: 0,
    acceptance_min_roi: 0,
    tags: [],
  },
  rules: [],
  recent_snapshot_collections: [],
};

const DEFAULT_BACKEND_TIMEOUT_MS = 9000;
const HEALTH_BACKEND_TIMEOUT_MS = 7000;
const OPTIONAL_BACKEND_TIMEOUT_MS = 5000;

function backendTimeoutMs() {
  const configured = Number(process.env.TRADER_BACKEND_TIMEOUT_MS ?? DEFAULT_BACKEND_TIMEOUT_MS);
  return Number.isFinite(configured) && configured > 0 ? configured : DEFAULT_BACKEND_TIMEOUT_MS;
}

async function backendFetch<T>(path: string, init?: RequestInit, timeoutMs = backendTimeoutMs()): Promise<T> {
  const baseUrl = process.env.TRADER_BACKEND_URL;
  const token = process.env.TRADER_BACKEND_TOKEN;

  if (!baseUrl || !token) {
    throw new Error("Vercel backend connection is not configured.");
  }

  const url = `${baseUrl.replace(/\/$/, "")}${path}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...init,
      cache: "no-store",
      signal: controller.signal,
      headers: {
        "X-Rory-Dashboard-Token": token,
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });

    if (response.ok) {
      return response.json() as Promise<T>;
    }

    const body = await response.text();
    throw new Error(`Backend request failed for ${path}: ${response.status} ${body.slice(0, 240)}`);
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(`Backend request timed out for ${path} after ${timeoutMs}ms.`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function optionalBackendFetch<T>(
  path: string,
  fallback: T,
  issues?: BackendFetchIssue[],
  timeoutMs?: number,
): Promise<T> {
  try {
    return await backendFetch<T>(path, undefined, timeoutMs);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.warn(message);
    issues?.push({ path, message });
    return fallback;
  }
}

function normalizeOverview(overview: Partial<Overview> | undefined): Overview {
  return {
    journal_events: 0,
    executed_positions: 0,
    open_positions: 0,
    closed_positions: 0,
    won_positions: 0,
    lost_positions: 0,
    void_positions: 0,
    marked_open_positions: 0,
    total_stake: 0,
    total_commission_paid: 0,
    total_realized_pnl: 0,
    total_unrealized_pnl: 0,
    total_net_pnl: 0,
    latest_strategy_decisions: 0,
    latest_strategy_acceptances: 0,
    latest_strategy_rejections: 0,
    latest_strategy_snapshots_seen: 0,
    ...(overview ?? {}),
  };
}

function normalizeHealth(health: Partial<Health> | undefined): Health {
  const source = health ?? {};
  return {
    status: source.status ?? "unknown",
    checked_at: source.checked_at ?? new Date(0).toISOString(),
    betfair: {
      ok: source.betfair?.ok ?? null,
      approval_status: source.betfair?.approval_status ?? "not_checked",
      message: source.betfair?.message ?? "Backend health did not include Betfair status.",
    },
    snapshots: {
      latest_snapshot_modified_at: source.snapshots?.latest_snapshot_modified_at ?? null,
      snapshot_age_seconds: source.snapshots?.snapshot_age_seconds ?? null,
      stale: source.snapshots?.stale ?? true,
      stale_after_seconds: source.snapshots?.stale_after_seconds ?? 1800,
    },
    data_quality: {
      ...emptyDataQuality,
      ...(source.data_quality ?? {}),
    },
    supports_live_execution: source.supports_live_execution ?? false,
    live_enabled: source.live_enabled ?? false,
    live_execution_available: source.live_execution_available ?? false,
  };
}

function normalizePerformance(performance: Partial<PerformanceBreakdown> | undefined): PerformanceBreakdown {
  return {
    strategy: performance?.strategy ?? [],
    price_bucket: performance?.price_bucket ?? [],
    time_window: performance?.time_window ?? [],
  };
}

export async function getDashboardData() {
  const backendIssues: BackendFetchIssue[] = [];
  const [health, summary, latestMarkets, pnlSeries, strategyContext] = await Promise.all([
    optionalBackendFetch<Health>("/api/health", normalizeHealth(undefined), backendIssues, HEALTH_BACKEND_TIMEOUT_MS),
    optionalBackendFetch<DashboardSummary>(
      "/api/dashboard/summary?open_limit=12&closed_limit=8&recent_limit=12&decision_limit=100",
      {},
      backendIssues,
    ),
    optionalBackendFetch<LatestMarkets>(
      "/api/dashboard/latest-markets",
      emptyLatestMarkets,
      backendIssues,
      OPTIONAL_BACKEND_TIMEOUT_MS,
    ),
    optionalBackendFetch<{ points: PnlPoint[] }>(
      "/api/dashboard/pnl-series?limit=160",
      { points: [] },
      backendIssues,
      OPTIONAL_BACKEND_TIMEOUT_MS,
    ),
    optionalBackendFetch<StrategyContext>(
      "/api/dashboard/strategy-context",
      emptyStrategyContext,
      backendIssues,
      OPTIONAL_BACKEND_TIMEOUT_MS,
    ),
  ]);

  return {
    health: normalizeHealth(health),
    overview: normalizeOverview(summary.overview),
    openPositions: summary.open_positions ?? [],
    closedPositions: summary.closed_positions ?? [],
    recentEvents: summary.recent_events ?? [],
    latestMarkets,
    pnlPoints: pnlSeries.points,
    performance: normalizePerformance(summary.performance),
    strategyContext,
    strategyEvaluation: summary.strategy_evaluation ?? null,
    strategyDecisions: summary.strategy_decisions ?? [],
    backendIssues,
  };
}
