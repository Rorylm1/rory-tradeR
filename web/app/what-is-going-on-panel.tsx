"use client";

import { Activity, BarChart3, Database, ListFilter } from "lucide-react";
import { useState } from "react";
import type {
  LatestMarkets,
  PerformanceBreakdown,
  PerformanceRow,
  StrategyContext,
  StrategyDecision,
  StrategyEvaluation,
} from "../lib/backend";
import { formatDateTime, formatMoney, formatNumber, formatPercent } from "./format";
import { MarketTable } from "./market-table";

type TabKey = "strategy" | "snapshots" | "rejections" | "learning";

const tabs: { key: TabKey; label: string; icon: typeof Activity }[] = [
  { key: "strategy", label: "Strategy", icon: Activity },
  { key: "snapshots", label: "Snapshots", icon: Database },
  { key: "rejections", label: "Rejections", icon: ListFilter },
  { key: "learning", label: "Learning", icon: BarChart3 },
];

function fileName(path: string | undefined) {
  if (!path) return "n/a";
  return path.split("/").filter(Boolean).pop() ?? path;
}

function DecisionBadge({ accepted }: { accepted: boolean }) {
  return (
    <span className={accepted ? "decision-badge accepted" : "decision-badge rejected"}>
      {accepted ? "Accepted" : "Rejected"}
    </span>
  );
}

function MiniMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="mini-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TradeFunnel({
  evaluation,
  overview,
}: {
  evaluation: StrategyEvaluation;
  overview: {
    latest_strategy_snapshots_seen: number;
    latest_strategy_decisions: number;
    latest_strategy_rejections: number;
    latest_strategy_acceptances: number;
    open_positions: number;
    closed_positions: number;
  };
}) {
  const stages = [
    { label: "Markets scanned", value: evaluation?.snapshots_seen ?? overview.latest_strategy_snapshots_seen },
    { label: "Decisions", value: evaluation?.decisions_count ?? overview.latest_strategy_decisions },
    { label: "Rejected", value: evaluation?.rejected_count ?? overview.latest_strategy_rejections },
    { label: "Accepted", value: evaluation?.accepted_count ?? overview.latest_strategy_acceptances },
    { label: "Open positions", value: overview.open_positions },
    { label: "Closed positions", value: overview.closed_positions },
  ];

  return (
    <div className="funnel-steps compact">
      {stages.map((stage) => (
        <div key={stage.label} className="funnel-step">
          <span>{stage.label}</span>
          <strong>{stage.value}</strong>
        </div>
      ))}
    </div>
  );
}

function RejectionBreakdown({ evaluation }: { evaluation: StrategyEvaluation }) {
  const rejectionRows = Object.entries(evaluation?.rejection_counts ?? {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...rejectionRows.map(([, count]) => count), 1);

  if (rejectionRows.length === 0) {
    return <div className="empty-state">No rejection counts recorded yet.</div>;
  }

  return (
    <div className="rejection-bars">
      {rejectionRows.map(([reason, count]) => (
        <div key={reason} className="rejection-bar-row">
          <div>
            <span className="primary-cell">{reason}</span>
            <span className="secondary-cell">{count} rejected</span>
          </div>
          <div className="rejection-bar-track" aria-hidden="true">
            <span style={{ width: `${Math.max(8, (count / max) * 100)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function StrategyDecisionTable({
  decisions,
  accepted,
}: {
  decisions: StrategyDecision[];
  accepted?: boolean;
}) {
  const rows = accepted === undefined ? decisions : decisions.filter((decision) => decision.accepted === accepted);
  if (rows.length === 0) {
    return <div className="empty-state">No matching strategy decisions recorded yet.</div>;
  }

  return (
    <div className="table-wrap">
      <table className="decision-table">
        <thead>
          <tr>
            <th>Market</th>
            <th>Selection</th>
            <th>Decision</th>
            <th>Price</th>
            <th>Reason</th>
            <th>Start</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 60).map((decision, index) => (
            <tr key={`${decision.recorded_at}-${decision.market_id}-${decision.selection_id ?? "market"}-${index}`}>
              <td>
                <span className="primary-cell">{decision.market_title}</span>
                <span className="secondary-cell">{decision.subcategory}</span>
              </td>
              <td>{decision.selection_name ?? "Market"}</td>
              <td>
                <DecisionBadge accepted={decision.accepted} />
              </td>
              <td>
                <span className="primary-cell">{formatNumber(decision.best_back)}</span>
                <span className="secondary-cell">
                  lay {formatNumber(decision.best_lay)} / spread {formatNumber(decision.spread)}
                </span>
              </td>
              <td>
                <span className="primary-cell">{decision.reason_code}</span>
                <span className="secondary-cell">{decision.reason}</span>
              </td>
              <td>{formatDateTime(decision.event_start)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 60 ? <div className="table-note">Showing 60 of {rows.length} decisions.</div> : null}
    </div>
  );
}

function performanceLabel(row: PerformanceRow, group: "strategy" | "price_bucket" | "time_window") {
  if (group === "strategy") {
    const name = row.strategy_name ?? "Strategy";
    return row.strategy_version ? `${name}@${row.strategy_version}` : name;
  }
  if (group === "price_bucket") {
    return row.price_bucket ?? "No price bucket";
  }
  return row.time_window ?? "No time window";
}

function PerformanceTable({
  title,
  rows,
  group,
}: {
  title: string;
  rows: PerformanceRow[];
  group: "strategy" | "price_bucket" | "time_window";
}) {
  if (rows.length === 0) {
    return (
      <section className="learning-block">
        <h3>{title}</h3>
        <div className="empty-state">No paper performance rows yet.</div>
      </section>
    );
  }

  return (
    <section className="learning-block">
      <h3>{title}</h3>
      <div className="table-wrap">
        <table className="learning-table">
          <thead>
            <tr>
              <th>Segment</th>
              <th>Exec</th>
              <th>Closed</th>
              <th>Win</th>
              <th>Conf</th>
              <th>Realized</th>
              <th>Unrealized</th>
              <th>Net</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${group}-${performanceLabel(row, group)}`}>
                <td>
                  <span className="primary-cell">{performanceLabel(row, group)}</span>
                  <span className="secondary-cell">{row.open_positions} open</span>
                </td>
                <td>{row.executed_positions}</td>
                <td>{row.closed_positions}</td>
                <td>{formatPercent(row.win_rate)}</td>
                <td>{formatNumber(row.avg_confidence, 3)}</td>
                <td>{formatMoney(row.total_realized_pnl)}</td>
                <td>{formatMoney(row.total_unrealized_pnl)}</td>
                <td>{formatMoney(row.total_net_pnl)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function StrategyTab({
  context,
  evaluation,
}: {
  context: StrategyContext;
  evaluation: StrategyEvaluation;
}) {
  const definition = context.definition;
  return (
    <div className="insight-section">
      <div className="strategy-summary">
        <div>
          <span className="breakdown-title">Active paper strategy</span>
          <h3>{definition.name}@{definition.version}</h3>
          <p>{definition.description}</p>
        </div>
        <div className="tag-row">
          {definition.tags.map((tag) => (
            <span key={tag} className="runner-pill">{tag}</span>
          ))}
        </div>
      </div>
      <div className="rule-grid">
        {context.rules.map((rule) => (
          <div key={rule.label} className="rule-row">
            <span>{rule.label}</span>
            <strong>{rule.value}</strong>
            <small>{rule.detail}</small>
          </div>
        ))}
      </div>
      <div className="mini-metrics">
        <MiniMetric label="Latest evaluation" value={formatDateTime(evaluation?.recorded_at)} />
        <MiniMetric label="Accepted" value={evaluation?.accepted_count ?? 0} />
        <MiniMetric label="Rejected" value={evaluation?.rejected_count ?? 0} />
        <MiniMetric label="Snapshot max age" value={`${definition.max_snapshot_age_seconds}s`} />
      </div>
    </div>
  );
}

function SnapshotsTab({
  latestMarkets,
}: {
  latestMarkets: LatestMarkets;
}) {
  const quality = latestMarkets.data_quality;
  return (
    <div className="insight-section">
      <div className="mini-metrics">
        <MiniMetric label="Captured" value={formatDateTime(latestMarkets.captured_at)} />
        <MiniMetric label="Markets" value={latestMarkets.market_count} />
        <MiniMetric label="Selections" value={latestMarkets.selection_count} />
        <MiniMetric label="Usable runners" value={quality.tradeable_selection_count} />
        <MiniMetric label="Missing prices" value={quality.missing_price_count} />
        <MiniMetric label="Delayed markets" value={quality.delayed_market_data_count} />
      </div>
      <MarketTable markets={latestMarkets.markets} limit={40} emptyLabel="No saved snapshot rows yet." />
    </div>
  );
}

function SnapshotCollectionsTab({ context }: { context: StrategyContext }) {
  if (context.recent_snapshot_collections.length === 0) {
    return null;
  }

  return (
    <div className="table-wrap">
      <table className="snapshot-table">
        <thead>
          <tr>
            <th>Recorded</th>
            <th>Category</th>
            <th>Snapshots</th>
            <th>File</th>
          </tr>
        </thead>
        <tbody>
          {context.recent_snapshot_collections.map((snapshot) => (
            <tr key={`${snapshot.recorded_at}-${snapshot.snapshot_path}`}>
              <td>{formatDateTime(snapshot.recorded_at)}</td>
              <td>{snapshot.category ?? "n/a"}</td>
              <td>{snapshot.snapshot_count ?? "n/a"}</td>
              <td>{fileName(snapshot.snapshot_path)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RejectionsTab({
  evaluation,
  decisions,
  overview,
}: {
  evaluation: StrategyEvaluation;
  decisions: StrategyDecision[];
  overview: Parameters<typeof TradeFunnel>[0]["overview"];
}) {
  return (
    <div className="insight-section">
      <TradeFunnel evaluation={evaluation} overview={overview} />
      <RejectionBreakdown evaluation={evaluation} />
      <StrategyDecisionTable decisions={decisions} accepted={false} />
    </div>
  );
}

function LearningTab({ performance }: { performance: PerformanceBreakdown }) {
  const rowCount = performance.strategy.length + performance.price_bucket.length + performance.time_window.length;
  if (rowCount === 0) {
    return <div className="empty-state">No paper fills have been grouped yet.</div>;
  }

  return (
    <div className="insight-section">
      <div className="learning-grid">
        <PerformanceTable title="By Strategy" rows={performance.strategy} group="strategy" />
        <PerformanceTable title="By Price" rows={performance.price_bucket} group="price_bucket" />
        <PerformanceTable title="By Time" rows={performance.time_window} group="time_window" />
      </div>
      <div className="empty-state compact-note">
        Closed positions drive win rate and realized PnL. Open positions are mark-to-market only.
      </div>
    </div>
  );
}

export function WhatIsGoingOnPanel({
  context,
  evaluation,
  decisions,
  latestMarkets,
  performance,
  overview,
}: {
  context: StrategyContext;
  evaluation: StrategyEvaluation;
  decisions: StrategyDecision[];
  latestMarkets: LatestMarkets;
  performance: PerformanceBreakdown;
  overview: Parameters<typeof TradeFunnel>[0]["overview"];
}) {
  const [activeTab, setActiveTab] = useState<TabKey>("strategy");
  const rejectedCount = decisions.filter((decision) => !decision.accepted).length;

  return (
    <section className="panel insight-panel">
      <div className="panel-heading">
        <div>
          <h2>What&apos;s Going On</h2>
          <p>
            {context.definition.name}@{context.definition.version} / {latestMarkets.market_count} saved markets /{" "}
            {rejectedCount} visible rejections
          </p>
        </div>
      </div>

      <div className="tab-row" role="tablist" aria-label="Dashboard insight tabs">
        {tabs.map((tabItem) => {
          const Icon = tabItem.icon;
          const active = activeTab === tabItem.key;
          return (
            <button
              key={tabItem.key}
              className={active ? "tab-button active" : "tab-button"}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setActiveTab(tabItem.key)}
            >
              <Icon size={16} />
              <span>{tabItem.label}</span>
            </button>
          );
        })}
      </div>

      <div className="tab-panel" role="tabpanel">
        {activeTab === "strategy" ? <StrategyTab context={context} evaluation={evaluation} /> : null}
        {activeTab === "snapshots" ? (
          <>
            <SnapshotsTab latestMarkets={latestMarkets} />
            <SnapshotCollectionsTab context={context} />
          </>
        ) : null}
        {activeTab === "rejections" ? (
          <RejectionsTab evaluation={evaluation} decisions={decisions} overview={overview} />
        ) : null}
        {activeTab === "learning" ? <LearningTab performance={performance} /> : null}
      </div>
    </section>
  );
}
