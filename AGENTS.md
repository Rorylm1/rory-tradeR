# Rory TradeR - Agent Guide

## Mission

Turn `rory-tradeR` into a secure, upstream-derived trading research repo that:
- inherits the useful research structure from `prediction-market-analysis`
- adds Betfair and Smarkets exchange access
- supports paper trading with clear safety rails
- remains conservative about security and operational risk

## What Good Looks Like

- Upstream provenance is obvious.
- Data ingestion is verified and documented.
- Exchange integrations are normalized and testable.
- Paper-trading flows are deterministic and reviewable.
- No live execution can happen accidentally.

## Risks To Keep Front Of Mind

### Security

- external archives may be malicious or malformed
- credentials and tokens may leak through logs or fixtures
- runtime state may accidentally be committed

### Product / Scope

- the repo can drift into a greenfield rewrite instead of leveraging upstream
- Smarkets access may be approval-gated and slower than Betfair
- live-trading ambition can overwhelm the infrastructure-first milestone

### Operational

- stale prices can corrupt paper results
- exchange-specific odd formats can lead to incorrect normalization
- retries or fallback logic can hide partial failures

## Constraints

- first milestone is paper-only
- no unattended bots
- no geo-bypass logic
- no browser automation
- no secret values in the repo

## Important Repo Facts

- local path: `/Users/rorymelville/Documents/side projects/rory-tradeR`
- `origin`: `https://github.com/Rorylm1/rory-tradeR.git`
- `upstream`: `https://github.com/Jon-Becker/prediction-market-analysis.git`
- this repo is separate from the art app and must stay separate

## Decision Defaults

- prefer preserving upstream Python/`uv`/DuckDB structure over rewriting
- prefer explicit CLI commands over background services
- prefer fail-closed safety behavior over convenience
- prefer fixture-based testing for exchange integrations
- prefer manual confirmation for risky data operations

## Must-Read Docs Before Major Work

- `spec.md`
- `milestones.md`
- `docs/trading/security.md` once created
- relevant milestone `to-do.md`
