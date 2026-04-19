# Rory TradeR - Claude Notes

## Objective

Build a secure, research-first prediction-market trading system based on the upstream `prediction-market-analysis` project.

Current focus:
- upstream-compatible repo structure
- secure data ingestion
- Betfair + Smarkets market-data access
- paper trading only

## Hard Rules

- Do not place live-money orders unless explicitly requested in a later phase.
- Do not add hidden background automation.
- Do not add VPN, scraping, or geo-bypass logic.
- Do not expose secrets in logs, docs, or fixtures.
- Do not treat upstream bulk data as trusted until verified.

## Key Risks

- External bulk datasets are a stronger risk surface than repo-tracked code.
- Exchange auth/session handling can leak sensitive values if logging is careless.
- A paper-trading codepath can drift into live execution if boundaries are vague.
- Betfair and Smarkets have different approval, rate-limit, and operational constraints.
- Exchange downtime or stale data can create false confidence in strategy behavior.

## Priority Order

1. preserve upstream provenance and structure
2. secure the data workflow
3. normalize exchange access
4. build paper execution
5. only later assess live-readiness

## Key Files

- `spec.md`
- `milestones.md`
- `AGENTS.md`
- `docs/trading/`

## Working Convention

- If scope changes, update `spec.md` first.
- If execution work changes, update the relevant milestone `to-do.md`.
- If a new risk appears, add it to `AGENTS.md`.
