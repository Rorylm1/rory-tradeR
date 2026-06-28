# Security Guide

## Security Objective

This repository is trading-adjacent and handles external archives plus exchange credentials. It should default to safe, reviewable, fail-closed behavior.

## Trust Tiers

### Tier 1: Repo-tracked source code

- source: Git-tracked code and docs
- controls: review, tests, and explicit documentation

### Tier 2: Package dependencies

- source: PyPI and locked dependencies in `uv.lock`
- controls: pinned versions, lockfile review, minimal dependency growth

### Tier 3: External bulk data

- source: historical datasets and downloaded archives
- controls: checksum, provenance recording, quarantine extraction, manual confirmation

## Historical Data Workflow

Do not run upstream `make setup` blindly.

Required workflow:
1. inspect upstream setup scripts
2. record source URL and expected size
3. download archive
4. compute SHA-256
5. inspect archive contents before extraction
6. extract in quarantine first
7. move validated data into local working directories only after inspection

### Current Upstream Archive

Current upstream data path:
- URL: `https://s3.jbecker.dev/data.tar.zst`
- advertised compressed size: approximately `36 GiB`
- expected extracted root: `data/`
- expected primary subdirectories: `data/kalshi/` and `data/polymarket/`

Current upstream behavior to avoid:
- auto-extracting directly into the working tree
- auto-deleting the source archive immediately after extraction

Preferred local workflow:
- download to a quarantine location
- run `uv run main.py data-verify <archive>`
- record the SHA-256 in this document or an operator log
- inspect top-level paths
- only then extract in an isolated location
- if disk is constrained, use selective extraction into a quarantine subdirectory instead of full extraction

Active data-root behavior:
- the repo supports an optional `RORY_TRADER_DATA_ROOT` environment variable
- if it is unset, the code will prefer `runtime/quarantine/extracted-lite/data` when that location contains a dataset and the repo `data/` directory does not
- this allows safe use of the verified quarantine subset without copying it into the live repo data path

Runtime-state behavior:
- append-only journals should live under `runtime/journals/`
- dashboard SQLite state should live under `runtime/dashboard/`
- live gating should remain off by default via `RORY_TRADER_LIVE_ENABLED=false`
- proposal generation and paper fills should be reviewable from local journal output before any live promotion
- deployed dashboard API access should require `RORY_TRADER_DASHBOARD_TOKEN`
- Vercel may hold dashboard auth and backend API token values, but must not hold Betfair credentials
- recurring VPS jobs may run only through bounded paper-only systemd units:
  `rory-trader-paper-session.service` / `rory-trader-paper-session.timer` for proposals and fills, and
  `rory-trader-settlement.service` / `rory-trader-settlement.timer` for settled-market journal resolutions
- the paper and settlement loops must log to journald, use `RORY_TRADER_LIVE_ENABLED=false`, and be disable-able with
  `sudo systemctl disable --now rory-trader-paper-session.timer` and
  `sudo systemctl disable --now rory-trader-settlement.timer`
- fresh Betfair odds may be shown in the dashboard from explicit paper snapshot runs or operator-triggered read-only live odds refreshes, but live order execution must remain unavailable
- stale snapshots, missing executable prices, delayed market data, in-play markets, and thin books should be surfaced as dashboard guardrails before any operator review

Paper risk defaults:
- commission: `RORY_TRADER_PAPER_COMMISSION_RATE=0.02`
- slippage: `RORY_TRADER_PAPER_SLIPPAGE_BPS=25`
- max stake per paper trade: `RORY_TRADER_MAX_STAKE_PER_TRADE=10`
- max open exposure per market: `RORY_TRADER_MAX_MARKET_EXPOSURE=20`
- max daily realized loss before new paper fills stop: `RORY_TRADER_MAX_DAILY_LOSS=20`
- stale snapshot kill switch: `RORY_TRADER_PAPER_MAX_SNAPSHOT_AGE_SECONDS=1800`
- minimum top-of-book available size: `RORY_TRADER_PAPER_MIN_AVAILABLE_SIZE=2`
- settlement loop defaults: dry-run unless `--apply`, minimum age `RORY_TRADER_SETTLEMENT_MIN_AGE_HOURS=3`,
  max market batch `RORY_TRADER_SETTLEMENT_MAX_MARKETS=50`, max positions per run
  `RORY_TRADER_SETTLEMENT_MAX_POSITIONS=500`

Verified archive on `2026-04-19`:
- archive path: `runtime/quarantine/data.tar.zst`
- sha256: `0be77ff1eae2e8c0fa962bbb1fdf7c26522a7bf19cb627cfb19d26388b71a920`
- archive format: `tar.zst`
- member count: `78,739`
- top-level entries: `data`
- unsafe paths detected: `no`

Selective extraction performed on `2026-04-19`:
- destination: `runtime/quarantine/extracted-lite`
- extracted prefixes:
  - `data/kalshi`
  - `data/polymarket/blocks`
  - `data/polymarket/markets`
  - `data/polymarket/legacy_trades`
  - `data/polymarket/fpmm_collateral_lookup.json`
- skipped on purpose:
  - `data/polymarket/trades`
- reason for selective extraction:
  - full uncompressed archive size is about `49.9 GiB`
  - available disk at extraction time was about `42 GiB`
  - `data/polymarket/trades` alone is about `44.9 GiB`

## Extraction Checklist

- top-level paths match expectation
- no suspicious executable content
- no path traversal entries
- no silent auto-delete of the source archive before validation

## Secret Handling

- use `.env` for secrets only
- never commit secrets
- never print raw tokens, passwords, or session identifiers
- scrub recorded fixtures before they are committed
- Betfair non-interactive login requires a public certificate plus matching private key; keep the `.key` file local
  and upload only the `.crt` file to Betfair
- project-local Betfair certs live under `runtime/betfair/certs/`, which is ignored runtime state
- generate a local Betfair cert/key pair with:

```bash
scripts/create-betfair-cert.sh --write-env
```

- after uploading the generated `.crt` to Betfair, confirm access with `uv run main.py doctor` before any paper
  session; if doctor is not `OK`, `paper` must not fetch markets or create fills

## Paper-Only Rule

Milestone one is paper-only.

That means:
- no live order submission
- no unattended live strategy loops
- any recurring VPS loop is paper-only, bounded, logged, and easy to disable
- no hidden execution path behind config defaults

## Paper Position Resolution

Resolve paper positions only after the underlying Betfair market has settled and the result is known from an ordinary
account/operator review. Use:

```bash
uv run main.py resolve-paper <proposal_id> <won|lost|void> "source note"
```

The command appends a `resolution` event, calculates realized PnL after commission, and leaves the original proposal
and fill events untouched. Do not edit the journal by hand unless performing a documented incident repair.

Automated paper settlement is allowed only for overdue Betfair paper positions where `listMarketBook` returns a
`CLOSED` market and a settleable runner status. The settlement command is dry-run by default:

```bash
uv run main.py settle-paper
uv run main.py settle-paper --apply --max-positions 500 --max-markets 50
```

The apply path appends `resolution` events only. It must not place, cancel, replace, or update live orders. The
settlement timer should call the same command through `scripts/run-settlement-session.sh`, remain bounded by timeout
and max-position settings, and be disable-able with:

```bash
sudo systemctl disable --now rory-trader-settlement.timer
```

## Promotion Checklist For Any Future Live Mode

- explicit live readiness review completed
- exchange constraints confirmed
- secret redaction tested
- kill switches tested
- operator confirmations documented
- clear go / no-go recorded in docs
