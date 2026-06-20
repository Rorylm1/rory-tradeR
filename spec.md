# Rory TradeR Spec

## Overview

`rory-tradeR` is a separate sibling repository to the art app and is intended to become a secure, fork-derived successor to [`Jon-Becker/prediction-market-analysis`](https://github.com/Jon-Becker/prediction-market-analysis).

This repository should preserve the upstream project's strengths:
- Python-first tooling
- `uv`-managed environment
- DuckDB + Parquet research workflow
- CLI-driven ingestion and analysis patterns

This repository should add a new trading-focused layer:
- secure upstream dataset ingestion
- inherited Kalshi/Polymarket market-behavior research priors
- Betfair market-data, account validation, and strategy evaluation support
- paper-trading infrastructure with strong operational safety defaults
- a later manual-assisted tiny-live Betfair path once paper evidence justifies it

This first milestone is intentionally limited to research and infrastructure. It must not place live-money orders, run unattended bots, or include hidden background automation.

The VPS paper milestone allows one explicit exception: a bounded, logged, paper-only systemd service/timer may collect
snapshots, evaluate strategies, create paper fills, and update journals. It must remain easy to disable and must never
submit live orders.

## Repository Boundary

### Local placement

The local checkout path is:

`/Users/rorymelville/Documents/side projects/rory-tradeR`

This project must remain:
- completely separate from the art app
- a sibling directory under `side projects`
- free of shared runtime or code coupling with other side projects

### Remote structure

The repository should be treated as an upstream-derived project.

Remotes:
- `origin`: `https://github.com/Rorylm1/rory-tradeR.git`
- `upstream`: `https://github.com/Jon-Becker/prediction-market-analysis.git`

### Fork stance

This repo should be explicit about its relationship to the upstream project:
- it began as an adaptation/fork successor of `prediction-market-analysis`
- it retains the upstream analysis architecture where useful
- it layers exchange access, trading abstractions, and safety controls on top

## First Milestone Goals

The first milestone should deliver five things:

1. establish the repo as an upstream-derived trading research project
2. preserve the upstream Python analysis shape
3. add a secure workflow for historical dataset ingestion
4. add Betfair market-data access with normalized internal models
5. add a journaled paper-trading path with explicit safety rails

## Non-Goals

The first milestone must not include:
- live auto-trading
- unattended live daemons or live background bots
- unbounded or hard-to-disable paper loops
- browser automation or scraping hacks
- geo-bypass logic
- secret values committed to the repository
- any hidden order-submission path

## Top-Level Repository Structure

The target layout should preserve upstream concepts and add trading-specific areas.

```text
README.md
spec.md
docs/
  trading/
    roadmap.md
    exchanges.md
    security.md
    strategy-spec.md
src/
  analysis/
  common/
  indexers/
  exchanges/
    common/
    betfair/
    smarkets/
  trading/
tests/
data/
runtime/
```

### Directory intent

- `docs/trading/`: living design and operating documents
- `src/exchanges/common/`: shared exchange abstractions and normalization
- `src/exchanges/betfair/`: Betfair-specific auth, discovery, and pricing
- `src/exchanges/smarkets/`: Smarkets-specific auth, discovery, and pricing
- `src/trading/`: paper broker, risk checks, portfolio state, and journals
- `data/`: local datasets, cached snapshots, and verified archives
- `runtime/`: logs, execution journals, and transient state that must not be committed

## Documentation Requirements

### `docs/trading/roadmap.md`

Must include:
- project purpose
- upstream relationship
- local directory boundary from the art app
- phased milestones
- implementation order

### `docs/trading/exchanges.md`

Must include:
- Betfair account and API setup steps
- Smarkets API application and approval requirements
- capability matrix by exchange
- current limitations and missing pieces

### `docs/trading/security.md`

Must include:
- trust model
- dependency trust policy
- dataset verification workflow
- extraction checklist
- secret handling rules
- paper-to-live promotion checklist

### `docs/trading/strategy-spec.md`

Must include:
- normalized market model
- paper execution rules
- risk defaults
- CLI behavior
- replay and journaling rules

## Upstream Dataset Ingestion

### Security posture

The upstream dataset path must be treated as untrusted bulk data until verified.

The upstream project's setup flow downloads a large archive from an external bucket. This repository must not run `make setup` blindly on the host machine.

### Required secure acquisition workflow

Before using upstream historical data:
- inspect upstream setup scripts
- document the exact download URL
- document expected archive size
- document expected extracted directory shape
- define checksum verification steps

If no upstream checksum/signature is published:
- compute SHA-256 locally after download
- record the resulting hash in `docs/trading/security.md`
- require explicit operator confirmation before extraction

### Extraction workflow

Extraction must be quarantine-first:
- extract in an isolated or disposable workspace first
- inspect top-level paths before moving data into the working repo
- validate archive contents for path traversal and unexpected files
- do not auto-delete the source archive until validation is complete

### Trust tiers

The repo should formally use three trust tiers:

#### Tier 1: repo-tracked source code
- source: GitHub-tracked code
- controls: normal code review and test coverage

#### Tier 2: package dependencies
- source: package registries and lockfiles
- controls: pinned/locked dependencies, documented install path, review of risky packages

#### Tier 3: external bulk data
- source: historical archives and market snapshots
- controls: checksum, provenance notes, quarantine extraction, manual approval, no execution of bundled files

## Exchange Integration Architecture

### First milestone scope

The first milestone should support:
- credential/config validation
- market discovery
- price polling / snapshot retrieval
- normalized data mapping
- exchange-native proposal and paper-trade generation for future live use

The first milestone must not submit unattended live orders.

### Exchange modules

Add:
- `src/exchanges/common/`
- `src/exchanges/betfair/`
- `src/trading/`

### Shared internal interfaces

The exchange layer should define stable internal contracts for later use:
- `ExchangeAdapter`
- `MarketSnapshot`
- `SelectionSnapshot`
- `OrderIntent`
- `OrderQuote`
- `ExecutionReport`
- `Position`
- `PaperFill`
- `StrategySignal`
- `ProposedTrade`
- `StrategySignal`

### Required `ExchangeAdapter` capabilities

Every adapter should expose:
- `validate_credentials()`
- `list_markets(filters)`
- `get_market_snapshots(request)`
- `build_order_quote(order_intent)`
- `submit_order(order_intent, mode)`
- `supports_live_execution`
- `approval_status`

`submit_order(..., mode="paper")` is permitted in milestone one only as an interface boundary. Any live mode must remain disabled.

### Betfair depth

Betfair is the primary first-pass integration and should include:
- credential validation
- app key / session setup
- market catalogue lookup
- price polling
- normalized market mapping
- exchange-native order payload construction

Milestone-one rule:
- no live order submission

### Smarkets depth

Smarkets should include:
- config and credential plumbing
- approval-aware readiness reporting
- market discovery
- price ingestion
- normalized market mapping

Milestone-one rule:
- execution code paths are stubbed or disabled unless API approval is explicitly confirmed

## Normalized Market Model

Each tradable outcome must normalize to:
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

Internal normalization rules:
- store decimal odds
- store implied probability
- preserve exchange-native fields in `raw_payload` for debugging and reconciliation

## Trading Engine

### CLI surface

The project should extend the upstream CLI model rather than inventing a separate entrypoint.

New commands:
- `doctor`
- `markets`
- `paper`
- `replay`
- `data-verify`

### Command behavior

#### `doctor`

Checks:
- env/config presence
- credential shape
- connectivity to enabled exchanges
- exchange approval status
- safe-mode flags

#### `markets`

Behavior:
- fetch normalized market snapshots from enabled exchanges
- print structured summaries for sports/politics categories
- never place orders

#### `paper`

Behavior:
- run a paper-trading session
- process normalized market snapshots
- apply risk checks
- write append-only journal output
- print dry-run summary before execution begins

#### `replay`

Behavior:
- replay saved snapshots deterministically
- run strategy + paper broker over historical inputs
- produce reproducible journal output

#### `data-verify`

Behavior:
- validate archive checksum
- inspect top-level extraction shape
- confirm archive provenance metadata
- fail closed on unexpected structure

## Paper Broker

The paper-trading layer should live in `src/trading/` and include:
- strategy interface
- paper broker
- portfolio state
- position ledger
- realized/unrealized PnL
- slippage model
- commission model
- append-only execution journal

### Paper broker rules

- accept normalized `OrderIntent`
- fill only in paper mode
- simulate fills against best available prices
- apply configurable slippage and commissions
- track open and closed positions
- record all fills and PnL transitions in an append-only journal

## Risk and Safety Defaults

Milestone-one default protections:
- max stake per trade
- max exposure per market
- max daily loss
- stale-data kill switch
- auth-failure kill switch
- explicit paper-only mode default
- operator-visible dry-run summaries

### Security defaults

- `.env` for secrets only
- no secrets committed
- no secrets printed in logs
- auth/session tokens redacted in debug output
- separate runtime config from secrets
- recorded fixtures scrubbed before commit
- no hidden automation
- live execution disabled by default and protected by explicit flags

## Configuration Model

Use two configuration layers:

### Secrets

Environment variables in `.env`:
- exchange credentials
- session/application keys
- account identifiers where needed

### Runtime config

A checked-in config file should define:
- enabled exchanges
- categories
- polling interval
- slippage assumptions
- commission assumptions
- stake caps
- daily loss caps
- mode (`paper` / future `live`)
- data and runtime paths

## Testing Requirements

### Core tests

Must include:
- upstream bootstrap sanity checks
- Betfair normalization tests from recorded fixtures
- Smarkets normalization tests from recorded fixtures
- odds/probability conversion tests
- commission/slippage tests
- PnL reconciliation tests
- stale-data kill-switch tests
- auth-failure kill-switch tests
- secret redaction tests
- dataset checksum/extraction validation tests

### Integration scenarios

Must cover:
- `doctor` succeeds with valid Betfair credentials
- `doctor` reports missing Smarkets approval clearly and non-fatally
- `data-verify` validates checksum and archive structure
- `markets` returns normalized sports/politics data
- `paper` writes deterministic journal output
- no milestone-one command can submit a live order

## Phased Delivery

### Phase 1: Repo foundation

- bring upstream codebase into the repo
- preserve Python/`uv`/DuckDB structure
- add root documentation and trading docs
- establish `.gitignore`, runtime boundaries, and config shape

### Phase 2: Secure data workflow

- inspect upstream setup path
- add `data-verify`
- document checksum and quarantine extraction process
- prepare local data directory conventions

### Phase 3: Exchange normalization

- build common exchange interfaces
- implement Betfair integration first
- implement approval-aware Smarkets integration
- add normalized market snapshot output

### Phase 4: Paper-trading engine

- implement paper broker
- add strategy interface
- add replay mode
- add journaling and portfolio accounting

## Assumptions and Defaults

- `rory-tradeR` is a separate sibling repo, not part of the art app.
- The project is explicitly based on a fork/adaptation of `prediction-market-analysis`.
- The upstream Python stack is preserved rather than rewritten.
- Historical data will be used only through a checksum-and-quarantine workflow.
- Betfair is the primary first-depth exchange.
- Smarkets starts as approval-aware data integration, not live execution.
- First milestone remains paper-only.
- Security is a first-class deliverable, not a cleanup task.
