"use client";

import { RefreshCw, ShieldCheck } from "lucide-react";
import { useState } from "react";
import type { LiveOdds } from "../lib/backend";
import { MarketExplorer } from "./market-explorer";

const LIVE_ODDS_CATEGORY = "tennis";
const LIVE_ODDS_MAX_RESULTS = 50;

function dateTime(value: string | null | undefined) {
  if (!value) return "n/a";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}

export function LiveOddsPanel() {
  const [liveOdds, setLiveOdds] = useState<LiveOdds | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setPending(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        category: LIVE_ODDS_CATEGORY,
        max_results: String(LIVE_ODDS_MAX_RESULTS),
      });
      const response = await fetch(`/api/backend/api/dashboard/live-odds?${params}`, {
        cache: "no-store",
      });
      const payload = (await response.json()) as LiveOdds | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload && payload.error ? payload.error : "Live odds request failed.");
      }
      setLiveOdds(payload as LiveOdds);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Live odds request failed.");
    } finally {
      setPending(false);
    }
  }

  const quality = liveOdds?.data_quality;
  const guarded =
    !liveOdds ||
    liveOdds.error !== null ||
    quality?.tradeable_selection_count === 0 ||
    quality?.price_missing_kill_switch ||
    quality?.delayed_data_kill_switch ||
    quality?.in_play_kill_switch;

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Tennis 50 Odds</h2>
          <p>
            {liveOdds
              ? `${liveOdds.market_count} Betfair ${liveOdds.category} markets fetched ${dateTime(liveOdds.fetched_at)}`
              : `Read-only Betfair ${LIVE_ODDS_CATEGORY} / ${LIVE_ODDS_MAX_RESULTS} refresh. No live bet endpoint exists.`}
          </p>
        </div>
        <button className="icon-button" type="button" onClick={refresh} disabled={pending}>
          <RefreshCw size={16} />
          <span>{pending ? "Refreshing" : `Refresh ${LIVE_ODDS_CATEGORY} ${LIVE_ODDS_MAX_RESULTS}`}</span>
        </button>
      </div>

      <div className="live-odds-strip">
        <div>
          <ShieldCheck size={18} />
          <span>{liveOdds?.betfair.message ?? "Betfair auth will be checked when you refresh."}</span>
        </div>
        <span className={guarded ? "decision-badge rejected" : "decision-badge accepted"}>
          {guarded ? "Guarded" : "Fresh read-only odds"}
        </span>
        {quality ? (
          <span className="secondary-cell">
            {quality.tradeable_selection_count} usable / {quality.missing_price_count} missing prices
          </span>
        ) : null}
      </div>

      {error ? <div className="empty-state">{error}</div> : null}
      {liveOdds?.error ? <div className="empty-state">{liveOdds.error}</div> : null}
      {liveOdds && liveOdds.markets.length > 0 ? (
        <MarketExplorer markets={liveOdds.markets} scopeLabel={`${liveOdds.category} / ${liveOdds.max_results}`} />
      ) : !error && !liveOdds?.error ? (
        <div className="empty-state">Click refresh to fetch current read-only Betfair tennis odds.</div>
      ) : null}
    </section>
  );
}
