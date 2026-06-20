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

export type PnlPoint = {
  recorded_at: string;
  event_type: string;
  cumulative_realized_pnl: number;
  cumulative_stake: number;
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

async function backendFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = process.env.TRADER_BACKEND_URL;
  const token = process.env.TRADER_BACKEND_TOKEN;

  if (!baseUrl || !token) {
    throw new Error("Vercel backend connection is not configured.");
  }

  const response = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "X-Rory-Dashboard-Token": token,
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Backend request failed for ${path}: ${response.status} ${body}`);
  }

  return response.json() as Promise<T>;
}

async function optionalBackendFetch<T>(path: string, fallback: T): Promise<T> {
  try {
    return await backendFetch<T>(path);
  } catch (error) {
    console.warn(error instanceof Error ? error.message : error);
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

export async function getDashboardData() {
  const [
    health,
    overview,
    openPositions,
    closedPositions,
    recentEvents,
    latestMarkets,
    pnlSeries,
    strategyDecisions,
  ] = await Promise.all([
    backendFetch<Health>("/api/health"),
    backendFetch<{ overview: Overview }>("/api/dashboard/overview"),
    backendFetch<{ positions: Position[] }>("/api/dashboard/open-positions"),
    backendFetch<{ positions: Position[] }>("/api/dashboard/closed-positions"),
    backendFetch<{ events: RecentEvent[] }>("/api/dashboard/recent-events"),
    optionalBackendFetch<LatestMarkets>("/api/dashboard/latest-markets", emptyLatestMarkets),
    optionalBackendFetch<{ points: PnlPoint[] }>("/api/dashboard/pnl-series", { points: [] }),
    optionalBackendFetch<{ evaluation: StrategyEvaluation; decisions: StrategyDecision[] }>(
      "/api/dashboard/strategy-decisions",
      { evaluation: null, decisions: [] },
    ),
  ]);

  return {
    health,
    overview: normalizeOverview(overview.overview),
    openPositions: openPositions.positions,
    closedPositions: closedPositions.positions,
    recentEvents: recentEvents.events,
    latestMarkets,
    pnlPoints: pnlSeries.points,
    strategyEvaluation: strategyDecisions.evaluation,
    strategyDecisions: strategyDecisions.decisions,
  };
}
