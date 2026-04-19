# Strategy and Paper Trading Spec

## Scope

This document defines the first paper-trading boundary for `rory-tradeR`.

## First Milestone Rules

- strategies may emit normalized trade intents
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
- apply configurable slippage and commission
- reject intents that exceed risk limits
- stop if market data is stale or auth state is unhealthy

## Risk Defaults

- max stake per trade
- max exposure per market
- max daily loss
- stale-data kill switch
- auth-failure kill switch

## Replay Rules

- replay input should come from saved snapshots
- the same input should produce the same journal output
- replay must never call live exchange endpoints
