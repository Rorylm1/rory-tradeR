import type { MarketRow } from "../lib/backend";

function number(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "n/a";
  return value.toFixed(digits);
}

function moneySize(value: number | null | undefined) {
  if (value === null || value === undefined) return "n/a";
  return new Intl.NumberFormat("en-GB", {
    maximumFractionDigits: 0,
  }).format(value);
}

function dateTime(value: string | null | undefined) {
  if (!value) return "n/a";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function MarketTable({
  markets,
  limit = 30,
  emptyLabel = "No market rows yet.",
}: {
  markets: MarketRow[];
  limit?: number;
  emptyLabel?: string;
}) {
  if (markets.length === 0) {
    return <div className="empty-state">{emptyLabel}</div>;
  }

  return (
    <div className="table-wrap">
      <table className="market-table">
        <thead>
          <tr>
            <th>Event</th>
            <th>Selection</th>
            <th>Price</th>
            <th>Liquidity</th>
            <th>Start</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {markets.slice(0, limit).map((row) => (
            <tr key={`${row.market_id}-${row.selection_id}`}>
              <td>
                <span className="primary-cell">{row.event_name ?? row.market_title}</span>
                <span className="secondary-cell">{row.competition_name ?? row.market_title}</span>
              </td>
              <td>
                <span className="primary-cell">{row.selection_name}</span>
                <span className="secondary-cell">{row.subcategory}</span>
              </td>
              <td>
                <span className="primary-cell">back {number(row.best_back)}</span>
                <span className="secondary-cell">
                  lay {number(row.best_lay)} / last {number(row.last_traded)}
                </span>
              </td>
              <td>
                <span className="primary-cell">matched {moneySize(row.market_total_matched)}</span>
                <span className="secondary-cell">
                  back size {moneySize(row.best_back_size)} / lay size {moneySize(row.best_lay_size)}
                </span>
              </td>
              <td>{dateTime(row.event_start)}</td>
              <td>
                <span className={row.in_play ? "decision-badge rejected" : "decision-badge accepted"}>
                  {row.in_play ? "In-play" : "Pre-match"}
                </span>
                {row.is_market_data_delayed ? (
                  <span className="secondary-cell">Delayed data</span>
                ) : (
                  <span className="secondary-cell">{row.status}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {markets.length > limit ? <div className="table-note">Showing {limit} of {markets.length} rows.</div> : null}
    </div>
  );
}
