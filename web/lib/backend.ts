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
  supports_live_execution: boolean;
  live_enabled: boolean;
  live_execution_available: boolean;
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
    throw new Error(`Backend request failed: ${response.status} ${body}`);
  }

  return response.json() as Promise<T>;
}

export async function getDashboardData() {
  const [health, overview, openPositions, closedPositions, recentEvents] = await Promise.all([
    backendFetch<Health>("/api/health"),
    backendFetch<{ overview: Overview }>("/api/dashboard/overview"),
    backendFetch<{ positions: Position[] }>("/api/dashboard/open-positions"),
    backendFetch<{ positions: Position[] }>("/api/dashboard/closed-positions"),
    backendFetch<{ events: RecentEvent[] }>("/api/dashboard/recent-events"),
  ]);

  return {
    health,
    overview: overview.overview,
    openPositions: openPositions.positions,
    closedPositions: closedPositions.positions,
    recentEvents: recentEvents.events,
  };
}

