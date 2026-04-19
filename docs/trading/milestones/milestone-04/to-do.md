# Milestone 04 To-Do

## Objective

Build the paper-trading engine, replay flow, and append-only execution journal.

## Checklist

- [ ] Define `Strategy`, `PaperBroker`, and portfolio-state contracts.
- [ ] Implement paper fill simulation against normalized prices.
- [ ] Implement commission and slippage models.
- [ ] Implement open-position and closed-position accounting.
- [ ] Implement realized and unrealized PnL tracking.
- [ ] Implement max stake, max exposure, and max daily loss controls.
- [ ] Implement stale-data and auth-failure kill switches.
- [ ] Implement append-only execution journaling.
- [ ] Add a `paper` command for simulated sessions.
- [ ] Add a `replay` command for deterministic playback from saved snapshots.
- [ ] Add tests for PnL reconciliation, journal output, and safety controls.

## Exit Criteria

- [ ] Paper sessions can run without any live exchange execution.
- [ ] Journal output is deterministic and reviewable.
- [ ] Risk controls fail closed rather than continuing in an unsafe state.
