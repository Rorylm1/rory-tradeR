# Milestone 05 To-Do

## Objective

Review whether the system is mature enough to consider manual-assisted or live execution in a later phase.

## Checklist

- [ ] Document a live-readiness checklist in `docs/trading/security.md`.
- [ ] Confirm Betfair and Smarkets terms, approval state, and operational restrictions.
- [ ] Review secret handling, log redaction, and account-safety controls.
- [ ] Review rate limiting, retry behavior, and outage handling.
- [ ] Review paper-trading results and journal quality.
- [ ] Document manual-assisted mode requirements.
- [ ] Document live-mode kill switches and operator confirmations required.
- [ ] Record an explicit go / no-go decision before any live execution work starts.

## Exit Criteria

- [ ] We have written evidence for why live work should or should not proceed.
- [ ] Any move toward live execution is a conscious upgrade, not a drift from paper mode.
