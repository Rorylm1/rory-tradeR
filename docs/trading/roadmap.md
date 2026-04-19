# Trading Roadmap

## Purpose

`rory-tradeR` is a fork-derived trading research repository built on top of `prediction-market-analysis`.

We are preserving the upstream Python/`uv`/DuckDB research foundation while adding:
- secure historical-data ingestion
- exchange-access abstractions
- paper-trading execution infrastructure

## Local Boundary

This repo is a standalone sibling project at:

`/Users/rorymelville/Documents/side projects/rory-tradeR`

It is intentionally separate from the art app and must stay operationally independent.

## Delivery Phases

### Phase 1: Repo Foundation

- merge and preserve upstream history
- update the README and repo guidance files
- add trading-specific docs and directories
- add safe ignore rules for secrets, runtime state, and archives

### Phase 2: Secure Data Workflow

- inspect upstream setup scripts
- define checksum and quarantine extraction workflow
- add `data-verify` CLI support
- document provenance, archive shape, and trust tiers

### Phase 3: Exchange Integration

- define normalized exchange interfaces
- implement Betfair account validation and market discovery
- implement Smarkets approval-aware integration
- produce normalized market snapshots

### Phase 4: Paper Trading

- define order, quote, fill, and position models
- implement paper broker and journal output
- add replay support
- enforce risk and kill-switch logic

### Phase 5: Live-Readiness Review

- review operational, security, and exchange-specific constraints
- decide whether manual-assisted or live execution should ever proceed

## Implementation Order

1. repo structure and docs
2. secure data verification tooling
3. exchange adapters and normalization
4. paper broker and replay
5. live-readiness review
