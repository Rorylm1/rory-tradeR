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
import { getDashboardData, Position, RecentEvent } from "../lib/backend";
import { LiveReviewButtons } from "./live-review-buttons";

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

function PositionTable({ positions, closed = false }: { positions: Position[]; closed?: boolean }) {
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

export default async function DashboardPage() {
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

  const { health, overview, openPositions, closedPositions, recentEvents } = data;
  const betfairReady = health.betfair.ok === true;
  const dataFresh = !health.snapshots.stale;
  const liveDisabled = !health.live_execution_available && !health.live_enabled;

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>Rory TradeR</h1>
          <p>Betfair paper-trading monitor</p>
        </div>
        <div className="status-row">
          <StatusPill ok={betfairReady} label={betfairReady ? "Betfair ready" : health.betfair.approval_status} />
          <StatusPill ok={dataFresh} label={dataFresh ? "Data fresh" : "Data stale"} />
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
          <Lock size={18} />
          <span>Review controls only. No live order endpoint exists.</span>
        </div>
      </section>

      <section className="metrics-grid">
        <Metric label="Net PnL" value={money(overview.total_net_pnl)} icon={TrendingUp} />
        <Metric label="Open positions" value={String(overview.open_positions)} icon={Activity} />
        <Metric label="Total stake" value={money(overview.total_stake)} icon={Database} />
        <Metric label="Journal events" value={String(overview.journal_events)} icon={CheckCircle2} />
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Open Positions</h2>
          <p>{overview.marked_open_positions} marked from latest snapshot</p>
        </div>
        <PositionTable positions={openPositions} />
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
          <PositionTable positions={closedPositions.slice(0, 8)} closed />
        </section>
      </section>
    </main>
  );
}
