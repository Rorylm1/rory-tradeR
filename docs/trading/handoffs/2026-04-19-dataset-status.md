# Dataset Handoff - 2026-04-19

## Summary

Today we completed the secure download and verification of the upstream bulk archive from `https://s3.jbecker.dev/data.tar.zst`.

We did not trust upstream `make setup`.

We downloaded the archive into quarantine, verified it, and then performed a selective extraction into a separate quarantine directory because the full uncompressed archive would not fit on local disk.

## Verified Archive

- archive path: `runtime/quarantine/data.tar.zst`
- archive size on disk: about `34 GiB`
- archive format: `tar.zst`
- sha256: `0be77ff1eae2e8c0fa962bbb1fdf7c26522a7bf19cb627cfb19d26388b71a920`
- member count: `78,739`
- top-level entries: `data`
- unsafe paths detected: `no`

## What Was Extracted

Selective extraction destination:
- `runtime/quarantine/extracted-lite`

Extracted prefixes:
- `data/kalshi`
- `data/polymarket/blocks`
- `data/polymarket/markets`
- `data/polymarket/legacy_trades`
- `data/polymarket/fpmm_collateral_lookup.json`

Result:
- extracted members: `9,037`
- skipped members: `69,702`
- extracted bytes: `5,372,891,539`
- extracted size on disk: about `5.0 GiB`

## What Was Not Extracted

Skipped on purpose:
- `data/polymarket/trades`

Reason:
- full uncompressed archive is about `49.90 GiB`
- free disk at extraction time was about `42 GiB`
- `data/polymarket/trades` alone is about `44.89 GiB`

This means we now have:
- all extracted Kalshi markets and trades from the archive
- Polymarket blocks
- Polymarket markets
- Polymarket legacy trades
- Polymarket collateral lookup

We do not currently have:
- the large current `data/polymarket/trades` subtree extracted

## Current Safe State

- archive remains quarantined and intact
- extracted subset remains in a separate quarantine directory
- nothing from the archive has been executed
- no live trading capability has been enabled

## Code Added Today

Added selective extraction support:
- `src/trading/data_extract.py`
- `main.py` command: `data-extract`
- repo data-root auto-detection now prefers `runtime/quarantine/extracted-lite/data` when it contains the only real local dataset
- optional override env var: `RORY_TRADER_DATA_ROOT`

Purpose:
- allow safe, prefix-based extraction when disk is constrained
- keep extraction inside quarantine rather than the live repo `data/` path

## Recommended Next Step Tomorrow

Choose one:

1. Point analysis and ingestion code at `runtime/quarantine/extracted-lite/data` for immediate work.
2. Copy the extracted-lite subset into a cleaner local working `data/` layout if we want the repo to use it by default.
3. Keep the archive as the source of truth and only extract additional prefixes on demand.

## Product Direction Note

User said they likely only have `Betfair Exchange API` access.

Recommended planning adjustment:
- make Betfair the primary real exchange integration
- treat Smarkets as optional/later
- keep the internal exchange models generic, but bias milestones toward Betfair first
