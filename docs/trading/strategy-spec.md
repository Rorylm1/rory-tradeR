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
- only promote a strategy to tiny manual-assisted live trading after paper evidence survives costs
