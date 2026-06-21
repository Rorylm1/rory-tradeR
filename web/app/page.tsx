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
import { getDashboardData, PnlPoint, Position, RecentEvent } from "../lib/backend";
import { LiveOddsPanel } from "./live-odds-panel";
import { LiveReviewButtons } from "./live-review-buttons";
import { PaperSessionPanel } from "./paper-session-panel";
import { WhatIsGoingOnPanel } from "./what-is-going-on-panel";

export const dynamic = "force-dynamic";

function money(value: number | null | undefined) {
  if (value === null || value === undefined) return "n/a";
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    maximumFractionDigits: 2,
  }).format(value);
}

function number(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "n/a";
  return value.toFixed(digits);
}

function dateTime(value: string | null | undefined) {
  if (!value) return "n/a";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

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

function PositionTable({
  positions,
  closed = false,
  publicReadOnly = false,
}: {
  positions: Position[];
  closed?: boolean;
  publicReadOnly?: boolean;
}) {
  if (positions.length === 0) {
    return <div className="empty-state">No {closed ? "closed" : "open"} positions yet.</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Event</th>
            <th>Selection</th>
            <th>Stake</th>
            <th>Entry</th>
            <th>{closed ? "Realized" : "Mark"}</th>
            <th>{closed ? "Outcome" : "Unrealized"}</th>
            <th>Start</th>
            {!closed ? <th>Review</th> : null}
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => (
            <tr key={position.proposal_id}>
              <td>
                <span className="primary-cell">{position.event_name ?? position.market_title}</span>
                <span className="secondary-cell">{position.competition_name ?? position.market_title}</span>
              </td>
              <td>
                <span className="primary-cell">{position.selection_name}</span>
                <span className="secondary-cell">{position.side}</span>
              </td>
              <td>{money(position.stake)}</td>
              <td>{number(position.fill_price)}</td>
              <td>{closed ? money(position.realized_pnl) : number(position.mark_price)}</td>
              <td>{closed ? position.resolved_outcome ?? "n/a" : money(position.unrealized_pnl)}</td>
              <td>{dateTime(position.event_start)}</td>
              {!closed ? (
                <td>
                  <LiveReviewButtons
                    proposalId={position.proposal_id}
                    currentStatus={position.live_review?.status}
                    readOnly={publicReadOnly}
                  />
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
          <span>{dateTime(event.recorded_at)}</span>
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
        <span>{dateTime(points[0].recorded_at)}</span>
        <strong>{money(latest.cumulative_realized_pnl)}</strong>
        <span>{dateTime(latest.recorded_at)}</span>
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
          <span>Last snapshot: {dateTime(health.snapshots.latest_snapshot_modified_at)}</span>
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
        <Metric label="Net PnL" value={money(overview.total_net_pnl)} icon={TrendingUp} />
        <Metric label="Realized PnL" value={money(overview.total_realized_pnl)} icon={CheckCircle2} />
        <Metric label="Unrealized PnL" value={money(overview.total_unrealized_pnl)} icon={Activity} />
        <Metric label="Open positions" value={String(overview.open_positions)} icon={Activity} />
        <Metric label="Saved markets" value={String(latestMarkets.market_count)} icon={Database} />
        <Metric label="Usable odds" value={String(latestMarkets.data_quality.tradeable_selection_count)} icon={CheckCircle2} />
      </section>

      <PaperSessionPanel readOnly={publicReadOnly} />
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

      <section className="panel">
        <div className="panel-heading">
          <h2>Open Positions</h2>
          <p>{overview.marked_open_positions} marked from latest snapshot</p>
        </div>
        <PositionTable positions={openPositions} publicReadOnly={publicReadOnly} />
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
