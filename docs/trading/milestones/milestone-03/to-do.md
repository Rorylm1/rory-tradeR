# Milestone 03 To-Do

## Objective

Add exchange access, account validation, and normalized market-data ingestion for Betfair and Smarkets.

## Checklist

- [x] Define shared exchange DTOs and adapter interfaces.
- [x] Implement common auth/session utilities with secret redaction in logs.
- [x] Implement Betfair credential validation.
- [x] Implement Betfair market catalogue discovery.
- [x] Implement Betfair price polling and normalized mapping.
- [ ] Implement Betfair exchange-native order payload construction for future use.
- [x] Implement Smarkets credential/config plumbing.
- [x] Implement Smarkets approval-status reporting.
- [ ] Implement Smarkets market discovery and price ingestion.
- [x] Normalize both exchanges into a shared market snapshot shape.
- [x] Add fixture-based tests for Betfair normalization.
- [x] Add fixture-based tests for Smarkets normalization.
- [x] Add a `markets` command that outputs normalized sports/politics data.
- [x] Add a `doctor` command that reports capability and approval state safely.

## Completed This Session

- Created `src/exchanges/common/normalize.py` with category inference and price conversion utilities
- Updated Betfair adapter with category inference from event type ID
- Implemented Betfair `list_markets()` using market catalogue + market book API calls
- Added Smarkets `normalize_market()` method with basis-point to decimal odds conversion
- Created test fixtures: `tests/fixtures/betfair/` and `tests/fixtures/smarkets/`
- Added 25 normalization tests (10 Betfair, 15 Smarkets)
- Updated `docs/trading/exchanges.md` with capability matrix and implementation status
- Wired `uv run main.py markets <category> <max_results>` to real Betfair normalized output

## Remaining Work

- Implement `list_markets()` for Smarkets when access is confirmed
- Implement Betfair exchange-native order payload construction
- Decide whether to keep Smarkets in Milestone 03 or move it fully to a later milestone

## Exit Criteria

- [x] Betfair works as the primary first-depth exchange (normalization, discovery, and price snapshots working).
- [x] Smarkets works as an approval-aware data source (normalization complete, discovery stubbed).
- [x] Both exchanges can be queried without exposing secrets or live-order risk.
