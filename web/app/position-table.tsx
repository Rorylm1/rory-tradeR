import type { Position } from "../lib/backend";
import { formatDateTime, formatMoney, formatNumber } from "./format";
import { LiveReviewButtons } from "./live-review-buttons";

export function PositionTable({
  positions,
  closed = false,
  publicReadOnly = false,
  limit,
  emptyLabel,
}: {
  positions: Position[];
  closed?: boolean;
  publicReadOnly?: boolean;
  limit?: number;
  emptyLabel?: string;
}) {
  if (positions.length === 0) {
    return <div className="empty-state">{emptyLabel ?? `No ${closed ? "closed" : "open"} positions yet.`}</div>;
  }

  const visiblePositions = limit ? positions.slice(0, limit) : positions;

  return (
    <div className="table-wrap">
      <table className="position-table">
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
          {visiblePositions.map((position) => (
            <tr key={position.proposal_id}>
              <td>
                <span className="primary-cell">{position.event_name ?? position.market_title}</span>
                <span className="secondary-cell">{position.competition_name ?? position.market_title}</span>
              </td>
              <td>
                <span className="primary-cell">{position.selection_name}</span>
                <span className="secondary-cell">{position.reason ?? position.side}</span>
              </td>
              <td>{formatMoney(position.stake)}</td>
              <td>{formatNumber(position.fill_price)}</td>
              <td>{closed ? formatMoney(position.realized_pnl) : formatNumber(position.mark_price)}</td>
              <td>{closed ? position.resolved_outcome ?? "n/a" : formatMoney(position.unrealized_pnl)}</td>
              <td>{formatDateTime(position.event_start)}</td>
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
      {limit && positions.length > limit ? (
        <div className="table-note">Showing {limit} of {positions.length} positions.</div>
      ) : null}
    </div>
  );
}
