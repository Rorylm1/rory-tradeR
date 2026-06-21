# Strategy and Paper Trading Spec

## Scope

This document defines the first paper-trading boundary for `rory-tradeR`.

## First Milestone Rules

- strategies may emit versioned normalized trade intents
- all fills must happen in paper mode only
- journals must be append-only
- replay should be deterministic from saved snapshots

## Normalized Market Model

Each tradable outcome should map to:
- `exchange`
- `market_id`
- `selection_id`
- `market_title`
- `selection_name`
- `category`
- `subcategory`
- `event_start`
- `best_back`
- `best_lay`
- `last_traded`
- `status`
- `raw_payload`

## Paper Execution Rules

- simulate fills against best available price
- apply configurable slippage and commission and record both on each paper fill
- reject intents that exceed per-trade, per-market exposure, or daily-loss limits
- stop if market data is stale or auth state is unhealthy
- version strategy rules so journaled results stay comparable over time
- avoid short-horizon reactive strategies while only delayed odds are assumed

## Risk Defaults

- commission: `2%` of stake by default (`RORY_TRADER_PAPER_COMMISSION_RATE=0.02`)
- slippage: `25` basis points of decimal odds by default (`RORY_TRADER_PAPER_SLIPPAGE_BPS=25`)
- max stake per trade: `10` (`RORY_TRADER_MAX_STAKE_PER_TRADE=10`)
- max open exposure per market: `20` (`RORY_TRADER_MAX_MARKET_EXPOSURE=20`)
- max daily realized loss: `20` (`RORY_TRADER_MAX_DAILY_LOSS=20`)
- stale-data kill switch: snapshots older than `1800` seconds are rejected
- auth-failure kill switch: `paper` exits before fetching markets if Betfair validation fails
- recurring service bound: paper sessions should finish within `300` seconds on the VPS

Tennis scouting defaults:
- strategy: `betfair_tennis_pre_match_back_bucket`
- minimum time to event: `0.5` hours (`RORY_TRADER_TENNIS_MIN_HOURS_TO_EVENT=0.5`)
- maximum time to event: `72` hours (`RORY_TRADER_TENNIS_MAX_HOURS_TO_EVENT=72`)
- maximum spread: `0.2` decimal odds (`RORY_TRADER_TENNIS_MAX_SPREAD=0.2`)
- minimum market matched: `50` (`RORY_TRADER_TENNIS_MIN_MARKET_TOTAL_MATCHED=50`)
- Betfair market types: `MATCH_ODDS,SET_WINNER`
- Betfair discovery window: starts at `30` minutes out and ends at `72` hours out
  (`RORY_TRADER_BETFAIR_TENNIS_MIN_START_MINUTES=30`,
  `RORY_TRADER_BETFAIR_TENNIS_MAX_START_HOURS=72`)

The tennis defaults are intentionally more permissive than the generic sports strategy so the system can create
small, reviewable paper fills from real tennis books once Betfair authentication is healthy. They still reject
in-play or immediate-start situations through the minimum time-to-event guardrail and stale-snapshot checks.

If a local workstation returns `BETTING_RESTRICTED_LOCATION`, run paper sessions from the approved VPS path instead
of relaxing strategy rules or adding geo-bypass logic. The dashboard API exposes a token-protected
`POST /api/paper-session/run` endpoint that calls the bounded paper-only script on the backend host and returns the
resulting proposal/fill counts.

The dashboard API also exposes read-only performance breakdowns so the proof view can show what the strategy is
learning without granting write access:

```bash
curl -H "X-Rory-Dashboard-Token: <token>" \
  https://api.your-domain.example/api/dashboard/performance
```

## Replay Rules

- replay input should come from saved snapshots
- the same input should produce the same journal output
- replay must never call live exchange endpoints
- default output should go to a separate replay journal under `runtime/journals/replays/`
- replay should fail if the target output journal already exists instead of appending silently

Command:

```bash
uv run main.py replay [snapshot_parquet] [output_journal]
```

If no snapshot path is supplied, replay uses the latest saved Betfair snapshot. The snapshot capture time is used as
the evaluation clock so old snapshots can be replayed deterministically.

## Learning Loop

- use inherited Kalshi/Polymarket history to study price-bucket calibration and market behavior
- use Betfair as the venue where we collect proposals, paper fills, and post-trade review data
- review journal output by strategy version, price bucket, and time-to-event
- expose those grouped metrics in the dashboard learning review, while treating open-position marks as provisional
- only promote a strategy to tiny manual-assisted live trading after paper evidence survives costs
