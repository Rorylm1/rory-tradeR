# Milestone 03 To-Do

## Objective

Add exchange access, account validation, and normalized market-data ingestion for Betfair and Smarkets.

## Checklist

- [ ] Define shared exchange DTOs and adapter interfaces.
- [ ] Implement common auth/session utilities with secret redaction in logs.
- [ ] Implement Betfair credential validation.
- [ ] Implement Betfair market catalogue discovery.
- [ ] Implement Betfair price polling and normalized mapping.
- [ ] Implement Betfair exchange-native order payload construction for future use.
- [ ] Implement Smarkets credential/config plumbing.
- [ ] Implement Smarkets approval-status reporting.
- [ ] Implement Smarkets market discovery and price ingestion.
- [ ] Normalize both exchanges into a shared market snapshot shape.
- [ ] Add fixture-based tests for Betfair normalization.
- [ ] Add fixture-based tests for Smarkets normalization.
- [ ] Add a `markets` command that outputs normalized sports/politics data.
- [ ] Add a `doctor` command that reports capability and approval state safely.

## Exit Criteria

- [ ] Betfair works as the primary first-depth exchange.
- [ ] Smarkets works as an approval-aware data source.
- [ ] Both exchanges can be queried without exposing secrets or live-order risk.
