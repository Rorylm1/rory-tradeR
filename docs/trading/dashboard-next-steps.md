# Dashboard Cockpit Iteration Log

Date: 2026-05-08

## Shipped

- Added a dashboard market explorer for the latest Betfair paper snapshot.
- Grouped duplicate runner rows into market-level rows with runner pills, price summaries, and priced/no-price status.
- Added search, market-type filtering, and priced-only filtering.
- Added a realized PnL over time chart from the journal.
- Added a strategy decision trail so accepted and rejected paper signals are visible.
- Added rejection counts to the dashboard overview.
- Added API coverage for latest markets, PnL series, and strategy decisions.
- Added Betfair liquidity and traded-volume fields to normalized snapshots.
- Added dashboard data-quality gates for freshness, missing prices, delayed market data, in-play markets, and thin books.
- Added paper-strategy and paper-broker stale snapshot checks so stale or timestamp-missing data fails closed.
- Narrowed tennis discovery to higher-signal market types by default: `MATCH_ODDS` and `SET_WINNER`.
- Added a read-only live odds endpoint and dashboard panel for operator-triggered Betfair refreshes.

## Current Behavior

- The market explorer is snapshot-live, not streaming-live.
- Fresh data is produced by supervised CLI runs such as:

```bash
uv run main.py paper tennis 25
```

- The dashboard then reads the latest saved snapshot and journal state.
- Live order execution remains disabled. The dashboard is still review-only.
- Live Betfair odds can be fetched on demand with the dashboard refresh button, but no live order endpoint exists.

## Latest Tennis Observation

The 2026-05-08 tennis paper run collected 25 markets and 98 runners. The strategy accepted 0 signals and rejected 25. The dominant rejection reason was `event_start_too_soon`, because the current strategy requires a longer lead time before event start.

## Recommended Next Steps

1. Add odds history per market from saved snapshots so the dashboard can show price movement, not just the latest point.
2. Add replay from saved snapshots so strategy changes can be compared deterministically.
3. Add max exposure and max daily loss controls before any manual-assisted live discussion.
4. Review live odds and paper results after the liquidity filters are active, then record a go/no-go note for whether tiny manual-assisted live work is justified.
5. Later, consider scheduled paper-only monitoring. Keep live execution disabled until the paper evidence and safety controls justify a separate go/no-go decision.
