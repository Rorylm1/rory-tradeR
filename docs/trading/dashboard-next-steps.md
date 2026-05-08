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

## Current Behavior

- The market explorer is snapshot-live, not streaming-live.
- Fresh data is produced by supervised CLI runs such as:

```bash
uv run main.py paper tennis 25
```

- The dashboard then reads the latest saved snapshot and journal state.
- Live order execution remains disabled. The dashboard is still review-only.

## Latest Tennis Observation

The 2026-05-08 tennis paper run collected 25 markets and 98 runners. The strategy accepted 0 signals and rejected 25. The dominant rejection reason was `event_start_too_soon`, because the current strategy requires a longer lead time before event start.

## Recommended Next Steps

1. Add a supervised dashboard refresh button that runs a paper-only tennis snapshot collection and clearly reports success, failure, and freshness.
2. Narrow tennis discovery to high-signal market types first, especially match odds and set winner markets. Avoid in-play game markets until they are intentionally supported.
3. Add odds history per market from saved snapshots so the dashboard can show price movement, not just the latest point.
4. Add liquidity and traded-volume fields to Betfair normalization, then filter out thin or unusable markets.
5. Add explicit stale-data, auth-failure, and price-missing kill switches before any scheduled paper monitoring exists.
6. Add replay from saved snapshots so strategy changes can be compared deterministically.
7. Later, consider scheduled paper-only monitoring. Keep live execution disabled until the paper evidence and safety controls justify a separate go/no-go decision.
