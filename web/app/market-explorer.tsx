"use client";

import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import type { MarketRow } from "../lib/backend";

function number(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "n/a";
  return value.toFixed(digits);
}

function compactNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "n/a";
  return new Intl.NumberFormat("en-GB", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function dateTime(value: string | null | undefined) {
  if (!value) return "n/a";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function isPriced(market: MarketRow) {
  return market.best_back !== null || market.best_lay !== null || market.last_traded !== null;
}

function isLiquid(market: MarketRow) {
  const backSizeOk = market.best_back_size === null || market.best_back_size >= 2;
  const marketMatchedOk = market.market_total_matched === null || market.market_total_matched >= 100;
  return market.best_back !== null && market.best_lay !== null && backSizeOk && marketMatchedOk;
}

type MarketGroup = {
  market_id: string;
  event_name: string | null;
  competition_name: string | null;
  market_title: string;
  subcategory: string;
  event_start: string | null;
  status: string;
  runners: MarketRow[];
  priced: boolean;
  liquid: boolean;
  market_total_matched: number | null;
  in_play: boolean | null;
  is_market_data_delayed: boolean | null;
};

function runnerKey(market: MarketRow) {
  return [
    market.selection_id,
    market.selection_name,
    market.best_back ?? "",
    market.best_lay ?? "",
    market.last_traded ?? "",
  ].join("|");
}

function groupMarkets(markets: MarketRow[]): MarketGroup[] {
  const groups = new Map<string, MarketGroup>();

  for (const market of markets) {
    const group = groups.get(market.market_id) ?? {
      market_id: market.market_id,
      event_name: market.event_name,
      competition_name: market.competition_name,
      market_title: market.market_title,
      subcategory: market.subcategory,
      event_start: market.event_start,
      status: market.status,
      runners: [],
      priced: false,
      liquid: false,
      market_total_matched: market.market_total_matched,
      in_play: market.in_play,
      is_market_data_delayed: market.is_market_data_delayed,
    };
    const existingRunnerKeys = new Set(group.runners.map(runnerKey));
    if (!existingRunnerKeys.has(runnerKey(market))) {
      group.runners.push(market);
    }
    group.priced = group.priced || isPriced(market);
    group.liquid = group.liquid || isLiquid(market);
    groups.set(market.market_id, group);
  }

  return Array.from(groups.values());
}

export function MarketExplorer({ markets }: { markets: MarketRow[] }) {
  const [query, setQuery] = useState("");
  const [marketTitle, setMarketTitle] = useState("all");
  const [pricedOnly, setPricedOnly] = useState(false);
  const [liquidOnly, setLiquidOnly] = useState(false);

  const marketTitles = useMemo(
    () => Array.from(new Set(markets.map((market) => market.market_title))).sort(),
    [markets],
  );

  const marketGroups = useMemo(() => groupMarkets(markets), [markets]);

  const filteredGroups = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return marketGroups.filter((group) => {
      const matchesTitle = marketTitle === "all" || group.market_title === marketTitle;
      const matchesPriced = !pricedOnly || group.priced;
      const matchesLiquid = !liquidOnly || group.liquid;
      const searchable = [
        group.event_name,
        group.competition_name,
        group.market_title,
        group.subcategory,
        ...group.runners.map((runner) => runner.selection_name),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return matchesTitle && matchesPriced && matchesLiquid && (!normalizedQuery || searchable.includes(normalizedQuery));
    });
  }, [liquidOnly, marketGroups, marketTitle, pricedOnly, query]);

  return (
    <div>
      <div className="explorer-controls">
        <label className="search-control">
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search event, market, selection"
          />
        </label>
        <select value={marketTitle} onChange={(event) => setMarketTitle(event.target.value)}>
          <option value="all">All markets</option>
          {marketTitles.map((title) => (
            <option key={title} value={title}>
              {title}
            </option>
          ))}
        </select>
        <label className="toggle-control">
          <input type="checkbox" checked={pricedOnly} onChange={(event) => setPricedOnly(event.target.checked)} />
          Priced only
        </label>
        <label className="toggle-control">
          <input type="checkbox" checked={liquidOnly} onChange={(event) => setLiquidOnly(event.target.checked)} />
          Liquid only
        </label>
        <span className="control-count">
          {filteredGroups.length} / {marketGroups.length} markets
        </span>
      </div>

      {filteredGroups.length === 0 ? (
        <div className="empty-state">No markets match the current filters.</div>
      ) : (
        <div className="table-wrap">
          <table className="market-table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Market</th>
                <th>Runners</th>
                <th>Best Prices</th>
                <th>Liquidity</th>
                <th>Status</th>
                <th>Start</th>
              </tr>
            </thead>
            <tbody>
              {filteredGroups.slice(0, 40).map((group) => {
                const pricedRunners = group.runners.filter(isPriced);
                const previewRunners = group.runners.slice(0, 4);
                const pricePreview = pricedRunners.slice(0, 3);

                return (
                <tr key={group.market_id}>
                  <td>
                    <span className="primary-cell">{group.event_name ?? group.market_title}</span>
                    <span className="secondary-cell">{group.competition_name ?? group.subcategory}</span>
                  </td>
                  <td>
                    <span className="primary-cell">{group.market_title}</span>
                    <span className="secondary-cell">
                      {group.subcategory} / {group.runners.length} runners
                    </span>
                  </td>
                  <td>
                    <div className="runner-list">
                      {previewRunners.map((runner, index) => (
                        <span className="runner-pill" key={`${runnerKey(runner)}-${index}`}>
                          {runner.selection_name}
                        </span>
                      ))}
                      {group.runners.length > previewRunners.length ? (
                        <span className="runner-pill muted">+{group.runners.length - previewRunners.length}</span>
                      ) : null}
                    </div>
                  </td>
                  <td>
                    {pricePreview.length === 0 ? (
                      <span className="secondary-cell">No priced runners</span>
                    ) : (
                      <div className="price-list">
                        {pricePreview.map((runner, index) => (
                          <span key={`${runnerKey(runner)}-${index}`}>
                            {runner.selection_name}: {number(runner.best_back)} / {number(runner.best_lay)}
                            {runner.best_back_size !== null ? ` (${compactNumber(runner.best_back_size)})` : ""}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td>
                    <span className="primary-cell">{compactNumber(group.market_total_matched)}</span>
                    <span className="secondary-cell">{group.liquid ? "usable" : "thin or incomplete"}</span>
                  </td>
                  <td>
                    <span className={group.priced && group.liquid ? "decision-badge accepted" : "decision-badge rejected"}>
                      {group.is_market_data_delayed
                        ? "Delayed"
                        : group.in_play
                          ? "In-play"
                          : group.priced && group.liquid
                            ? "Live odds"
                            : group.priced
                              ? "Thin"
                              : "No price"}
                    </span>
                  </td>
                  <td>{dateTime(group.event_start)}</td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
