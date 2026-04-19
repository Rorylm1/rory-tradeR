# Rory TradeR Milestones

This document tracks the medium-term delivery plan for `rory-tradeR`.

The rule for this repository is:
- each milestone has a dedicated checklist
- work should be ticked off in the milestone's `to-do.md`
- we should not start a later milestone until the earlier milestone is stable enough to support it

## Milestone 01: Repo Foundation

Goal:
- turn `rory-tradeR` into a clean, secure, upstream-derived trading research repo

Key outcomes:
- local repo boundary established
- upstream relationship documented
- core repo docs created
- initial structure for trading work in place

Checklist:
- [Milestone 01 to-do](docs/trading/milestones/milestone-01/to-do.md)

## Milestone 02: Secure Data Ingestion

Goal:
- create a safe, repeatable way to acquire and verify upstream historical data

Key outcomes:
- upstream setup path inspected
- checksum and provenance workflow documented
- quarantine-first extraction process implemented
- `data-verify` workflow defined

Checklist:
- [Milestone 02 to-do](docs/trading/milestones/milestone-02/to-do.md)

## Milestone 03: Exchange Access + Normalization

Goal:
- add Betfair and Smarkets account validation and normalized market-data access

Key outcomes:
- shared exchange adapter contract
- Betfair integration at full first-pass depth
- Smarkets integration with approval-aware gating
- normalized market snapshots for sports/politics

Checklist:
- [Milestone 03 to-do](docs/trading/milestones/milestone-03/to-do.md)

## Milestone 04: Paper Trading Engine

Goal:
- add a safe paper-execution path with journaling, replay, and PnL tracking

Key outcomes:
- paper broker
- portfolio state + risk checks
- `paper` and `replay` CLI flows
- deterministic journal output

Checklist:
- [Milestone 04 to-do](docs/trading/milestones/milestone-04/to-do.md)

## Milestone 05: Live-Readiness Review

Goal:
- decide whether the system is safe enough to even consider manual-assisted or live execution later

Key outcomes:
- live-mode requirements documented
- risk and compliance review completed
- exchange-specific constraints confirmed
- explicit go/no-go decision recorded

Checklist:
- [Milestone 05 to-do](docs/trading/milestones/milestone-05/to-do.md)

## Operating Rules

- Milestones are implementation-oriented, not brainstorming notes.
- `to-do.md` files should be actively updated as work lands.
- If scope changes materially, update `spec.md` first, then update the milestone checklist.
- Security-sensitive work should always be reflected in both the relevant `to-do.md` and `AGENTS.md`.
