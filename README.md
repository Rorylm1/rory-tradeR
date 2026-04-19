# Rory TradeR

`rory-tradeR` is a secure, paper-trading-first successor to
[`Jon-Becker/prediction-market-analysis`](https://github.com/Jon-Becker/prediction-market-analysis).

It keeps the upstream Python/`uv`/DuckDB research structure and extends it with:
- secure historical-data ingestion workflows
- Betfair exchange access and normalization
- Smarkets integration scaffolding with approval-aware gating
- paper-trading infrastructure, replay, and execution journaling

This repository is deliberately separate from the art app and other side projects. Its local home is:

`/Users/rorymelville/Documents/side projects/rory-tradeR`

## What We Retain From Upstream

The upstream project gave us a strong starting point for:
- CLI-driven ingestion and analysis
- Parquet + DuckDB research workflows
- category-based market analysis
- testing and CI conventions

The original upstream focus was:
- Polymarket and Kalshi market/trade collection
- prediction-market analysis scripts
- historical dataset packaging and processing

## What Changes Here

`rory-tradeR` changes the project direction in three important ways:

1. it treats the repo as a trading-research system rather than a pure analysis repo
2. it adds exchange-access abstractions for Betfair and Smarkets
3. it keeps the first milestone strictly limited to paper trading with strong safety defaults

## Current Scope

Current milestone goals:
- preserve the upstream codebase and provenance
- document and secure the upstream dataset ingestion path
- add account-validation and market-data access layers for Betfair and Smarkets
- add paper-trading commands and journaling

Explicit non-goals for the first milestone:
- no live-money order placement
- no unattended auto-trading
- no geo-bypass logic
- no browser automation or scraping hacks

## Getting Started

Requires Python 3.9+ and [`uv`](https://github.com/astral-sh/uv).

Install dependencies:

```bash
uv sync --group dev
```

Review repo documentation before using external data or exchange credentials:
- [spec.md](spec.md)
- [milestones.md](milestones.md)
- [docs/ANALYSIS.md](docs/ANALYSIS.md)
- [docs/SCHEMAS.md](docs/SCHEMAS.md)

## CLI

Upstream analysis commands remain available:

```bash
uv run main.py analyze
uv run main.py index
uv run main.py package
```

Trading-foundation commands added in this repo:

```bash
uv run main.py doctor
uv run main.py data-verify /path/to/data.tar.zst
uv run main.py markets
uv run main.py paper
uv run main.py replay
```

Notes:
- `doctor` checks exchange config and approval readiness
- `data-verify` validates archive checksum and extraction shape
- `paper` and `replay` are paper-only safety boundaries

## Data Safety

Do not run `make setup` blindly.

The upstream historical dataset is downloaded from an external bucket and must be treated as untrusted until verified. In this repo the intended workflow is:
- inspect the upstream setup scripts
- download the archive manually or through a documented wrapper
- compute and record SHA-256
- inspect archive contents before extraction
- extract in quarantine first

## Exchange Notes

Betfair:
- primary first-depth integration target
- requires valid account credentials and app access

Smarkets:
- approval-aware integration target
- API access may require explicit approval and activation before full use

## Repo Guides

Core repo guidance lives in:
- [AGENTS.md](AGENTS.md)
- [claude.md](claude.md)
- [docs/trading/](docs/trading)
