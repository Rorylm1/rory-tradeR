# Rory TradeR

`rory-tradeR` is a secure, paper-trading-first successor to
[`Jon-Becker/prediction-market-analysis`](https://github.com/Jon-Becker/prediction-market-analysis).

It keeps the upstream Python/`uv`/DuckDB research structure and extends it with:
- secure historical-data ingestion workflows
- inherited Kalshi/Polymarket research priors
- Betfair exchange access, snapshot collection, and normalization
- paper-trading proposals, execution journaling, and review commands
- a manual-assisted live-trading path that stays gated until paper results justify it

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
2. it uses inherited Kalshi/Polymarket history as a research template rather than a direct execution signal
3. it makes Betfair the primary execution venue, with paper and live trading gated by strict safety defaults

## Current Scope

Current milestone goals:
- preserve the upstream codebase and provenance
- document and secure the upstream dataset ingestion path
- collect and normalize Betfair market snapshots
- generate versioned paper-trading proposals and journal them durably
- review strategy performance before any tiny live trading is considered

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
uv run main.py paper sports 25
uv run main.py research-priors
uv run main.py journal-report
uv run main.py resolve-paper <proposal_id> <won|lost|void>
uv run main.py replay [snapshot_parquet] [output_journal]
uv run main.py dashboard-api 127.0.0.1 8000
```

Notes:
- `doctor` checks exchange config and approval readiness
- `data-verify` validates archive checksum and extraction shape
- `paper` collects Betfair snapshots, emits strategy proposals, and simulates paper fills
- `research-priors` summarizes inherited Kalshi price-bucket priors
- `journal-report` summarizes open positions, closed results, and PnL by strategy, price bucket, and time-to-event
- `resolve-paper` manually settles a paper position by `proposal_id` and appends the outcome to the journal
- `replay` runs strategy evaluation and paper execution from saved snapshot parquet only, writing a separate replay journal
- `dashboard-api` serves the token-protected FastAPI backend for the deployed trade monitor

## Dashboard

The first deployed dashboard uses a hybrid shape:
- Hetzner VPS runs the FastAPI backend, Betfair access, SQLite dashboard state, and append-only journal.
- Vercel serves the login-protected Next.js UI from `web/`.
- Betfair secrets stay on the VPS and must not be configured in Vercel.
- Live-review buttons record status and notes only; no live order endpoint exists in this milestone.

Deployment notes live in [docs/trading/deployment/hetzner-vercel-dashboard.md](docs/trading/deployment/hetzner-vercel-dashboard.md).

On the VPS, Betfair credentials and certificate files are configured with:

```bash
sudo BETFAIR_CERT_SOURCE=/tmp/client.crt \
  BETFAIR_KEY_SOURCE=/tmp/client.key \
  bash /opt/rory-trader/scripts/configure-betfair-vps.sh
```

To refresh the dashboard with Betfair paper data immediately, run one explicit paper session:

```bash
sudo systemctl start rory-trader-paper-session
```

The deployed VPS can also run the bounded paper-only timer:

```bash
sudo systemctl status rory-trader-paper-session.timer
sudo systemctl disable --now rory-trader-paper-session.timer
```

The service fetches current market data, creates paper-only fills, and writes the append-only journal for the dashboard. It never enables live Betfair order submission.

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
- primary execution and learning target
- requires valid account credentials and app access

Smarkets:
- deferred optional expansion path
- not part of the core trading loop right now

## Repo Guides

Core repo guidance lives in:
- [AGENTS.md](AGENTS.md)
- [claude.md](claude.md)
- [docs/trading/](docs/trading)
