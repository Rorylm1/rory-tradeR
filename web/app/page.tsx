import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  Lock,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { getDashboardData, PnlPoint, RecentEvent } from "../lib/backend";
import { formatDateTime, formatMoney } from "./format";
import { LiveOddsPanel } from "./live-odds-panel";
import { PaperSessionPanel } from "./paper-session-panel";
import { PositionTable } from "./position-table";
import { TradingCockpit } from "./trading-cockpit";
import { WhatIsGoingOnPanel } from "./what-is-going-on-panel";

export const dynamic = "force-dynamic";

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return <span className={ok ? "pill good" : "pill warn"}>{label}</span>;
}

function Metric({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: typeof Activity;
}) {
  return (
    <section className="metric">
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
      </div>
      <Icon size={22} aria-hidden="true" />
    </section>
  );
}

function EventFeed({ events }: { events: RecentEvent[] }) {
  if (events.length === 0) {
    return <div className="empty-state">No journal activity yet.</div>;
  }

  return (
    <ol className="event-feed">
      {events.slice(0, 12).map((event, index) => (
        <li key={`${event.recorded_at}-${index}`}>
          <span className="event-type">{event.event_type}</span>
          <span>{formatDateTime(event.recorded_at)}</span>
        </li>
      ))}
    </ol>
  );
}

function PnlChart({ points }: { points: PnlPoint[] }) {
  if (points.length === 0) {
    return <div className="empty-state">No PnL history yet.</div>;
  }

  const width = 640;
  const height = 180;
  const padding = 24;
  const values = points.map((point) => point.cumulative_realized_pnl);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const span = Math.max(max - min, 1);
  const coordinates = points.map((point, index) => {
    const x = padding + (index / Math.max(points.length - 1, 1)) * (width - padding * 2);
    const y = height - padding - ((point.cumulative_realized_pnl - min) / span) * (height - padding * 2);
    return { x, y, point };
  });
  const polyline = coordinates.map(({ x, y }) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const zeroY = height - padding - ((0 - min) / span) * (height - padding * 2);
  const latest = points[points.length - 1];

  return (
    <div className="chart-panel">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Realized PnL over time">
        <line x1={padding} y1={zeroY} x2={width - padding} y2={zeroY} className="chart-zero" />
        <polyline points={polyline} className="chart-line" />
        {coordinates.map(({ x, y, point }) => (
          <circle key={`${point.recorded_at}-${point.event_type}`} cx={x} cy={y} r="3.5" className="chart-dot" />
        ))}
      </svg>
      <div className="chart-meta">
        <span>{formatDateTime(points[0].recorded_at)}</span>
        <strong>{formatMoney(latest.cumulative_realized_pnl)}</strong>
        <span>{formatDateTime(latest.recorded_at)}</span>
      </div>
    </div>
  );
}

export default async function DashboardPage() {
  const authEnabled = process.env.DASHBOARD_BASIC_AUTH_ENABLED === "true";
  const publicReadOnly = !authEnabled || process.env.DASHBOARD_PUBLIC_READ_ONLY === "true";
  let data: Awaited<ReturnType<typeof getDashboardData>>;
  try {
    data = await getDashboardData();
  } catch (error) {
    return (
      <main className="shell">
        <section className="error-panel">
          <AlertTriangle size={28} />
          <div>
            <h1>Dashboard backend unavailable</h1>
            <p>{error instanceof Error ? error.message : "Unknown backend error."}</p>
          </div>
        </section>
      </main>
    );
  }

  const {
    health,
    overview,
    openPositions,
    closedPositions,
    recentEvents,
    latestMarkets,
    pnlPoints,
    performance,
    strategyContext,
    strategyEvaluation,
    strategyDecisions,
  } = data;
  const betfairReady = health.betfair.ok === true;
  const dataFresh = !health.snapshots.stale;
  const oddsUsable =
    dataFresh &&
    health.data_quality.tradeable_selection_count > 0 &&
    !health.data_quality.price_missing_kill_switch &&
    !health.data_quality.delayed_data_kill_switch &&
    !health.data_quality.in_play_kill_switch;
  const liveDisabled = !health.live_execution_available && !health.live_enabled;

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>Rory TradeR</h1>
          <p>Tennis Betfair paper monitor</p>
        </div>
        <div className="status-row">
          <StatusPill ok label="Tennis paper" />
          <StatusPill ok={betfairReady} label={betfairReady ? "Betfair ready" : health.betfair.approval_status} />
          <StatusPill ok={dataFresh} label={dataFresh ? "Data fresh" : "Data stale"} />
          <StatusPill ok={oddsUsable} label={oddsUsable ? "Odds usable" : "Odds guarded"} />
          <StatusPill ok={liveDisabled} label={liveDisabled ? "Live disabled" : "Live enabled"} />
        </div>
      </header>

      <section className="health-strip">
        <div>
          <ShieldCheck size={18} />
          <span>{health.betfair.message}</span>
        </div>
        <div>
          <Clock3 size={18} />
          <span>Last snapshot: {formatDateTime(health.snapshots.latest_snapshot_modified_at)}</span>
        </div>
        <div>
          <Database size={18} />
          <span>
            {health.data_quality.tradeable_selection_count} usable runners / {health.data_quality.missing_price_count} missing prices
          </span>
        </div>
        <div>
          <Lock size={18} />
          <span>Review controls only. No live order endpoint exists.</span>
        </div>
      </section>

      <section className="metrics-grid">
        <Metric label="Net PnL" value={formatMoney(overview.total_net_pnl)} icon={TrendingUp} />
        <Metric label="Realized PnL" value={formatMoney(overview.total_realized_pnl)} icon={CheckCircle2} />
        <Metric label="Unrealized PnL" value={formatMoney(overview.total_unrealized_pnl)} icon={Activity} />
        <Metric label="Open positions" value={String(overview.open_positions)} icon={Activity} />
        <Metric label="Saved markets" value={String(latestMarkets.market_count)} icon={Database} />
        <Metric label="Usable odds" value={String(latestMarkets.data_quality.tradeable_selection_count)} icon={CheckCircle2} />
      </section>

      <PaperSessionPanel readOnly={publicReadOnly} />
      <TradingCockpit
        openPositions={openPositions}
        latestMarkets={latestMarkets}
        overview={overview}
        publicReadOnly={publicReadOnly}
      />
      <LiveOddsPanel />

      <WhatIsGoingOnPanel
        context={strategyContext}
        evaluation={strategyEvaluation}
        decisions={strategyDecisions}
        latestMarkets={latestMarkets}
        performance={performance}
        overview={overview}
      />

      <section className="panel">
        <div className="panel-heading">
          <h2>PnL Over Time</h2>
          <p>Realized journal PnL</p>
        </div>
        <PnlChart points={pnlPoints} />
      </section>

      <section className="split-grid">
        <section className="panel">
          <div className="panel-heading">
            <h2>Recent Activity</h2>
            <p>Append-only journal</p>
          </div>
          <EventFeed events={recentEvents} />
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Closed Positions</h2>
            <p>{overview.closed_positions} settled</p>
          </div>
          <PositionTable positions={closedPositions.slice(0, 8)} closed publicReadOnly={publicReadOnly} />
        </section>
      </section>
    </main>
  );
}
