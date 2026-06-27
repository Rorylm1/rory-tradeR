import { Activity, Clock3, Database, ShieldCheck } from "lucide-react";
import type { LatestMarkets, Overview, Position } from "../lib/backend";
import { formatDateTime, formatMoney, formatWholeNumber } from "./format";
import { MarketTable } from "./market-table";
import { PositionTable } from "./position-table";

function GuardBadge({ guarded }: { guarded: boolean }) {
  return (
    <span className={guarded ? "decision-badge rejected" : "decision-badge accepted"}>
      {guarded ? "Guarded" : "Tradable"}
    </span>
  );
}

export function TradingCockpit({
  openPositions,
  openPositionsUnavailable = false,
  latestMarkets,
  overview,
  publicReadOnly,
}: {
  openPositions: Position[];
  openPositionsUnavailable?: boolean;
  latestMarkets: LatestMarkets;
  overview: Overview;
  publicReadOnly: boolean;
}) {
  const quality = latestMarkets.data_quality;
  const guarded =
    quality.tradeable_selection_count === 0 ||
    quality.price_missing_kill_switch ||
    quality.liquidity_kill_switch ||
    quality.delayed_data_kill_switch ||
    quality.in_play_kill_switch;

  return (
    <section className="cockpit-grid" aria-label="Paper trading cockpit">
      <section className="panel cockpit-panel">
        <div className="panel-heading cockpit-heading">
          <div>
            <h2>Open Paper Bets</h2>
            <p>
              {overview.open_positions} open / {overview.marked_open_positions} marked from the latest snapshot
            </p>
          </div>
          <div className="cockpit-total">
            <span>Unrealized</span>
            <strong>{formatMoney(overview.total_unrealized_pnl)}</strong>
          </div>
        </div>
        <div className="cockpit-strip">
          <span>
            <Activity size={16} aria-hidden="true" />
            {overview.executed_positions} filled
          </span>
          <span>
            <ShieldCheck size={16} aria-hidden="true" />
            paper only
          </span>
          <span>
            <Clock3 size={16} aria-hidden="true" />
            {overview.closed_positions} settled
          </span>
        </div>
        <PositionTable
          positions={openPositions}
          publicReadOnly={publicReadOnly}
          limit={12}
          emptyLabel={openPositionsUnavailable ? "Open paper bets are temporarily unavailable." : "No open paper bets yet."}
        />
      </section>

      <section className="panel cockpit-panel">
        <div className="panel-heading cockpit-heading">
          <div>
            <h2>Saved Tennis Markets</h2>
            <p>
              {latestMarkets.market_count} markets / {latestMarkets.selection_count} runners / saved{" "}
              {formatDateTime(latestMarkets.captured_at)}
            </p>
          </div>
          <GuardBadge guarded={guarded} />
        </div>
        <div className="cockpit-strip">
          <span>
            <Database size={16} aria-hidden="true" />
            {quality.tradeable_selection_count} usable
          </span>
          <span>{quality.missing_price_count} missing prices</span>
          <span>{formatWholeNumber(quality.min_market_total_matched)} min matched</span>
        </div>
        <MarketTable markets={latestMarkets.markets} limit={16} emptyLabel="No saved tennis markets yet." />
      </section>
    </section>
  );
}
